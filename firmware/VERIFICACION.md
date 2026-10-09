# Verificación ESP32 — 2026-10-08

## Resultado

Compilación correcta para `esp32:esp32:esp32` (ESP32 Dev Module clásico), con
Espressif Arduino 3.3.2 y ArduinoJson 6.21.5:

```text
Sketch uses 1060379 bytes (80%) of program storage space. Maximum is 1310720 bytes.
Global variables use 47064 bytes (14%) of dynamic memory, leaving 280616 bytes for local variables.
```

Comando usado desde la raíz del proyecto (herramientas locales de esta revisión):

```powershell
.tools/arduino-cli/arduino-cli.exe compile --fqbn esp32:esp32:esp32 --warnings all --build-path firmware/build --config-file .tools/arduino-cli.yaml firmware/smart_factory
```

El binario de aplicación está en `firmware/build/smart_factory.ino.bin`.
Para subir desde Arduino IDE abre `smart_factory/smart_factory.ino`, con su
archivo `amazon_root_ca.h` en la misma carpeta. Selecciona placa y puerto USB.
No se ha flasheado ni probado una placa física en esta revisión.

## Bloqueo observado en AWS

Consulta de solo lectura al endpoint configurado en la guía, `.env` y Grafana:

```text
GET https://wrsbsxcc03.execute-api.us-east-2.amazonaws.com/prod/control?led_id=led1
HTTP 403
{"message":"Missing Authentication Token"}
```

Ese resultado no demuestra por sí solo la causa. Revisa que exista el método
GET en `/control`, esté vinculado a `SmartFactoryControl` con integración proxy,
que los cambios estén desplegados en `prod` y que la configuración de autorización
permita este cliente. Confirma también que la URL siga vigente.
La respuesta esperada es HTTP 200 con `{"led_id":"led1","state":0}` (o estado 1).
No se enviaron comandos ni telemetría de prueba a la nube.

## Cambios necesarios para el motor real

- Red configurada: `prueba` / `prueba123`, banda 2.4 GHz.
- Firmware extraído de la guía a un sketch compilable; control para led1/GPIO2 y led2/GPIO4.
- ADC calibrado en milivoltios, atenuación explícita, divisor 5:1.
- Reconexión Wi-Fi, tiempos límite de red y fechas UTC reales por NTP.
- HTTPS con CA de Amazon; errores HTTP y JSON tratados explícitamente.
- Columnas analógicas ampliadas a `NUMERIC(6,2)`. Aplica
  `database/migrations/001_motor_voltage_range.sql` a una base existente.
- Medidor de Grafana del canal 1 ampliado a 16 V, umbrales 12.5/13.5 V.

El contrato JSON del firmware coincide con los campos consumidos por
`aws/lambda_function.py`. Las URLs de consulta de LEDs distinguen AWS y Flask local.
No se ejecutó una prueba de inserción SQL: Docker no estaba activo y no se accedió
a RDS. La migración y el dashboard no se aplicaron a servicios externos.

## Pendiente en hardware

Sigue la sección 6 de `ESP32_INTEGRATION_GUIDE.md`: aplicar migración, corregir
el endpoint AWS, detener el simulador, verificar tensión con multímetro, probar
ambos LEDs y cortar/restaurar Wi-Fi. Las consultas actuales de Grafana no filtran
por dispositivo; un simulador activo puede ocultar las mediciones del ESP32.

El receptor local devuelve estado 0 y HTTP 200 si falla su consulta de control a
PostgreSQL (`receiver/src/app.py`). Ese comportamiento preexistente puede apagar
un LED ante un fallo de base de datos; tenlo presente al probar la opción local.
El firmware está pensado para LEDs; no constituye control seguro de un motor o relé.

Referencia ADC: https://docs.espressif.com/projects/arduino-esp32/en/latest/api/adc.html
La API `analogReadMilliVolts` entrega una lectura calibrada. Para ESP32 clásico
con 11 dB el rango documentado llega aproximadamente a 3.1 V (15.5 V con divisor 5:1).
No conectes una fuente de 24/25 V a ese divisor: superaría el límite del pin.
