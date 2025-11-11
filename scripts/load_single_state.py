#!/usr/bin/env python3
"""
Script para cargar UN SOLO estado de SEPOMEX e INEGI (prueba rápida)
"""

import os
import subprocess
import zipfile
from pathlib import Path
import psycopg2

# Configuración
DB_CONFIG = {
    'host': os.getenv('PGHOST', '/var/run/postgresql'),  # Unix socket directory
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'cp2ageb'),
    'user': os.getenv('POSTGRES_USER', 'geouser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'geopassword')
}

# Aguascalientes como estado de prueba
CVE_ENT = "01"
ESTADO_NOMBRE = "Aguascalientes"
SEPOMEX_ZIP = "/data/cp_shapefiles/CP_Ags.zip"
INEGI_ZIP = "/data/ageb_shapefiles/01_aguascalientes.zip"


def extract_zip(zip_path: Path, extract_to: Path) -> list:
    """Extrae archivo ZIP y retorna lista de archivos .shp"""
    print(f"  Extrayendo {zip_path.name}... ", end="", flush=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        shp_files = list(extract_to.rglob("*.shp"))
        print(f"✓ ({len(shp_files)} shapefiles)")
        return shp_files
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def load_shapefile_to_postgis(shp_file: Path, schema: str, table_name: str, transform_to_srid: int = None) -> bool:
    """Carga un shapefile a PostGIS usando ogr2ogr"""
    try:
        print(f"    Cargando {shp_file.name} → {schema}.{table_name}... ", end="", flush=True)

        # Build connection string - omit host if empty (Unix socket)
        if DB_CONFIG['host']:
            pg_conn = f"PG:host={DB_CONFIG['host']} port={DB_CONFIG['port']} "
        else:
            pg_conn = f"PG:port={DB_CONFIG['port']} "

        pg_conn += (f"dbname={DB_CONFIG['database']} user={DB_CONFIG['user']} "
                    f"password={DB_CONFIG['password']}")

        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            pg_conn,
            str(shp_file),
            "-nln", f"{schema}.{table_name}",
            "-nlt", "PROMOTE_TO_MULTI",  # Promover todas las geometrías a Multi* para evitar conflictos
            "-lco", "GEOMETRY_NAME=geom",
            "-lco", f"SCHEMA={schema}",
            "-overwrite",
            "-skipfailures"
        ]

        # Transformar SRID si se especifica (para unificar INEGI con SEPOMEX)
        if transform_to_srid:
            cmd.extend(["-t_srs", f"EPSG:{transform_to_srid}"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("✓")
            return True
        else:
            error_msg = result.stderr.split('\n')[0] if result.stderr else "Unknown error"
            print(f"✗ {error_msg[:80]}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    print("=" * 70)
    print(f"  Carga Rápida - {ESTADO_NOMBRE}")
    print("=" * 70)

    temp_dir = Path("/tmp/test_load")
    temp_dir.mkdir(exist_ok=True)

    exitosos = 0
    fallidos = 0

    # 1. Cargar SEPOMEX (Códigos Postales)
    print(f"\n[SEPOMEX] Cargando códigos postales...")
    sepomex_dir = temp_dir / "sepomex"
    sepomex_dir.mkdir(exist_ok=True)

    shp_files = extract_zip(Path(SEPOMEX_ZIP), sepomex_dir)
    for shp_file in shp_files:
        table_name = f"cp_{CVE_ENT}_{shp_file.stem.lower()}"
        # Cargar con proyección nativa (ambos usan Lambert Conformal Conic)
        if load_shapefile_to_postgis(shp_file, "sepomex", table_name):
            exitosos += 1
        else:
            fallidos += 1

    subprocess.run(["rm", "-rf", str(sepomex_dir)], check=False)

    # 2. Cargar INEGI (AGEBs, Manzanas, etc.)
    print(f"\n[INEGI] Cargando Marco Geoestadístico...")
    inegi_dir = temp_dir / "inegi"
    inegi_dir.mkdir(exist_ok=True)

    shp_files = extract_zip(Path(INEGI_ZIP), inegi_dir)
    for shp_file in shp_files:
        stem_lower = shp_file.stem.lower()

        # Clasificar por nombre de archivo
        if stem_lower == f"{CVE_ENT.lower()}a":
            geom_type = 'ageb_urbana'
        elif stem_lower == f"{CVE_ENT.lower()}ar":
            geom_type = 'ageb_rural'
        elif stem_lower == f"{CVE_ENT.lower()}m":
            geom_type = 'manzana'
        elif stem_lower in [f"{CVE_ENT.lower()}l", f"{CVE_ENT.lower()}lpr"]:
            geom_type = 'localidad'
        elif stem_lower == f"{CVE_ENT.lower()}mun":
            geom_type = 'municipio'
        elif stem_lower in [f"{CVE_ENT.lower()}ent", f"{CVE_ENT.lower()}e"]:
            geom_type = 'entidad'
        else:
            print(f"    Omitiendo {shp_file.name} (tipo desconocido)")
            continue

        table_name = f"{geom_type}_{CVE_ENT}"
        # INEGI usa SRID 900916 nativo (no requiere transformación)
        if load_shapefile_to_postgis(shp_file, "inegi", table_name):
            exitosos += 1
        else:
            fallidos += 1

    subprocess.run(["rm", "-rf", str(inegi_dir)], check=False)

    # Resumen
    print("\n" + "=" * 70)
    print(f"  Total - Exitosos: {exitosos}, Fallidos: {fallidos}")
    print("=" * 70)

    # Verificar tablas cargadas
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sepomex';")
        sepomex_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='inegi';")
        inegi_count = cur.fetchone()[0]

        print(f"\nTablas en base de datos:")
        print(f"  - SEPOMEX: {sepomex_count} tablas")
        print(f"  - INEGI: {inegi_count} tablas")

        # Listar tablas INEGI
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='inegi' ORDER BY table_name;")
        inegi_tables = [row[0] for row in cur.fetchall()]
        print(f"\nTablas INEGI creadas:")
        for table in inegi_tables:
            print(f"  - {table}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error verificando tablas: {e}")


if __name__ == "__main__":
    main()
