"""
Script para construir el paquete de despliegue de AWS Lambda.
Descarga psycopg2-binary precompilado para Linux x86_64 (compatible con AWS Lambda)
y lo empaqueta junto con lambda_function.py y lambda_control.py en un archivo ZIP.

CÓMO USARLO:
    python build_lambda_zip.py

RESULTADO:
    Genera el archivo dist/lambda_deployment.zip listo para subir a AWS Lambda.
"""

import os
import sys
import urllib.request
import zipfile
import shutil
import tempfile

# ── Configuración ──────────────────────────────────────────────────────────────
# Wheel de psycopg2 precompilado para AWS Lambda (Python 3.12, Linux x86_64 manylinux2014)
PSYCOPG2_WHEEL_URL = (
    "https://files.pythonhosted.org/packages/b8/01/"
    "5d20773d2745e57140e74b3353e1f0e42d76f8749a468d6f54664c1cd869/"
    "psycopg2_binary-2.9.9-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
)

# Archivos de código a incluir en el ZIP
LAMBDA_FILES = [
    os.path.join("aws", "lambda_function.py"),
    os.path.join("aws", "lambda_control.py"),
]

# Carpeta de salida y nombre del ZIP
DIST_DIR = "dist"
ZIP_NAME = "lambda_deployment.zip"
ZIP_PATH = os.path.join(DIST_DIR, ZIP_NAME)
# ──────────────────────────────────────────────────────────────────────────────


def print_step(n, msg):
    print(f"\n[Paso {n}] {msg}")


def download_wheel(url: str, dest_path: str):
    print(f"  Descargando: {url}")
    urllib.request.urlretrieve(url, dest_path)
    print(f"  Descargado en: {dest_path}")


def extract_wheel(wheel_path: str, extract_dir: str):
    """Un archivo .whl es un ZIP renombrado; lo extraemos directamente."""
    print(f"  Extrayendo wheel en: {extract_dir}")
    with zipfile.ZipFile(wheel_path, "r") as whl:
        # Solo extraemos el paquete psycopg2 (no los metadatos)
        members = [m for m in whl.namelist() if m.startswith("psycopg2")]
        whl.extractall(extract_dir, members=members)
    print(f"  Extraídos {len(members)} archivos del wheel.")


def build_zip(source_dir: str, lambda_files: list, zip_path: str):
    print(f"  Creando ZIP en: {zip_path}")
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Añadir todos los archivos de psycopg2
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname = os.path.relpath(abs_path, source_dir)
                zf.write(abs_path, arcname)

        # Añadir los scripts Lambda en la raíz del ZIP
        for lf in lambda_files:
            if os.path.exists(lf):
                arcname = os.path.basename(lf)
                zf.write(lf, arcname)
                print(f"  Añadido: {arcname}")
            else:
                print(f"  ADVERTENCIA: No se encontró el archivo {lf}")

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n  [OK] ZIP generado exitosamente: {zip_path} ({size_mb:.2f} MB)")


def main():
    # Verificar que estamos en la raíz del proyecto
    if not os.path.exists("aws"):
        print("ERROR: Ejecuta este script desde la raíz del proyecto (la carpeta que contiene /aws).")
        sys.exit(1)

    # Buscar el wheel de psycopg2 ya descargado en dist/wheels/
    wheels_dir = os.path.join("dist", "wheels")
    wheel_files = [f for f in os.listdir(wheels_dir) if f.startswith("psycopg2_binary") and f.endswith(".whl")]
    if not wheel_files:
        print(f"ERROR: No se encontró el wheel de psycopg2 en '{wheels_dir}'.")
        print("Ejecuta primero: python -m pip download psycopg2-binary==2.9.9 --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all: --no-deps -d dist/wheels")
        sys.exit(1)

    wheel_path = os.path.join(wheels_dir, wheel_files[0])
    print(f"[Paso 1] Usando wheel descargado: {wheel_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        extract_dir = os.path.join(tmpdir, "packages")
        os.makedirs(extract_dir, exist_ok=True)

        print_step(2, "Extrayendo los binarios de psycopg2...")
        extract_wheel(wheel_path, extract_dir)

        print_step(3, f"Empaquetando todo en {ZIP_PATH}...")
        build_zip(extract_dir, LAMBDA_FILES, ZIP_PATH)

    print("\n" + "="*60)
    print("  SIGUIENTE PASO:")
    print(f"  Sube el archivo '{ZIP_PATH}' a tu función Lambda en AWS.")
    print("="*60)


if __name__ == "__main__":
    main()
