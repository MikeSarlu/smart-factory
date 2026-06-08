-- Tabla optimizada para datos de telemetría de series de tiempo
CREATE TABLE IF NOT EXISTS telemetry_data (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    analog_ch1 NUMERIC(3,2),
    analog_ch2 NUMERIC(3,2),
    digital_ch1 SMALLINT,
    digital_ch2 SMALLINT,
    digital_ch3 SMALLINT,
    digital_ch4 SMALLINT,
    digital_ch5 SMALLINT
);

-- Índice compuesto para agilizar las consultas por dispositivo y rango de tiempo en Grafana
CREATE INDEX IF NOT EXISTS idx_telemetry_device_time 
ON telemetry_data (device_id, timestamp DESC);
