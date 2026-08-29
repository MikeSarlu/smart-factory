# Sistema Educativo de Telemetría IoT (Smart-Factory)

Este proyecto emula la telemetría de una planta industrial, transmitiendo datos simulados a la nube y visualizándolos en Grafana. Consta de 4 capas principales:

1. **Capa de Simulación**: Script en Python ejecutado en Docker (o directamente) que genera señales analógicas y digitales emulando sensores industriales.
2. **Capa de Transporte**: Envío de los payloads JSON mediante peticiones HTTP POST a un endpoint de AWS (API Gateway + Lambda) o un receptor local.
3. **Capa de Almacenamiento**: Base de datos PostgreSQL (local o en AWS RDS), optimizada para series de tiempo.
4. **Capa de Visualización**: Tablero en Grafana para monitorear en tiempo real los voltajes y estados lógicos de la maquinaria.

---

## Solo quiero ver el proyecto en funcionamiento

Si te han compartido una URL del dashboard de Grafana público y quieres ver la demostración funcionando en tiempo real o interactuar con el simulador, sigue estos pasos:

1. Entra a la URL pública de Grafana (ej. `http://<IP-EC2>:3000`).
2. Inicia sesión con las credenciales proporcionadas.
3. Para ver el hardware simulado reaccionar a tus comandos desde Grafana, solo necesitas correr el simulador en tu computadora. Necesitarás tener Python instalado:

   ```bash
   # 1. Clona o descarga este repositorio y entra a la carpeta
   git clone <url-del-repositorio>
   cd smart-factory
   
   # 2. Instala la dependencia necesaria
   pip install requests
   
   # 3. Configura las URLs del API de AWS (pide estos enlaces al creador del proyecto)
   
   # -- En Linux/macOS/GitBash:
   export API_GATEWAY_URL="<URL_PROPORCIONADA_DE_TELEMETRY>"
   export CONTROL_URL="<URL_PROPORCIONADA_DE_CONTROL>"
   
   # -- En Windows (PowerShell):
   $env:API_GATEWAY_URL="<URL_PROPORCIONADA_DE_TELEMETRY>"
   $env:CONTROL_URL="<URL_PROPORCIONADA_DE_CONTROL>"
   
   # 4. Inicia el simulador
   python simulator/src/main.py
   ```
Verás en tu consola cómo se envían los datos. Cuando aprietes "Enviar Comandos al Hardware" en el Grafana web, verás en tu consola cómo el hardware simulado enciende o apaga sus LEDs.

---

## Replicar el Proyecto en tu Computadora (Localmente)

Si quieres levantar todo el ecosistema en tu propia computadora para desarrollo o pruebas (sin gastar en AWS), la forma más sencilla es usar Docker. Esto levantará la base de datos, un receptor web (simulando API Gateway), el simulador y Grafana auto-configurado.

### Requisitos Previos
* **Docker** y **Docker Compose** instalados. (En Windows se recomienda Docker Desktop con integración WSL2).
* **Git**.

### Pasos para levantar el entorno

1. **Clonar el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd smart-factory
   ```

2. **Configurar las variables de entorno:**
   Crea tu archivo `.env` a partir del ejemplo:
   ```bash
   # En Linux/macOS o Git Bash
   cp .env.example .env
   
   # En Windows PowerShell
   Copy-Item .env.example .env
   ```

3. **Levantar los servicios:**
   Ejecuta el siguiente comando para construir y levantar todos los contenedores:
   ```bash
   docker compose up --build
   ```

4. **Acceder a Grafana Local:**
   * Abre tu navegador en [http://localhost:3000](http://localhost:3000)
   * **Usuario:** `admin`
   * **Contraseña:** `admin`
   * El dashboard llamado "Panel de Telemetría de Smart-Factory" ya estará conectado a la base de datos y mostrando los datos del simulador automáticamente.

---

## Despliegue en AWS

Para desplegar la infraestructura real en la nube utilizando AWS (API Gateway, Lambda, RDS y EC2), sigue estos pasos detallados:

### Paso 1: Configurar la Base de Datos RDS (PostgreSQL)
1. **Crear Instancia:** En la consola de AWS, ve a **RDS** y crea una base de datos PostgreSQL. Asegúrate de configurar un usuario maestro y una contraseña segura.
2. **Acceso Público:** Si vas a conectarte desde tu computadora local o un EC2 externo, asegúrate de que la base de datos tenga **Public Access** habilitado (o esté en la misma VPC que tu EC2) y que el **Security Group** permita tráfico entrante en el puerto `5432` desde tu IP.
3. **Inicializar Tablas:**
   * Usa un cliente SQL (como DBeaver, pgAdmin o la extensión de VS Code).
   * Conéctate usando el **Endpoint** que te da RDS, el usuario maestro y la contraseña.
   * Ejecuta el contenido completo del archivo [database/init.sql](database/init.sql) para crear las tablas `telemetry_data` y `control_commands`.

### Paso 2: Empaquetar y Desplegar las Lambdas
Dado que las funciones Lambda necesitan la librería `psycopg2` para conectarse a PostgreSQL, no puedes simplemente copiar y pegar el código en la consola web de AWS. Debes subir un archivo `.zip` con las dependencias precompiladas.

1. **Crear las Funciones en AWS:**
   * Ve a **AWS Lambda** y crea dos funciones desde cero con runtime **Python 3.12** (o similar):
     * `SmartFactoryTelemetry` (para procesar datos).
     * `SmartFactoryControl` (para los comandos de los LEDs).
2. **Empaquetar el Código:** 
   * En tu computadora, asegúrate de tener Docker instalado y ejecutándose.
   * Ejecuta el script de empaquetado incluido en este repositorio:
     ```bash
     python build_lambda_zip.py
     ```
   * Esto utilizará Docker para descargar las librerías binarias correctas de `psycopg2` para el entorno de Amazon Linux y creará un archivo llamado `lambda_package.zip`.
3. **Subir el ZIP:**
   * Entra a la configuración de cada una de tus dos Lambdas en AWS.
   * En la pestaña **Code**, elige **Upload from -> .zip file** y sube el `lambda_package.zip`.
   * En los ajustes de **Runtime settings**, haz clic en **Edit** y cambia el **Handler** de la siguiente manera:
     * Para `SmartFactoryTelemetry`, el handler debe ser: `aws.lambda_function.lambda_handler`
     * Para `SmartFactoryControl`, el handler debe ser: `aws.lambda_control.lambda_handler`
4. **Variables de Entorno:**
   * En la pestaña **Configuration > Environment variables** de ambas Lambdas, agrega:
     * `DB_HOST`: El Endpoint de tu instancia RDS.
     * `DB_NAME`: El nombre de tu base de datos (por defecto `postgres`).
     * `DB_USER`: Tu usuario.
     * `DB_PASSWORD`: Tu contraseña.
     * `DB_PORT`: `5432`

### Paso 3: Configurar API Gateway
1. **Crear API REST:** Ve a **API Gateway** y crea una nueva **REST API** (no HTTP API).
2. **Crear Recursos y Métodos:**
   * Crea un recurso llamado `/telemetry`.
     * Dentro, crea un método **POST**. En "Integration type" selecciona **Lambda Function** y elige tu lambda `SmartFactoryTelemetry`. Activa **Use Lambda Proxy integration**.
   * Crea un recurso llamado `/control`.
     * Dentro, crea un método **GET** apuntando a `SmartFactoryControl` (con Proxy Integration).
     * Crea un método **POST** apuntando a `SmartFactoryControl` (con Proxy Integration).
3. **Habilitar CORS:**
   * Selecciona el recurso `/control`, haz clic en **Enable CORS** y acepta las configuraciones por defecto. Esto es crucial para que Grafana pueda enviar solicitudes (POST) desde el navegador sin ser bloqueado.
4. **Desplegar la API:**
   * Haz clic en **Deploy API**, crea un nuevo Stage (ej. `prod`) y despliega.
   * AWS te dará una **Invoke URL** (ej. `https://xxxx.execute-api.us-east-2.amazonaws.com/prod`).

### Paso 4: Configurar Grafana (EC2)
1. Instala Grafana en una instancia EC2 (Asegúrate de abrir el puerto `3000` en el Security Group de la EC2).
2. Entra a `http://<IP-EC2>:3000` con `admin/admin`.
3. Ve a **Connections > Data Sources > Add data source** y elige **PostgreSQL**. Configura la conexión a tu RDS. **Obligatorio:** Selecciona SSL Mode en `require`.
4. Ve a **Dashboards > Import** y sube el archivo [grafana/dashboard.json](grafana/dashboard.json).
5. Abre las configuraciones del dashboard (Configuración -> Variables) y cambia el valor de la variable `control_url` por tu URL de API Gateway completa terminada en `/control` (ej. `https://xxxx.execute-api.us-east-2.amazonaws.com/prod/control`).

### Paso 5: Apuntar el Simulador a la Nube
Finalmente, configura el simulador de tu computadora para que envíe los datos a AWS en lugar del entorno local:
1. Abre tu archivo `.env`.
2. Actualiza las variables con tu Invoke URL:
   ```bash
   API_GATEWAY_URL=https://xxxx.execute-api.us-east-2.amazonaws.com/prod/telemetry
   CONTROL_URL=https://xxxx.execute-api.us-east-2.amazonaws.com/prod/control
   ```
3. Ejecuta el simulador:
   ```bash
   docker compose up --build simulator
   ```
   ¡Listo! El simulador ahora está enviando telemetría real a tu RDS en AWS, y tu dashboard público de Grafana está visualizando esos datos y enviando comandos a través del API Gateway.