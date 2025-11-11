#!/usr/bin/env python3
"""
Script para cargar shapefiles de SEPOMEX e INEGI a la base de datos PostGIS
"""

import os
import sys
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime
import psycopg2

# Configuración de base de datos (desde variables de entorno o valores por defecto)
DB_CONFIG = {
    'host': os.getenv('PGHOST', '/var/run/postgresql'),  # Unix socket directory
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'cp2ageb'),
    'user': os.getenv('POSTGRES_USER', 'geouser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'geopassword')
}

# Control de capas a cargar (desde variables de entorno)
LOAD_LAYERS = {
    'agebs': os.getenv('LOAD_AGEBS', 'true').lower() == 'true',
    'manzanas': os.getenv('LOAD_MANZANAS', 'false').lower() == 'true',
    'localidades': os.getenv('LOAD_LOCALIDADES', 'false').lower() == 'true',
    'municipios': os.getenv('LOAD_MUNICIPIOS', 'false').lower() == 'true',
    'entidades': os.getenv('LOAD_ENTIDADES', 'false').lower() == 'true',
}

# Control de validación de ZIPs (desde variable de entorno)
# "quick" = solo verificar que se puede abrir (rápido, por defecto)
# "full" = verificar integridad completa con testzip() (lento pero exhaustivo)
# "none" = sin validación
VALIDATE_ZIPS = os.getenv('VALIDATE_ZIPS', 'quick').lower()

# Control de sobrescritura de tablas existentes (desde variable de entorno)
# "false" (default) = saltar tablas que ya existen en la DB (rápido)
# "true" = sobrescribir todas las tablas
FORCE_RELOAD = os.getenv('FORCE_RELOAD', 'false').lower() == 'true'

# Control de estados a cargar (desde variables de entorno)
# Formato: "01,02,03" o "Ags,BC,BCS" o "Aguascalientes,Baja California"
# Vacío o "all" = todos los estados
LOAD_ESTADOS_ENV = os.getenv('LOAD_ESTADOS', 'all').strip()

# Mapeo de estados para SEPOMEX
ESTADOS_SEPOMEX = {
    "01": ("Ags", "Aguascalientes"),
    "02": ("BC", "Baja California"),
    "03": ("BCS", "Baja California Sur"),
    "04": ("Camp", "Campeche"),
    "05": ("Coah", "Coahuila"),
    "06": ("Col", "Colima"),
    "07": ("Chis", "Chiapas"),
    "08": ("Chih", "Chihuahua"),
    "09": ("CDMX", "Ciudad de México"),
    "10": ("Dgo", "Durango"),
    "11": ("Gto", "Guanajuato"),
    "12": ("Gro", "Guerrero"),
    "13": ("Hgo", "Hidalgo"),
    "14": ("Jal", "Jalisco"),
    "15": ("Mex", "Estado de México"),
    "16": ("Mich", "Michoacán"),
    "17": ("Mor", "Morelos"),
    "18": ("Nay", "Nayarit"),
    "19": ("NL", "Nuevo León"),
    "20": ("Oax", "Oaxaca"),
    "21": ("Pue", "Puebla"),
    "22": ("Qro", "Querétaro"),
    "23": ("QRoo", "Quintana Roo"),
    "24": ("SLP", "San Luis Potosí"),
    "25": ("Sin", "Sinaloa"),
    "26": ("Son", "Sonora"),
    "27": ("Tab", "Tabasco"),
    "28": ("Tamps", "Tamaulipas"),
    "29": ("Tlax", "Tlaxcala"),
    "30": ("Ver", "Veracruz"),
    "31": ("Yuc", "Yucatán"),
    "32": ("Zac", "Zacatecas"),
}

# Mapeo de estados para INEGI
ESTADOS_INEGI = {
    "01": "aguascalientes",
    "02": "bajacalifornia",
    "03": "bajacaliforniasur",
    "04": "campeche",
    "05": "coahuiladezaragoza",
    "06": "colima",
    "07": "chiapas",
    "08": "chihuahua",
    "09": "ciudaddemexico",
    "10": "durango",
    "11": "guanajuato",
    "12": "guerrero",
    "13": "hidalgo",
    "14": "jalisco",
    "15": "mexico",
    "16": "michoacandeocampo",
    "17": "morelos",
    "18": "nayarit",
    "19": "nuevoleon",
    "20": "oaxaca",
    "21": "puebla",
    "22": "queretaro",
    "23": "quintanaroo",
    "24": "sanluispotosi",
    "25": "sinaloa",
    "26": "sonora",
    "27": "tabasco",
    "28": "tamaulipas",
    "29": "tlaxcala",
    "30": "veracruzignaciodelallave",
    "31": "yucatan",
    "32": "zacatecas",
}


def normalize_estado(estado_input: str) -> str:
    """
    Normaliza diferentes formatos de estado a código de 2 dígitos.

    Formatos aceptados:
    - "1" o "01" -> "01"
    - "Ags" o "ags" -> "01"
    - "Aguascalientes" o "aguascalientes" -> "01"

    Returns:
        Código de estado de 2 dígitos o None si no se encuentra
    """
    estado = estado_input.strip()

    # Formato numérico (1 o 01)
    if estado.isdigit():
        cve = estado.zfill(2)  # Rellenar con ceros a la izquierda
        if cve in ESTADOS_SEPOMEX:
            return cve
        return None

    # Convertir a lowercase para comparación
    estado_lower = estado.lower()

    # Buscar por abreviatura o nombre completo
    for cve_ent, (abbr, nombre) in ESTADOS_SEPOMEX.items():
        if estado_lower == abbr.lower() or estado_lower == nombre.lower():
            return cve_ent

    # Buscar por nombre de archivo INEGI
    for cve_ent, nombre_archivo in ESTADOS_INEGI.items():
        if estado_lower == nombre_archivo.lower():
            return cve_ent

    return None


def parse_estados_filter() -> set:
    """
    Parsea la variable de entorno LOAD_ESTADOS y retorna conjunto de códigos.

    Returns:
        Set de códigos de estado de 2 dígitos, o None si se deben cargar todos
    """
    if not LOAD_ESTADOS_ENV or LOAD_ESTADOS_ENV.lower() == 'all':
        return None  # Cargar todos

    estados = set()
    for item in LOAD_ESTADOS_ENV.split(','):
        item = item.strip()
        if not item:
            continue

        cve = normalize_estado(item)
        if cve:
            estados.add(cve)
        else:
            print(f"⚠ Estado no reconocido: '{item}' (ignorado)")

    return estados if estados else None


# Parsear estados al iniciar
ESTADOS_FILTER = parse_estados_filter()


def table_exists(schema: str, table_name: str) -> bool:
    """Verifica si una tabla existe en la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = %s
            )
        """, (schema, table_name))

        exists = cur.fetchone()[0]

        cur.close()
        conn.close()

        return exists
    except Exception as e:
        # En caso de error, asumir que no existe para intentar cargar
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> list:
    """Extrae archivo ZIP y retorna lista de archivos .shp

    Si el archivo ZIP está corrupto, lo elimina para permitir re-descarga.

    Modos de validación (variable VALIDATE_ZIPS):
    - "quick" (default): Validación rápida - solo verifica que se puede abrir
    - "full": Validación completa - ejecuta testzip() en todos los archivos (lento)
    - "none": Sin validación - solo extrae
    """
    print(f"  Extrayendo {zip_path.name}... ", end="", flush=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Validación según modo configurado
            if VALIDATE_ZIPS == 'full':
                # Validación completa (lenta pero exhaustiva)
                bad_file = zip_ref.testzip()
                if bad_file:
                    raise zipfile.BadZipFile(f"Archivo corrupto en ZIP: {bad_file}")
            elif VALIDATE_ZIPS == 'quick':
                # Validación rápida: verificar que namelist() funciona
                # Esto detecta ZIPs totalmente corruptos sin verificar cada archivo interno
                if not zip_ref.namelist():
                    raise zipfile.BadZipFile("ZIP vacío o corrupto")
            # Si es 'none', no validar (más rápido pero sin verificación)

            zip_ref.extractall(extract_to)

        # Buscar archivos .shp
        shp_files = list(extract_to.rglob("*.shp"))
        print(f"✓ ({len(shp_files)} shapefiles)")

        return shp_files
    except zipfile.BadZipFile as e:
        print(f"✗ Archivo ZIP corrupto o inválido")
        print(f"    Eliminando {zip_path.name} para permitir re-descarga...")
        try:
            zip_path.unlink()
            print(f"    ✓ Archivo eliminado. Re-ejecute para descargar de nuevo.")
        except Exception as del_err:
            print(f"    ✗ Error al eliminar: {del_err}")
        return []
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def load_shapefile_to_postgis(shp_file: Path, schema: str, table_name: str, transform_to_srid: int = None) -> bool:
    """Carga un shapefile a PostGIS usando ogr2ogr

    Retorna:
        True si se cargó exitosamente
        False si falló
        None si se saltó (ya existía)
    """
    try:
        # Verificar si la tabla ya existe (a menos que FORCE_RELOAD esté activo)
        if not FORCE_RELOAD and table_exists(schema, table_name):
            print(f"    [✓] {schema}.{table_name} (ya cargado)")
            return None  # Indica que se saltó

        print(f"    Cargando {shp_file.name} → {schema}.{table_name}... ", end="", flush=True)

        # Build connection string - omit host if empty (Unix socket)
        if DB_CONFIG['host']:
            pg_conn = f"PG:host={DB_CONFIG['host']} port={DB_CONFIG['port']} "
        else:
            pg_conn = f"PG:port={DB_CONFIG['port']} "

        pg_conn += (f"dbname={DB_CONFIG['database']} user={DB_CONFIG['user']} "
                    f"password={DB_CONFIG['password']}")

        # Usar ogr2ogr para cargar el shapefile
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
            "-skipfailures"  # Continuar si hay errores en algunos features
        ]

        # Transformar SRID si se especifica (para unificar INEGI con SEPOMEX)
        if transform_to_srid:
            cmd.extend(["-t_srs", f"EPSG:{transform_to_srid}"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("✓")
            return True
        else:
            # Mostrar solo la primera línea del error para no saturar
            error_msg = result.stderr.split('\n')[0] if result.stderr else "Unknown error"
            print(f"✗ {error_msg[:80]}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ Timeout")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def register_load(table_name: str, source: str, file_name: str, rows_count: int = None, status: str = 'success'):
    """Registra la carga en la tabla de metadatos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO public.load_metadata (table_name, source, file_name, rows_count, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (table_name, source, file_name, rows_count, status))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"  Advertencia: No se pudo registrar la carga: {e}")


def load_sepomex_shapefiles():
    """Carga todos los shapefiles de SEPOMEX"""
    print("\n=== Cargando Shapefiles de SEPOMEX (Códigos Postales) ===\n")

    # Mostrar filtro de estados si está activo
    if ESTADOS_FILTER:
        estados_nombres = [ESTADOS_SEPOMEX[cve][1] for cve in sorted(ESTADOS_FILTER) if cve in ESTADOS_SEPOMEX]
        print(f"Estados a cargar: {', '.join(estados_nombres)} ({len(ESTADOS_FILTER)} de 32)")
    else:
        print("Estados a cargar: Todos (32)")
    print()

    cp_dir = Path("/data/cp_shapefiles")
    temp_dir = Path("/tmp/cp_extracts")
    temp_dir.mkdir(exist_ok=True)

    if not cp_dir.exists():
        print("⚠ Directorio /data/cp_shapefiles no encontrado")
        return

    exitosos = 0
    fallidos = 0
    omitidos = 0

    for cve_ent, (abrev, nombre) in ESTADOS_SEPOMEX.items():
        # Filtrar por estados si está configurado
        if ESTADOS_FILTER and cve_ent not in ESTADOS_FILTER:
            omitidos += 1
            continue

        zip_file = cp_dir / f"CP_{abrev}.zip"

        if not zip_file.exists():
            print(f"⚠ Archivo no encontrado: {zip_file.name}")
            fallidos += 1
            continue

        print(f"[{cve_ent}] {nombre}")

        # Extraer ZIP
        extract_dir = temp_dir / f"cp_{cve_ent}"
        extract_dir.mkdir(exist_ok=True)

        shp_files = extract_zip(zip_file, extract_dir)

        # Cargar cada shapefile
        for shp_file in shp_files:
            table_name = f"cp_{cve_ent}_{shp_file.stem.lower()}"

            # Cargar con proyección nativa (ambos usan Lambert Conformal Conic)
            if load_shapefile_to_postgis(shp_file, "sepomex", table_name):
                register_load(table_name, "SEPOMEX", zip_file.name)
                exitosos += 1
            else:
                register_load(table_name, "SEPOMEX", zip_file.name, status='failed')
                fallidos += 1

        # Limpiar archivos temporales
        subprocess.run(["rm", "-rf", str(extract_dir)], check=False)

    resultado = f"\nSEPOMEX - Exitosos: {exitosos}, Fallidos: {fallidos}"
    if omitidos > 0:
        resultado += f", Omitidos: {omitidos}"
    print(resultado)


def load_inegi_shapefiles():
    """Carga todos los shapefiles de INEGI"""
    print("\n=== Cargando Shapefiles de INEGI (Marco Geoestadístico 2020) ===\n")

    # Mostrar filtro de estados si está activo
    if ESTADOS_FILTER:
        estados_nombres = [ESTADOS_SEPOMEX[cve][1] for cve in sorted(ESTADOS_FILTER) if cve in ESTADOS_SEPOMEX]
        print(f"Estados a cargar: {', '.join(estados_nombres)} ({len(ESTADOS_FILTER)} de 32)")
    else:
        print("Estados a cargar: Todos (32)")

    # Mostrar configuración de capas
    print("\nCapas a cargar:")
    print(f"  ✓ AGEBs (urbanas y rurales): {'SÍ' if LOAD_LAYERS['agebs'] else 'NO'}")
    print(f"  {'✓' if LOAD_LAYERS['manzanas'] else '○'} Manzanas: {'SÍ' if LOAD_LAYERS['manzanas'] else 'NO'}")
    print(f"  {'✓' if LOAD_LAYERS['localidades'] else '○'} Localidades: {'SÍ' if LOAD_LAYERS['localidades'] else 'NO'}")
    print(f"  {'✓' if LOAD_LAYERS['municipios'] else '○'} Municipios: {'SÍ' if LOAD_LAYERS['municipios'] else 'NO'}")
    print(f"  {'✓' if LOAD_LAYERS['entidades'] else '○'} Entidades: {'SÍ' if LOAD_LAYERS['entidades'] else 'NO'}")
    print()

    ageb_dir = Path("/data/ageb_shapefiles")
    temp_dir = Path("/tmp/ageb_extracts")
    temp_dir.mkdir(exist_ok=True)

    if not ageb_dir.exists():
        print("⚠ Directorio /data/ageb_shapefiles no encontrado")
        return

    exitosos = 0
    fallidos = 0
    omitidos = 0

    for cve_ent, nombre_archivo in ESTADOS_INEGI.items():
        # Filtrar por estados si está configurado
        if ESTADOS_FILTER and cve_ent not in ESTADOS_FILTER:
            omitidos += 1
            continue

        zip_file = ageb_dir / f"{cve_ent}_{nombre_archivo}.zip"

        if not zip_file.exists():
            print(f"⚠ Archivo no encontrado: {zip_file.name}")
            fallidos += 1
            continue

        print(f"[{cve_ent}] {nombre_archivo.title()}")

        # Extraer ZIP
        extract_dir = temp_dir / f"ageb_{cve_ent}"
        extract_dir.mkdir(exist_ok=True)

        shp_files = extract_zip(zip_file, extract_dir)

        # Cargar cada shapefile
        for shp_file in shp_files:
            # Determinar tipo de geometría por nombre de archivo
            stem_lower = shp_file.stem.lower()

            # Patrón INEGI: {cve_ent}a, {cve_ent}ar, {cve_ent}m, etc.
            # Verificar primero patrones específicos de INEGI
            if stem_lower == f"{cve_ent}a":
                geom_type = 'ageb_urbana'
            elif stem_lower == f"{cve_ent}ar":
                geom_type = 'ageb_rural'
            elif stem_lower == f"{cve_ent}m":
                geom_type = 'manzana'
            elif stem_lower == f"{cve_ent}l" or stem_lower == f"{cve_ent}lpr":
                geom_type = 'localidad'
            elif stem_lower == f"{cve_ent}mun":
                geom_type = 'municipio'
            elif stem_lower in [f"{cve_ent}ent", f"{cve_ent}e"]:
                geom_type = 'entidad'
            # Patrones genéricos para otros formatos
            elif 'ageb_urb' in stem_lower or 'ageb urbana' in stem_lower:
                geom_type = 'ageb_urbana'
            elif 'ageb_rur' in stem_lower or 'ageb rural' in stem_lower:
                geom_type = 'ageb_rural'
            elif 'manzana' in stem_lower:
                geom_type = 'manzana'
            elif 'localidad' in stem_lower:
                geom_type = 'localidad'
            elif 'municipio' in stem_lower:
                geom_type = 'municipio'
            elif 'entidad' in stem_lower:
                geom_type = 'entidad'
            else:
                # Omitir archivos que no coincidan con tipos conocidos
                print(f"    Omitiendo {shp_file.name} (tipo desconocido)")
                continue

            # Verificar si se debe cargar esta capa
            skip = False
            if geom_type in ['ageb_urbana', 'ageb_rural'] and not LOAD_LAYERS['agebs']:
                print(f"    Omitiendo {shp_file.name} (AGEBs deshabilitados)")
                skip = True
            elif geom_type == 'manzana' and not LOAD_LAYERS['manzanas']:
                print(f"    Omitiendo {shp_file.name} (Manzanas deshabilitadas)")
                skip = True
            elif geom_type == 'localidad' and not LOAD_LAYERS['localidades']:
                print(f"    Omitiendo {shp_file.name} (Localidades deshabilitadas)")
                skip = True
            elif geom_type == 'municipio' and not LOAD_LAYERS['municipios']:
                print(f"    Omitiendo {shp_file.name} (Municipios deshabilitados)")
                skip = True
            elif geom_type == 'entidad' and not LOAD_LAYERS['entidades']:
                print(f"    Omitiendo {shp_file.name} (Entidades deshabilitadas)")
                skip = True

            if skip:
                continue

            table_name = f"{geom_type}_{cve_ent}"

            # INEGI usa SRID 900916 nativo (no requiere transformación)
            if load_shapefile_to_postgis(shp_file, "inegi", table_name):
                register_load(table_name, "INEGI", zip_file.name)
                exitosos += 1
            else:
                register_load(table_name, "INEGI", zip_file.name, status='failed')
                fallidos += 1

        # Limpiar archivos temporales
        subprocess.run(["rm", "-rf", str(extract_dir)], check=False)

    resultado = f"\nINEGI - Exitosos: {exitosos}, Fallidos: {fallidos}"
    if omitidos > 0:
        resultado += f", Omitidos: {omitidos}"
    print(resultado)


def main():
    print("=" * 70)
    print("  Cargador de Shapefiles a PostGIS - cp2ageb")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base de datos: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")

    # Mostrar modo de validación
    validation_modes = {
        'quick': 'Rápida (solo apertura)',
        'full': 'Completa (testzip)',
        'none': 'Sin validación'
    }
    validation_desc = validation_modes.get(VALIDATE_ZIPS, 'Desconocido')
    print(f"Validación de ZIPs: {validation_desc}")
    print("=" * 70)

    # Verificar conexión a base de datos
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print("✓ Conexión a base de datos exitosa\n")
    except Exception as e:
        print(f"✗ Error conectando a base de datos: {e}")
        sys.exit(1)

    # Cargar shapefiles
    load_sepomex_shapefiles()
    load_inegi_shapefiles()

    print("\n" + "=" * 70)
    print("  Carga completada")
    print("=" * 70)


if __name__ == "__main__":
    main()
