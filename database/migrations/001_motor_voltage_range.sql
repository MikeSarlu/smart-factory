-- Ejecutar una vez en bases existentes (Docker o RDS).
-- init.sql solo se ejecuta al crear un volumen nuevo.
BEGIN;
ALTER TABLE telemetry_data
    ALTER COLUMN analog_ch1 TYPE NUMERIC(6,2),
    ALTER COLUMN analog_ch2 TYPE NUMERIC(6,2);
COMMIT;
