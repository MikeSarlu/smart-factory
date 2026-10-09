# ESP32: puesta en marcha de Smart-Factory paso por paso

Esta guía conecta un **ESP32 clásico WROOM-32** al proyecto para medir una fuente o motor DC de 12 V, enviar datos a PostgreSQL y consultar comandos de LEDs desde Grafana.

La ruta principal usa **AWS**. Si quieres probar con **Docker local**, sigue primero la sección 13; allí se indican los pasos de AWS que debes omitir. Ejecuta los comandos del proyecto desde su carpeta raíz. Los ejemplos de terminal principales usan **PowerShell en Windows**.

## 1. Qué está listo y qué falta comprobar

El firmware [smart_factory.ino](firmware/smart_factory/smart_factory.ino) compiló correctamente con **esp32 de Espressif 3.3.2** y **ArduinoJson 6.21.5** para `ESP32 Dev Module`. Usó 80 % de memoria de programa y 14 % de RAM. No se ha cargado ni probado físicamente una placa en esta revisión.

En la revisión del **8 de octubre de 2026**, esta consulta devolvió `403 Missing Authentication Token`:

```text
GET https://wrsbsxcc03.execute-api.us-east-2.amazonaws.com/prod/control?led_id=led1
```

Debes repetir la prueba después de revisar API Gateway. La compilación no confirma que AWS, la base de datos o el hardware estén funcionando.

Orden de trabajo:

1. Actualizar los archivos y preparar Wi-Fi.
2. Aplicar la migración SQL.
3. Revisar las Lambdas y corregir API Gateway.
4. Comprobar las consultas de control desde la computadora.
5. Actualizar Grafana y detener el simulador.
6. Preparar el circuito, compilar y cargar el firmware.
7. Verificar lecturas, LEDs y reconexión.

## 2. Descargar los cambios y preparar los materiales

Si estás trabajando desde otro equipo, actualiza tu copia del repositorio:

```powershell
git pull --ff-only origin main
```

Si Git informa que tienes cambios locales, revísalos antes de continuar. No necesitas hacer otro `pull` si tu copia ya contiene los archivos siguientes:

| Archivo | Para qué sirve |
| --- | --- |
| [firmware/smart_factory/smart_factory.ino](firmware/smart_factory/smart_factory.ino) | Programa que se carga en el ESP32 |
| [firmware/smart_factory/amazon_root_ca.h](firmware/smart_factory/amazon_root_ca.h) | Certificado raíz para HTTPS con AWS |
| [database/migrations/001_motor_voltage_range.sql](database/migrations/001_motor_voltage_range.sql) | Amplía las columnas para admitir 12 V |
| [grafana/dashboard.json](grafana/dashboard.json) | Dashboard con medidor del canal 1 de 0 a 16 V |
| [firmware/VERIFICACION.md](firmware/VERIFICACION.md) | Resultados de la revisión técnica |

Prepara:

- ESP32 clásico WROOM-32 o placa equivalente y cable USB **de datos**.
- Arduino IDE instalado.
- Multímetro y fuente DC conocida de 5 V o 12 V para comenzar.
- Divisor resistivo: R1 = 30 kΩ y R2 = 7.5 kΩ, o módulo divisor cuya relación **5:1 hayas confirmado**.
- Capacitor cerámico de 100 nF, cables y protoboard.
- LED externo y resistencia de 330 Ω para probar `led2` si lo necesitas.
- Acceso a API Gateway, Lambda, PostgreSQL/RDS y Grafana para la ruta AWS.

**Esta configuración de pines no corresponde a un ESP32-C3/S3.** Si esa es tu placa, adapta placa y pines antes de cargar el programa.

## 3. Preparar la red Wi-Fi

Configura tu router o hotspot con:

| Ajuste | Valor |
| --- | --- |
| SSID | `prueba` |
| Contraseña | `prueba123` |
| Banda | **2.4 GHz** |

1. Conecta una computadora o teléfono a esa red y comprueba que tenga Internet.
2. Si usas una red con portal cautivo, inicia sesión desde la computadora y comparte su conexión por un hotspot. El ESP32 no completa ese inicio de sesión web.
3. El ESP32 debe poder acceder a HTTPS por TCP 443 y a NTP por UDP 123.
4. Para AWS no necesitas abrir puertos de entrada en tu computadora.

En Windows puedes crear el hotspot desde **Configuración → Red e Internet → Zona con cobertura inalámbrica móvil**, editar nombre/contraseña y seleccionar 2.4 GHz si el adaptador lo permite.

En Fedora, si vas a usar un hotspot, identifica tu interfaz y sustituye `wlan0` por su nombre real:

```bash
nmcli device
sudo nmcli device wifi hotspot ifname wlan0 ssid prueba password "prueba123" band bg
```

**Resultado esperado:** otro dispositivo puede conectarse a `prueba` y navegar.

## 4. Preparar PostgreSQL para guardar 12 V

Las columnas antiguas `NUMERIC(3,2)` solo admiten hasta `9.99`; por eso una lectura de 12 V falla. La migración cambia ambos canales analógicos a `NUMERIC(6,2)`.

### Si usas RDS o una base existente

1. Abre DBeaver, pgAdmin o tu cliente SQL.
2. Conéctate a la **misma base** que usan las Lambdas: confirma `DB_HOST` y `DB_NAME` en sus variables de entorno.
3. Abre [001_motor_voltage_range.sql](database/migrations/001_motor_voltage_range.sql).
4. Ejecuta su contenido completo:

```sql
BEGIN;
ALTER TABLE telemetry_data
    ALTER COLUMN analog_ch1 TYPE NUMERIC(6,2),
    ALTER COLUMN analog_ch2 TYPE NUMERIC(6,2);
COMMIT;
```

5. Comprueba el resultado:

```sql
SELECT column_name, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'telemetry_data'
  AND column_name IN ('analog_ch1', 'analog_ch2');
```

**Resultado esperado:** ambos canales muestran precisión `6` y escala `2`.

Si faltan las tablas, ejecuta primero [database/init.sql](database/init.sql) en la base elegida. Una instalación nueva ya crea las columnas con el tamaño correcto. Si aparece `relation telemetry_data does not exist`, confirma primero base y esquema.

No borres tablas ni volúmenes para aplicar la migración. Reiniciar Docker no actualiza automáticamente una base existente.

## 5. Revisar las dos funciones Lambda

Si las funciones ya están desplegadas con este código, verifica sus ajustes. Solo vuelve a subir el ZIP cuando necesites actualizar el código o corregir el paquete.

### 5.1. Generar el paquete si vas a actualizar las Lambdas

Desde la raíz del proyecto:

```powershell
python --version
python -m pip download psycopg2-binary==2.9.9 --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all: --no-deps -d dist/wheels
python build_lambda_zip.py
```

**Resultado esperado:** se genera `dist/lambda_deployment.zip`. El script usa el wheel descargado y no necesita Docker.

### 5.2. Revisar configuración en AWS Lambda

En la región de tu API, abre cada función y comprueba:

| Función de referencia | Runtime | Arquitectura | Handler del ZIP generado |
| --- | --- | --- | --- |
| `SmartFactoryTelemetry` | Python 3.12 | x86_64 | `lambda_function.lambda_handler` |
| `SmartFactoryControl` | Python 3.12 | x86_64 | `lambda_control.lambda_handler` |

El script actual coloca ambos `.py` en la **raíz del ZIP**. Por eso estos handlers no llevan el prefijo `aws.`. Si tus funciones tienen otros nombres, conserva sus nombres y verifica qué función está integrada con cada ruta.

1. Si vas a actualizar, selecciona **Upload from → .zip file** y carga `dist/lambda_deployment.zip` en ambas funciones.
2. En **Runtime settings**, verifica runtime, arquitectura y handler según la tabla.
3. En **Configuration → Environment variables**, configura `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` con los datos de tu PostgreSQL.
4. Comprueba que Lambda tenga conectividad de red a RDS y que el grupo de seguridad de RDS permita PostgreSQL desde el origen correcto, normalmente el grupo de seguridad de Lambda si comparten VPC.

### 5.3. Probar la Lambda de control sin cambiar un LED

En `SmartFactoryControl`, crea un evento de prueba con este JSON:

```json
{
  "httpMethod": "GET",
  "queryStringParameters": {
    "led_id": "led1"
  }
}
```

Ejecuta la prueba.

**Resultado esperado:** `statusCode: 200` y un `body` que contenga `led_id: led1` y `state: 0` o `1`. Si nunca se registró un comando para ese LED, devuelve `0`.

Si devuelve `500`, revisa **Monitor → View CloudWatch logs**: busca errores de conexión, credenciales, tabla inexistente o carga de `psycopg2`. Resuelve eso antes de atribuir el fallo a API Gateway.

## 6. Corregir el endpoint de API Gateway

El firmware usa el formato de una **REST API con integración Lambda proxy**. Los handlers actuales leen `httpMethod`; no cambies a una HTTP API con eventos v2 sin adaptar el backend.

1. En la consola AWS, selecciona la región **us-east-2** para la URL actual.
2. Abre **API Gateway** y busca la REST API cuyo ID es `wrsbsxcc03`. Si ya no existe o tu despliegue es otro, obtén la URL de la API correcta y úsala en el paso 7.
3. En **Resources**, comprueba estas rutas:

| Recurso | Método | Integración |
| --- | --- | --- |
| `/telemetry` | POST | Lambda de telemetría, proxy activado |
| `/control` | GET | Lambda de control, proxy activado |
| `/control` | POST | Lambda de control, proxy activado |
| `/control` | OPTIONS | Respuesta CORS o Lambda de control con proxy |

4. Si falta `GET /control`, créalo y vincúlalo a la Lambda de control.
5. Comprueba que la integración pueda invocar Lambda. Si la consola solicita agregar el permiso correspondiente, complétalo.
6. Revisa la autorización de los métodos. El firmware actual no envía firma IAM, token de authorizer ni API key. Si la API está protegida deliberadamente, conserva esa protección y adapta el cliente; si es tu API de demostración sin autenticación, configura los métodos de acuerdo con ese diseño. El error 403 por sí solo no identifica la causa.
7. Configura CORS en `/control` para permitir POST con el encabezado `Content-Type` desde el origen de Grafana. El handler incluye encabezados CORS; también debe responder el preflight OPTIONS.
8. Selecciona **Deploy API**, elige el stage **prod** y despliega los cambios. Si tu stage tiene otro nombre, usa ese nombre en las URLs.
9. En **Stages**, copia la **Invoke URL**. Para el despliegue actual es:

```text
https://wrsbsxcc03.execute-api.us-east-2.amazonaws.com/prod
```

**Resultado esperado:** las rutas están disponibles en el stage desplegado. Que una prueba interna de Lambda funcione no confirma que API Gateway esté desplegado correctamente.

AWS documenta que `Missing Authentication Token` puede aparecer al invocar un recurso o método inexistente y también al faltar una firma exigida por IAM. Consulta la [explicación oficial del error 403](https://repost.aws/knowledge-center/api-gateway-authentication-token-errors) y el [despliegue de REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-deployments.html).

## 7. Comprobar AWS desde tu computadora

Define la URL base real, incluyendo el stage y sin `/telemetry` ni `/control` al final:

```powershell
$apiBase = 'https://wrsbsxcc03.execute-api.us-east-2.amazonaws.com/prod'
curl.exe -i "${apiBase}/control?led_id=led1"
curl.exe -i "${apiBase}/control?led_id=led2"
```

**Resultado esperado:** HTTP `200` y un objeto JSON como:

```json
{"led_id":"led1","state":0}
```

El segundo debe devolver `led2`; los estados pueden ser `0` o `1`. Estas consultas no crean comandos ni encienden LEDs.

Comprueba el preflight del navegador sustituyendo el origen por la dirección real de tu Grafana:

```powershell
$grafanaOrigin = 'http://localhost:3000'
curl.exe -i -X OPTIONS "${apiBase}/control" -H "Origin: $grafanaOrigin" -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type'
```

**Resultado esperado:** respuesta 2xx con `Access-Control-Allow-Origin` que acepte ese origen, `Access-Control-Allow-Methods` que incluya POST y `Access-Control-Allow-Headers` que incluya Content-Type. Los GET pueden funcionar aunque este preflight falle; en ese caso Grafana no podrá enviar los comandos desde el navegador. Consulta [CORS en REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html).

Si la URL base cambió, actualiza estos tres lugares:

| Lugar | Valor que debe contener |
| --- | --- |
| `AWS_API_BASE_URL` en el sketch | URL base con stage |
| Variable `control_url` de Grafana | URL base + `/control` |
| `.env`, si seguirás usando el simulador | `API_GATEWAY_URL` = base + `/telemetry`; `CONTROL_URL` = base + `/control` |

El ESP32 no lee `.env`: sus ajustes están en el sketch.

## 8. Preparar Grafana y detener el simulador

1. Abre tu Grafana y confirma que su datasource PostgreSQL apunte a la misma base que las Lambdas.
2. En **Dashboards → Import**, carga [grafana/dashboard.json](grafana/dashboard.json). Si actualizas un dashboard existente, confirma que estás abriendo la versión importada.
3. Verifica que el medidor del canal analógico 1 tenga máximo **16 V**.
4. En la configuración del dashboard, abre **Variables → control_url** y configura la URL completa terminada en `/control`.
5. Comprueba que el panel de formularios esté disponible. El proyecto Docker usa `volkovlabs-form-panel` versión `3.2.1`; en un Grafana externo el plugin debe estar instalado y ser compatible con tu versión.
6. Detén el simulador que estés ejecutando:

```powershell
docker compose stop simulator
```

Si lo ejecutaste directamente con Python, usa `Ctrl+C` en su terminal. Si existe otra instancia enviando datos a la misma base, detenla también durante la prueba.

Las consultas actuales del dashboard muestran mediciones de cualquier dispositivo. Un simulador activo puede ocultar las del ESP32.

**Resultado esperado:** Grafana está conectado a la base correcta y el simulador ya no genera nuevas filas.

## 9. Conectar el circuito con la alimentación apagada

Empieza con una fuente DC conocida de 5 V o 12 V. Prueba el motor después de validar las mediciones con la fuente.

**No conectes 24/25 V con el divisor actual 5:1.** Aunque un módulo se venda como “0–25V”, a 25 V entregaría aproximadamente 5 V al ESP32. El rango útil documentado del ADC del ESP32 clásico a 11 dB llega aproximadamente a **3.1 V**, equivalente a **15.5 V** con este divisor. Mantén margen para ruido y transitorios; 3.3 V no es un objetivo de operación. Consulta la [documentación del ADC de Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html).

### 9.1. Divisor resistivo para 12 V

Conecta:

1. Positivo de la fuente → R1 de **30 kΩ**.
2. Otro extremo de R1 → nodo de señal.
3. Nodo de señal → **GPIO 34**.
4. Nodo de señal → R2 de **7.5 kΩ** → negativo de la fuente.
5. Negativo de la fuente → **GND del ESP32**.
6. Capacitor de **100 nF** entre el nodo de señal y GND.

```text
Fuente + ── R1 30 kΩ ──┬──────── GPIO 34
                       │
                       ├── R2 7.5 kΩ ──┐
                       │               │
                       └── 100 nF ─────┤
                                       │
Fuente − ──────────────────────────────┴── GND ESP32
```

A 12 V de entrada debes medir aproximadamente **2.4 V** en el nodo de señal. Verifica el divisor con el multímetro antes de conectarlo al GPIO. Alimenta la placa por USB; no alimentes el motor desde el pin de 3.3 V ni desde un GPIO.

### 9.2. Si usas un módulo divisor comercial

Confirma su esquema y relación de división: no todos los módulos tienen el mismo pinout. En el divisor pasivo común 5:1, conecta entrada positiva/negativa a la fuente, señal `S` al GPIO 34 y tierra al GND compartido. No conectes un pin `+` del conector de señal sin verificar su función en el módulo.

### 9.3. LEDs

| Comando | Pin | Conexión |
| --- | --- | --- |
| `led1` | GPIO 2 | LED integrado solo si tu placa lo usa y es activo en HIGH |
| `led2` | GPIO 4 | GPIO 4 → resistencia 330 Ω → ánodo del LED; cátodo → GND |

Si tu placa no tiene LED en GPIO 2, puedes comprobarlo con un LED externo y resistencia. Estos GPIO controlan LEDs en la prueba; un motor o relé necesita una etapa de potencia apropiada.

## 10. Instalar el soporte y cargar el programa

1. Abre Arduino IDE.
2. En **Preferences**, agrega esta URL al gestor de placas si todavía no tienes el soporte ESP32:

```text
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

3. Abre **Boards Manager**, busca **esp32 by Espressif Systems** e instala **3.3.2** para reproducir la compilación verificada.
4. Abre **Library Manager**, busca **ArduinoJson** e instala **6.21.5**.
5. Abre [firmware/smart_factory/smart_factory.ino](firmware/smart_factory/smart_factory.ino). Conserva `amazon_root_ca.h` en esa misma carpeta.
6. Revisa estos ajustes del sketch:

```cpp
const char* WIFI_SSID = "prueba";
const char* WIFI_PASSWORD = "prueba123";
const bool USE_LOCAL_SERVER = false;
const char* AWS_API_BASE_URL = "https://wrsbsxcc03.execute-api.us-east-2.amazonaws.com/prod";
```

7. Conecta la placa por USB y selecciona **ESP32 Dev Module** y su puerto en **Tools**. Identifica el puerto que aparece al conectar la placa; no selecciones COM1 por suposición.
8. Pulsa **Verify**. Debe compilar sin errores.
9. Pulsa **Upload**. Si se queda en `Connecting...`, mantén presionado **BOOT** mientras comienza la conexión y suéltalo al iniciar la escritura, si tu placa lo requiere.
10. Abre **Serial Monitor** a **115200 baudios**. Pulsa **EN/RESET** si necesitas ver el arranque.

No pegues una versión antigua del código desde otro documento. El archivo `.ino` del repositorio es la referencia actual. Para instalación, consulta [Arduino-ESP32 de Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html).

## 11. Verificar telemetría de extremo a extremo

### 11.1. Monitor serial

Busca mensajes equivalentes a:

```text
[WIFI] Conectando a prueba...
[WIFI] Conectado: 192.168.x.x
[TELEMETRIA] OK (200) {"timestamp":"...","device_id":"esp32_motor_node_01","telemetry":{...}}
[CONTROL] led1=0
[CONTROL] led2=0
```

La IP y los estados pueden variar. El firmware intenta enviar cada **2 segundos** y consultar ambos LEDs cada **4 segundos**; las peticiones son síncronas y los fallos de red pueden retrasar esos intervalos.

Puede aparecer al inicio:

```text
[NTP] Sin hora UTC valida; telemetria pendiente.
```

Espera a la sincronización. El firmware no imprime un mensaje separado de “NTP listo”: confirma la fecha UTC en el payload enviado. Si el aviso persiste, revisa acceso a Internet y UDP 123. El firmware usa `pool.ntp.org` y `time.google.com`.

### 11.2. Confirmar filas del ESP32 en PostgreSQL

Ejecuta en tu cliente SQL:

```sql
SELECT timestamp, device_id, analog_ch1, analog_ch2,
       digital_ch1, digital_ch3
FROM telemetry_data
WHERE device_id = 'esp32_motor_node_01'
ORDER BY timestamp DESC
LIMIT 10;
```

**Resultado esperado:** filas nuevas con hora reciente y el voltaje de la fuente en `analog_ch1`. El canal 2 queda en cero porque el firmware solo mide una entrada analógica.

- A 12 V, el canal 1 debe estar próximo a la medición del multímetro; no esperes precisión de laboratorio sin calibrar el divisor real.
- `digital_ch1` vale 1 cuando la lectura supera 1 V.
- `digital_ch3` vale 1 cuando la lectura supera 13.5 V. No subas la tensión a propósito para probar la alarma si no has confirmado los límites del circuito.
- Si no hay filas pese a recibir HTTP 200, confirma que estás consultando la misma base usada por Lambda.

### 11.3. Confirmar Grafana

1. Abre el dashboard actualizado.
2. Selecciona un rango reciente, por ejemplo **Last 5 minutes**.
3. Comprueba que el medidor del canal 1 muestre el voltaje de la fuente.
4. Cambia de forma controlada entre dos tensiones conocidas dentro del rango permitido y confirma el cambio en serial, SQL y Grafana.

**Resultado esperado:** la misma variación aparece en los tres lugares.

## 12. Verificar comandos y reconexión

### 12.1. Probar los LEDs desde Grafana

1. En el panel de control, cambia `led1` y pulsa **Enviar Comandos al Hardware**.
2. Espera al siguiente ciclo de consulta del ESP32.
3. Busca `[CONTROL] led1=1` o `led1=0` y comprueba físicamente el LED.
4. Repite con `led2` y GPIO 4.
5. Confirma el último comando con las consultas GET del paso 7 y con SQL:

```sql
SELECT led_id, state, command_timestamp, source
FROM control_commands
ORDER BY command_timestamp DESC, id DESC
LIMIT 10;
```

**No uses únicamente el aviso de éxito de Grafana como comprobación.** El código actual del panel no comprueba el estado HTTP del POST y puede mostrar éxito aunque el servidor rechace la solicitud. Confirma que el POST devuelve 200 en **F12 → Network**, que se creó la fila y que reaccionó el GPIO.

El panel también consulta `localStorage` para decidir qué cambios enviar y hace un intento adicional a `http://localhost:8080/control`. Si no se envía una petición, prueba ambos estados del switch y revisa Network; la petición que debe funcionar para AWS es la dirigida a tu `control_url`.

### 12.2. Probar recuperación de Wi-Fi

1. Mantén el ESP32 encendido y apaga la red `prueba`.
2. Comprueba los mensajes `[WIFI] Reintentando conexion...`.
3. Reactiva la red con el mismo SSID y contraseña.
4. Espera la reconexión y confirma que vuelven los mensajes de telemetría exitosa y las filas recientes.
5. Verifica nuevamente un cambio de LED.

El firmware arranca con ambos LEDs en LOW. Durante una desconexión o un error de respuesta mantiene el último estado aplicado; no implementa un apagado automático por pérdida de red.

**Prueba completada:** Wi-Fi conecta, GET de ambos LEDs devuelve 200, telemetría obtiene 200, PostgreSQL guarda las lecturas reales, Grafana las muestra, ambos LEDs responden y la transmisión se recupera tras cortar Wi-Fi.

## 13. Alternativa: probar todo con Docker local

Usa esta ruta si prefieres validar sin AWS. Omite los pasos **5, 6 y 7**; conserva los pasos de red, circuito, carga del firmware y pruebas físicas.

### 13.1. Iniciar servicios

1. Inicia Docker Desktop y espera a que el motor esté disponible.
2. Si no tienes `.env`, copia `.env.example` a `.env`. Si ya existe, edítalo sin sobrescribir otros valores.
3. Para una prueba local del simulador, los endpoints en `.env` son:

```dotenv
API_GATEWAY_URL=http://receiver:8080/telemetry
CONTROL_URL=http://receiver:8080/control
```

4. Levanta solo base de datos, receptor y Grafana:

```powershell
docker compose up -d --build db receiver grafana
docker compose stop simulator
docker compose ps
```

**Resultado esperado:** `db` está saludable y `receiver` y `grafana` están activos. El simulador debe permanecer detenido.

### 13.2. Aplicar la migración a la base local

En PowerShell:

```powershell
Get-Content -Raw database/migrations/001_motor_voltage_range.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d smartfactory
```

En Linux/Fedora:

```bash
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d smartfactory < database/migrations/001_motor_voltage_range.sql
```

Para abrir una sesión SQL y ejecutar las consultas de los pasos 4, 11 y 12:

```powershell
docker compose exec db psql -U postgres -d smartfactory
```

Escribe `\q` para salir. No ejecutes `docker compose down -v`: eliminaría los datos del volumen.

### 13.3. Identificar la IP accesible desde el ESP32

1. En Windows ejecuta `ipconfig` y localiza la IPv4 del adaptador que comparte la red `prueba`.
2. En Fedora ejecuta `ip addr show`; un hotspot de NetworkManager suele usar `10.42.0.1`, pero comprueba el valor real.
3. Esa IP debe ser accesible desde la red del ESP32. No uses `localhost`, `127.0.0.1` ni `receiver` en el sketch.
4. Si el firewall bloquea la conexión, permite TCP 8080 desde la red de pruebas. No necesitas abrir 3000 para el ESP32; ese puerto es para el navegador de Grafana.

En Fedora, si `firewalld` está activo, identifica la zona del hotspot y abre allí el puerto; sustituye `ZONA_HOTSPOT` por la zona real:

```bash
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --zone=ZONA_HOTSPOT --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

### 13.4. Configurar el firmware local

En el sketch cambia:

```cpp
const bool USE_LOCAL_SERVER = true;
const char* LOCAL_API_BASE_URL = "http://10.42.0.1:8080";
```

Sustituye la IP por la de tu computadora. El firmware local usa **HTTP** y consulta `/control/status/led1` y `/control/status/led2`. También necesita acceso a NTP para enviar telemetría.

Comprueba desde tu computadora, usando la IP elegida:

```powershell
$localApi = 'http://10.42.0.1:8080'
curl.exe -i "${localApi}/control/status/led1"
curl.exe -i "${localApi}/control/status/led2"
```

El receptor local actual no admite `GET /control?led_id=...`. Además, su ruta de estado devuelve `state: 0` y HTTP 200 si falla la consulta a PostgreSQL. Para descartar ese fallo, revisa también:

```powershell
docker compose logs --tail 100 receiver
```

### 13.5. Configurar Grafana local y probar

1. Abre `http://localhost:3000`. En una instalación nueva, el usuario y contraseña iniciales son `admin` / `admin`; si ya los cambiaste, usa los actuales.
2. Abre el dashboard aprovisionado desde `grafana/dashboard.json` y confirma el rango de 16 V del canal 1.
3. Configura `control_url` como `http://localhost:8080/control` si el navegador está en esa misma computadora. Si accedes desde otro equipo, usa la IP del receptor.
4. No uses la URL de AWS en ese dashboard durante la prueba local.
5. Sigue los pasos **9 a 12**, cargando el sketch con `USE_LOCAL_SERVER = true`.
6. Para regresar a AWS, vuelve a poner `USE_LOCAL_SERVER = false`, verifica su URL base, recompila y carga nuevamente.

## 14. Si algo falla

| Síntoma | Qué revisar |
| --- | --- |
| `403 Missing Authentication Token` | URL, stage, recurso y método GET; despliegue de API Gateway; autorización exigida |
| Lambda devuelve 500 | CloudWatch: variables DB, red a RDS, tablas y error de PostgreSQL |
| `Unable to import module` o fallo de `psycopg2` | ZIP en la raíz correcta, handlers sin `aws.`, Python 3.12 y x86_64 para este paquete |
| Arduino no encuentra `amazon_root_ca.h` | El `.h` debe estar junto a `smart_factory.ino` |
| Arduino no encuentra `ArduinoJson.h` | Instala ArduinoJson 6.21.5 en Library Manager |
| La carga no detecta la placa | Cable de datos, puerto correcto, controlador USB y BOOT si la placa lo requiere |
| Wi-Fi reintenta continuamente | SSID/contraseña, 2.4 GHz y hotspot sin portal cautivo pendiente |
| NTP nunca obtiene hora | Internet, DNS y UDP 123; revisar las restricciones del hotspot |
| Error HTTPS o de red | Conexión, DNS, hora válida y cadena de certificados; no desactives la validación TLS para ocultarlo |
| Falla al guardar 12 V | Migración aplicada en la misma base usada por Lambda |
| Serial muestra datos, Grafana no cambia | Base/datasource correcto, rango de tiempo y simuladores detenidos |
| Grafana anuncia éxito pero el LED no cambia | POST real en Network, GET de estado, fila en `control_commands`, GPIO y polaridad |
| Error local de conexión | IP de la computadora, puerto 8080, firewall y contenedor receiver activo |
| Lectura inestable o incorrecta | Tierra común, relación del divisor, capacitor, cableado y comparación con multímetro |

## 15. Comprobación final

- [ ] La placa es compatible con GPIO 34, 2 y 4 de esta configuración.
- [ ] La red `prueba` / `prueba123` funciona en 2.4 GHz.
- [ ] Ambas columnas analógicas tienen precisión 6 y escala 2.
- [ ] La Lambda de control pasa la prueba GET y las rutas desplegadas responden.
- [ ] Grafana apunta al backend y a la base elegidos; el simulador está detenido.
- [ ] El divisor entrega una tensión segura antes de conectar GPIO 34.
- [ ] El sketch compila, se carga y muestra telemetría HTTP 200 con fecha UTC reciente.
- [ ] PostgreSQL contiene filas recientes de `esp32_motor_node_01`.
- [ ] El voltaje coincide razonablemente con el multímetro y aparece en Grafana.
- [ ] Ambos LEDs responden y la red se recupera tras apagar/reactivar el hotspot.
