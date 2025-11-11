#!/usr/bin/env python3
"""
Script para descargar shapefiles de AGEBs (Áreas Geoestadísticas Básicas) del INEGI
Descarga el Marco Geoestadístico 2020 con AGEBs urbanas y rurales por entidad federativa
"""

import os
import sys
import requests
from pathlib import Path
from typing import List, Tuple

def show_help():
    """Muestra ayuda del script"""
    print("""
Uso: python3 download_ageb_shapefiles.py [opciones]

Descarga shapefiles del Marco Geoestadístico 2020 de INEGI para todos los estados.

OPCIONES:
    --help, -h      Muestra esta ayuda y sale

DESCRIPCIÓN:
    Este script descarga los 32 archivos ZIP de shapefiles del Marco Geoestadístico
    desde el repositorio oficial de INEGI.

    Cada archivo contiene capas geográficas:
    - AGEBs urbanas (Áreas Geoestadísticas Básicas urbanas)
    - AGEBs rurales (Áreas Geoestadísticas Básicas rurales)
    - Manzanas (bloques urbanos)
    - Localidades (pueblos y ciudades)
    - Municipios
    - Entidad (estado completo)

DIRECTORIO DE SALIDA:
    data/ageb_shapefiles/

ESTADOS DESCARGADOS:
    Todos los 32 estados de México

EJEMPLOS:
    python3 download_ageb_shapefiles.py          # Descargar todos los estados
    python3 download_ageb_shapefiles.py --help   # Mostrar esta ayuda

FUENTE DE DATOS:
    https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173
    Marco Geoestadístico 2020 - INEGI

NOTAS:
    - Los archivos ya descargados NO se vuelven a descargar
    - Tamaño total aproximado: ~2 GB
    - Tiempo estimado: 20-30 minutos (depende de la conexión)
    - Por defecto el sistema solo carga AGEBs (optimización de tiempo)
""")
    sys.exit(0)

# Mapeo de códigos INEGI (CVE_ENT) a nombres de archivos
# Formato: (código, nombre_archivo, nombre_completo)
ESTADOS: List[Tuple[str, str, str]] = [
    ("01", "aguascalientes", "Aguascalientes"),
    ("02", "bajacalifornia", "Baja California"),
    ("03", "bajacaliforniasur", "Baja California Sur"),
    ("04", "campeche", "Campeche"),
    ("05", "coahuiladezaragoza", "Coahuila de Zaragoza"),
    ("06", "colima", "Colima"),
    ("07", "chiapas", "Chiapas"),
    ("08", "chihuahua", "Chihuahua"),
    ("09", "ciudaddemexico", "Ciudad de México"),
    ("10", "durango", "Durango"),
    ("11", "guanajuato", "Guanajuato"),
    ("12", "guerrero", "Guerrero"),
    ("13", "hidalgo", "Hidalgo"),
    ("14", "jalisco", "Jalisco"),
    ("15", "mexico", "Estado de México"),
    ("16", "michoacandeocampo", "Michoacán de Ocampo"),
    ("17", "morelos", "Morelos"),
    ("18", "nayarit", "Nayarit"),
    ("19", "nuevoleon", "Nuevo León"),
    ("20", "oaxaca", "Oaxaca"),
    ("21", "puebla", "Puebla"),
    ("22", "queretaro", "Querétaro"),
    ("23", "quintanaroo", "Quintana Roo"),
    ("24", "sanluispotosi", "San Luis Potosí"),
    ("25", "sinaloa", "Sinaloa"),
    ("26", "sonora", "Sonora"),
    ("27", "tabasco", "Tabasco"),
    ("28", "tamaulipas", "Tamaulipas"),
    ("29", "tlaxcala", "Tlaxcala"),
    ("30", "veracruzignaciodelallave", "Veracruz de Ignacio de la Llave"),
    ("31", "yucatan", "Yucatán"),
    ("32", "zacatecas", "Zacatecas"),
]

BASE_URL = "https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173"


def download_file(url: str, output_path: Path, estado_nombre: str) -> bool:
    """
    Descarga un archivo desde una URL y verifica su integridad

    Args:
        url: URL del archivo a descargar
        output_path: Ruta donde guardar el archivo
        estado_nombre: Nombre del estado para mostrar en consola

    Returns:
        True si la descarga fue exitosa y el archivo es válido, False en caso contrario
    """
    try:
        print(f"Descargando {estado_nombre:30s} ... ", end="", flush=True)

        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        # Crear directorio si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Descargar archivo
        total_size = int(response.headers.get('content-length', 0))
        with open(output_path, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    downloaded += len(chunk)
                    f.write(chunk)

        file_size = output_path.stat().st_size / (1024 * 1024)  # MB

        # Verificar que el archivo ZIP es válido
        import zipfile
        try:
            with zipfile.ZipFile(output_path, 'r') as zip_ref:
                bad_file = zip_ref.testzip()
                if bad_file:
                    print(f"✗ ZIP corrupto (archivo dañado: {bad_file})")
                    output_path.unlink()  # Eliminar archivo corrupto
                    return False
        except zipfile.BadZipFile:
            print(f"✗ ZIP inválido")
            output_path.unlink()  # Eliminar archivo corrupto
            return False

        print(f"✓ ({file_size:.1f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        # Eliminar archivo parcial si existe
        if output_path.exists():
            output_path.unlink()
        return False
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        # Eliminar archivo parcial si existe
        if output_path.exists():
            output_path.unlink()
        return False


def main():
    """
    Descarga todos los shapefiles de AGEBs del Marco Geoestadístico 2020
    """
    # Procesar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            show_help()
        else:
            print(f"Error: Opción desconocida '{sys.argv[1]}'")
            print("")
            print("Para ver opciones disponibles: python3 download_ageb_shapefiles.py --help")
            sys.exit(1)

    # Directorio de salida
    output_dir = Path("data/ageb_shapefiles")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Descargador de Shapefiles AGEBs - Marco Geoestadístico 2020 INEGI ===")
    print(f"Directorio de salida: {output_dir.absolute()}")
    print(f"Total de estados: {len(ESTADOS)}\n")

    # Estadísticas
    exitosos = 0
    fallidos = 0

    # Descargar cada archivo
    for codigo, nombre_archivo, nombre_completo in ESTADOS:
        filename = f"{codigo}_{nombre_archivo}.zip"
        url = f"{BASE_URL}/{filename}"
        output_path = output_dir / filename

        # Verificar si el archivo ya existe y es válido
        if output_path.exists():
            import zipfile
            try:
                with zipfile.ZipFile(output_path, 'r') as zip_ref:
                    bad_file = zip_ref.testzip()
                    if bad_file is None:
                        # Archivo existe y es válido - saltar
                        print(f"[✓] {nombre_completo:30s} (ya descargado)")
                        exitosos += 1
                        continue
                    else:
                        # Archivo existe pero está corrupto - eliminar y re-descargar
                        print(f"[!] {nombre_completo:30s} (corrupto, re-descargando)")
                        output_path.unlink()
            except zipfile.BadZipFile:
                # Archivo existe pero no es ZIP válido - eliminar y re-descargar
                print(f"[!] {nombre_completo:30s} (inválido, re-descargando)")
                output_path.unlink()

        # Descargar archivo (solo si no existe o estaba corrupto)
        if download_file(url, output_path, nombre_completo):
            exitosos += 1
        else:
            fallidos += 1

    # Resumen
    print(f"\n=== Resumen ===")
    print(f"Exitosos: {exitosos}/{len(ESTADOS)}")
    print(f"Fallidos: {fallidos}/{len(ESTADOS)}")

    if fallidos > 0:
        print("\nAlgunos archivos no se pudieron descargar.")
        sys.exit(1)
    else:
        print(f"\n¡Todos los archivos descargados exitosamente en {output_dir.absolute()}!")
        print("\nCada archivo contiene:")
        print("  - AGEBs urbanas (.shp)")
        print("  - AGEBs rurales (.shp)")
        print("  - Manzanas urbanas (.shp)")
        print("  - Localidades (.shp)")
        print("  - Municipios (.shp)")
        print("  - Entidad (.shp)")
        sys.exit(0)


if __name__ == "__main__":
    main()
