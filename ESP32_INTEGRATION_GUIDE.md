# Guía de Integración con Hardware Real (ESP32)

Esta guía detalla paso a paso cómo reemplazar el simulador en Python de **Smart-Factory** por un microcontrolador físico **ESP32** para medir el voltaje real de un motor y transmitir la telemetría a la plataforma (Docker local o AWS).

---

## 1. Arquitectura del Sistema con Hardware Real

En el proyecto original, el contenedor `simulator` generaba datos matemáticos sintéticos. Al integrar el ESP32, la arquitectura queda de la siguiente manera:

```
[Motor DC / Fuente]
       │
       ▼ (Voltaje analógico)
[Divisor de Tensión / Sensor]
       │
       ▼ (0 - 3.3V)
[ESP32 (ADC GPIO 34)] ──(Wi-Fi / HTTP POST)──▶ [Receptor Local :8080 ó AWS API Gateway]
                                                           │
                                                           ▼
                                                    [PostgreSQL (RDS/Docker)]
                                                           │
                                                           ▼
                                                    [Grafana Dashboard]
```

---

## 2. Lista de Materiales Necesarios

| Componente | Cantidad | Descripción / Función |
| :--- | :---: | :--- |
| **Placa de Desarrollo ESP32** | 1 | NodeMCU-32S, ESP32-WROOM-32 o similar (Wi-Fi 2.4 GHz). |
| **Módulo Sensor de Voltaje DC (0-25V)** ó **Resistencias** | 1 | Módulo divisor resistivo comercial o 2 resistencias ($R_1 = 30\text{k}\Omega$, $R_2 = 7.5\text{k}\Omega$ para motor de 12 V; rango útil aproximado hasta 15.5 V). |
| **Capacitor cerámico 100 nF (0.1 µF)** | 1 | Filtro pasabajas para atenuar ruido electromagnético y picos del motor. |
| **Diodo Zener 3.3V (Opcional pero recomendado)** | 1 | Protección de sobretensión en el pin analógico del ESP32. |
| **Motor DC o Fuente de Prueba** | 1 | Dispositivo a monitorear (ej. motor 5V, 12V o 24V DC). |
| **Protoboard y Cables Dupont** | - | Para interconexión de componentes. |

---

## 3. Diagrama y Conexión Eléctrica

> [!CAUTION]
> **El ADC del ESP32 NO soporta más de 3.3V.** Conectar voltajes superiores a 3.3V quemará permanentemente el pin o el microcontrolador.

### Opción A: Usando el Módulo Sensor de Voltaje DC (0-25V)
Este módulo incluye internamente un divisor de tensión ($5:1$).
* **Lado de Alta Tensión (Entrada del Motor):**
  * `VCC (+) / Terminal +`: Positivo de la alimentación del motor.
  * `GND (-) / Terminal -`: Negativo/Gierra común del motor.
* **Lado de Baja Tensión (Hacia ESP32):**
  * `S (Señal)`: Conectar a **GPIO 34** del ESP32.
  * `- (GND)`: Conectar a **GND** del ESP32.
  * `+`: No se conecta (sin uso).

### Opción B: Divisor de Tensión Resistivo Casero (Ejemplo para Motor 12V DC)
Si construyes tu propio divisor con resistencias:
* $R_1 = 30\text{k}\Omega$ (entre el positivo del motor y el GPIO 34)
* $R_2 = 7.5\text{k}\Omega$ (entre el GPIO 34 y GND común)
* Factor de reducción: $\frac{7.5}{30 + 7.5} = 0.2$ (Rango útil aproximado: $3.1\text{V} / 0.2 = 15.5\text{V}$; 16.5 V es el límite teórico a 3.3 V, no un rango de operación seguro).

```
  [ (+) Motor / 12V ]
           │
          [R1: 30kΩ]
           │
           ├───▶ [ GPIO 34 (ADC ESP32) ]
           │         │
          [R2: 7.5k] [Capacitor 100nF]  (Opcional: Diodo Zener 3.3V a GND)
           │         │
  [ (-) GND Motor ] ─┴───────────▶ [ GND ESP32 ]  (Tierra compartida)
```

> [!IMPORTANT]
> Es fundamental unir el **GND del motor/fuente** con el **GND del ESP32** para tener una referencia común.

---

## 4. Superar Redes con Portal Cautivo (Fedora Linux / Hotspot)

Si estás en una red escolar, universitaria o corporativa con portal de inicio de sesión:

### Paso 1: Conectar tu PC y activar el Hotspot
1. Conéctate con tu laptop a la red institucional e inicia sesión en el portal cautivo.
2. Abre una terminal en Fedora y crea un Hotspot Wi-Fi en **2.4 GHz**:
   ```bash
   # Identifica tu interfaz de red (ej. wlan0, wlp2s0)
   nmcli device

   # Levanta el punto de acceso en banda 2.4 GHz (bg)
   sudo nmcli device wifi hotspot ifname wlan0 ssid prueba password "prueba123" band bg
   ```

### Paso 2: Habilitar puertos en el Firewall de Fedora (`firewalld`)
Fedora bloqueará las peticiones entrantes del ESP32 a menos que abras los puertos:
```bash
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --add-port=3000/tcp --permanent
sudo firewall-cmd --reload
```

### Paso 3: Identificar la IP de tu PC para el ESP32
Al crear el hotspot, Fedora asigna por defecto la IP `10.42.0.1`:
```bash
ip addr show
```
Tu endpoint local será: `http://10.42.0.1:8080/telemetry`.

---

## 5. Firmware para subir al ESP32

El código revisado está en [firmware/smart_factory/smart_factory.ino](firmware/smart_factory/smart_factory.ino).
Abre ese archivo en Arduino IDE; conserva `amazon_root_ca.h` en la misma carpeta.

Configuración incluida:

* SSID: `prueba`; contraseña: `prueba123`. La red debe emitir en **2.4 GHz**.
* Placa: **ESP32 clásico WROOM-32 / ESP32 Dev Module**. Para C3/S3 cambia placa y pines según su documentación.
* Entrada de voltaje: GPIO 34 (ADC1), divisor 5:1 y atenuación de 11 dB.
* `led1`: GPIO 2, activo en HIGH; `led2`: GPIO 4, LED externo con resistencia. Confirma los pines y polaridad de tu placa.
* AWS: `https://wrsbsxcc03.execute-api.us-east-2.amazonaws.com/prod`.
* Telemetría cada 2 segundos; consulta ambos LEDs cada 4 segundos cuando las peticiones responden a tiempo. Las operaciones HTTP son síncronas y pueden retrasar estos intervalos durante fallos de red.

Instala **esp32 de Espressif 3.3.2** y **ArduinoJson 6.21.5** para reproducir la compilación de esta revisión. Selecciona **ESP32 Dev Module**, el puerto USB de tu placa y sube el sketch. Abre el monitor a **115200 baudios**.

El firmware valida HTTPS con Amazon Root CA 1, espera una hora UTC válida por NTP antes de enviar telemetría y reintenta Wi-Fi sin bloquear indefinidamente el arranque. Si falla NTP no enviará mediciones; revisa que la red permita UDP 123. Si cambia la cadena de certificados del endpoint, actualiza la CA.

### Prueba con Docker local

Cambia `USE_LOCAL_SERVER` a `true` y `LOCAL_API_BASE_URL` por la IP LAN de tu computadora, por ejemplo `http://10.42.0.1:8080` (hotspot Fedora). El ESP32 no puede usar `localhost` ni el nombre Docker `receiver`. En local utiliza HTTP y `/control/status/led1` y `/control/status/led2`; en AWS utiliza HTTPS y `/control?led_id=...`. La opción local también requiere acceso a NTP.

## 6. Preparación y prueba del sistema

1. **Base de datos existente:** ejecuta [database/migrations/001_motor_voltage_range.sql](database/migrations/001_motor_voltage_range.sql) en PostgreSQL local o RDS. Las columnas anteriores `NUMERIC(3,2)` rechazan voltajes de 10 V o superiores. Las instalaciones nuevas usan `NUMERIC(6,2)` en `init.sql`. No borres el volumen para aplicar este cambio.
2. **Grafana:** importa el dashboard actualizado (el medidor del canal 1 ahora cubre 0–16 V). Detén el simulador durante la prueba física (`docker compose stop simulator`), pues las consultas actuales muestran la última medición de cualquier dispositivo.
3. **Conexiones:** comienza con una fuente DC conocida y verifica la lectura con multímetro. El módulo comercial llamado “0–25V” con divisor 5:1 **no permite conectar 24/25 V al ESP32**: produciría 4.8/5 V. El ADC del ESP32 clásico a 11 dB mide aproximadamente hasta 3.1 V; con divisor 5:1 corresponde a unos 15.5 V, dejando margen para transitorios. El límite absoluto de 3.3 V no equivale al rango útil de medición. Para 24 V rediseña el divisor y cambia `DIVIDER_FACTOR`.
4. **Monitor serial:** comprueba IP, sincronización de hora y `[TELEMETRIA] OK (200)`. Un código 400/403/500 se imprime como error, junto con la respuesta del servidor.
5. **Control:** conmuta `led1` y `led2` en Grafana y verifica GPIO 2 y 4 respectivamente. Ante una respuesta JSON inválida los pines mantienen su estado; no se apagan por un valor ausente.
6. **Reconexión:** apaga y vuelve a activar la red `prueba`; verifica que el dispositivo se reconecte y reanude los envíos.

La compilación verifica las APIs y el enlace para la placa seleccionada. La precisión del sensor, la conexión a esa red y el recorrido ESP32 → AWS → PostgreSQL → Grafana requieren la prueba física anterior.

---
## 7. Solución de Problemas Frecuentes

* **Error `HTTP -1 / Connection Refused` en AWS:** Verifica que tu Invoke URL de API Gateway termine en `/prod` (o el nombre de tu Stage) y que el método POST en `/telemetry` esté desplegado.
* **El ESP32 no conecta al Wi-Fi:** Recuerda que la red/Hotspot debe emitir en **2.4 GHz**.
* **Lecturas de voltaje inestables:** Coloca un capacitor cerámico de $100\text{nF}$ entre el pin analógico (GPIO 34) y GND.
