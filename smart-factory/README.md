# Sistema Educativo de Telemetría IoT (Smart-Factory)

Este proyecto emula la telemetría de una planta industrial, transmitiendo datos simulados a la nube y visualizándolos en Grafana. Consta de 4 capas principales:

1. **Capa de Simulación**: Script en Python ejecutado en Docker que genera señales analógicas y digitales emulando sensores industriales.
2. **Capa de Transporte**: Envío de los payloads JSON mediante peticiones HTTP POST a un endpoint de AWS (API Gateway + Lambda).
3. **Capa de Almacenamiento**: Base de datos PostgreSQL en AWS RDS, optimizada para series de tiempo.
4. **Capa de Visualización**: Tablero en Grafana para monitorear en tiempo real los voltajes y estados lógicos de la maquinaria.

## Requisitos y Configuración en Windows (WSL2)

El desarrollo está pensado para ejecutarse sobre Windows utilizando **WSL2** (Ubuntu/Debian) y **Docker Desktop**.

### 1. Activar integración de Docker con WSL2
- Instala Docker Desktop en Windows.
- Ve a **Settings > Resources > WSL Integration**.
- Asegúrate de habilitar la integración con tu distribución activa (ej. Ubuntu).

### 2. Variables de entorno
Copia el archivo `.env.example` a `.env` y configura tus variables locales (no subas el `.env` al repositorio):
```bash
cp .env.example .env
```

### 3. Ejecutar el Simulador
Desde la terminal de WSL, navega al directorio del simulador y ejecuta:

```bash
cd simulator
docker build -t smart-factory-simulator .
docker run --env-file ../.env smart-factory-simulator
```
La variable de entorno `PYTHONUNBUFFERED=1` en el contenedor garantiza que los logs de telemetría se impriman inmediatamente sin buffering.
