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

### 3. Ejecutar el Entorno Completo Local (Docker Compose)
Para levantar todo el ecosistema (PostgreSQL, Receptor Mock de Lambda, Simulador de Telemetría y Grafana auto-configurado):

Desde la terminal (PowerShell o WSL), ejecuta:
```bash
docker compose up --build
```

Esto levantará los siguientes servicios de manera automática:
* **PostgreSQL** (`localhost:5432`): Inicializado con la estructura de tablas de `init.sql`.
* **Mock Receiver** (`localhost:8080`): Expone la ruta `/telemetry` que recibe datos y ejecuta la lógica de `aws/lambda_function.py` localmente.
* **Simulator**: Empieza a generar la telemetría e hilos de datos y los envía al receptor.
* **Grafana** (`localhost:3000`): Inicia con el DataSource de PostgreSQL pre-configurado y el dashboard precargado de forma automática (credenciales por defecto: `admin/admin`).

