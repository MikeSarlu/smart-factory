--Tabla optimizada para datos de telemetría de series de tiempo
CREATE TABLE IF NOT EXISTS telemetry_data (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    analog_ch1 NUMERIC(6,2),
    analog_ch2 NUMERIC(6,2),
    digital_ch1 SMALLINT,
    digital_ch2 SMALLINT,
    digital_ch3 SMALLINT,
    digital_ch4 SMALLINT,
    digital_ch5 SMALLINT
);

--Índice compuesto para agilizar las consultas por dispositivo y rango de tiempo en Grafana
CREATE INDEX IF NOT EXISTS idx_telemetry_device_time 
ON telemetry_data (device_id, timestamp DESC);

--Tabla para los comandos de control enviados desde el dashboard de Grafana
--Permite encender o apagar LEDs/actuadores en el hardware real o simulado
CREATE TABLE IF NOT EXISTS control_commands (
    id SERIAL PRIMARY KEY,
    command_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    led_id VARCHAR(20) NOT NULL,       --Identificador del LED: 'led1' o 'led2'
    state SMALLINT NOT NULL,           --Estado deseado: 1=ENCENDIDO, 0=APAGADO
    source VARCHAR(50) DEFAULT 'grafana' --Origen del comando
);

--Índice para consultar el estado más reciente de cada LED rápidamente
CREATE INDEX IF NOT EXISTS idx_control_led_time
ON control_commands (led_id, command_timestamp DESC);
