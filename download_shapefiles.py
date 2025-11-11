#!/usr/bin/env python3
"""
Script para descargar shapefiles de códigos postales por entidad federativa desde datos.gob.mx
Descarga archivos .shp de SEPOMEX con delimitación geográfica de códigos postales
"""

import os
import sys
import requests
from pathlib import Path
from typing import Dict

def show_help():
    """Muestra ayuda del script"""
    print("""
Uso: python3 download_shapefiles.py [opciones]

Descarga shapefiles de códigos postales de SEPOMEX para todos los estados de México.

OPCIONES:
    --help, -h      Muestra esta ayuda y sale

DESCRIPCIÓN:
    Este script descarga los 32 archivos ZIP de shapefiles de códigos postales
    desde el repositorio oficial de datos.gob.mx.

    Cada archivo contiene:
    - Polígonos geográficos de códigos postales
    - Atributos: código postal, asentamiento, tipo de zona
    - Formato: Shapefile (.shp, .dbf, .shx, .prj)

DIRECTORIO DE SALIDA:
    data/cp_shapefiles/

ESTADOS DESCARGADOS:
    Todos los 32 estados de México (Aguascalientes, Baja California, etc.)

EJEMPLOS:
    python3 download_shapefiles.py          # Descargar todos los estados
    python3 download_shapefiles.py --help   # Mostrar esta ayuda

FUENTE DE DATOS:
    https://www.datos.gob.mx/dataset/codigos_postales_entidad_federativa
    SEPOMEX (Servicio Postal Mexicano)

NOTAS:
    - Los archivos ya descargados NO se vuelven a descargar
    - Tamaño total aproximado: ~200 MB
    - Tiempo estimado: 5-10 minutos (depende de la conexión)
""")
    sys.exit(0)

# Mapeo de estados a sus abreviaturas oficiales usadas en los archivos
ESTADOS: Dict[str, str] = {
    "Aguascalientes": "Ags",
    "Baja California": "BC",
    "Baja California Sur": "BCS",
    "Campeche": "Camp",
    "Chiapas": "Chis",
    "Chihuahua": "Chih",
    "Ciudad de México": "CDMX",
    "Coahuila": "Coah",
    "Colima": "Col",
    "Durango": "Dgo",
    "Guanajuato": "Gto",
    "Guerrero": "Gro",
    "Hidalgo": "Hgo",
    "Jalisco": "Jal",
    "México": "Mex",
    "Michoacán": "Mich",
    "Morelos": "Mor",
    "Nayarit": "Nay",
    "Nuevo León": "NL",
    "Oaxaca": "Oax",
    "Puebla": "Pue",
    "Querétaro": "Qro",
    "Quintana Roo": "QRoo",
    "San Luis Potosí": "SLP",
    "Sinaloa": "Sin",
    "Sonora": "Son",
    "Tabasco": "Tab",
    "Tamaulipas": "Tamps",
    "Tlaxcala": "Tlax",
    "Veracruz": "Ver",
    "Yucatán": "Yuc",
    "Zacatecas": "Zac",
}

BASE_URL = "https://repodatos.atdt.gob.mx/api_update/sepomex/codigos_postales_entidad_federativa"


def download_file(url: str, output_path: Path) -> bool:
    """
    Descarga un archivo desde una URL y verifica su integridad

    Args:
        url: URL del archivo a descargar
        output_path: Ruta donde guardar el archivo

    Returns:
        True si la descarga fue exitosa y el archivo es válido, False en caso contrario
    """
    try:
        print(f"Descargando: {output_path.name}... ", end="", flush=True)

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        # Crear directorio si no existe
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Descargar archivo
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
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

        print(f"✓ ({file_size:.2f} MB)")
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
    Descarga todos los shapefiles de códigos postales por entidad federativa
    """
    # Procesar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            show_help()
        else:
            print(f"Error: Opción desconocida '{sys.argv[1]}'")
            print("")
            print("Para ver opciones disponibles: python3 download_shapefiles.py --help")
            sys.exit(1)

    # Directorio de salida
    output_dir = Path("data/cp_shapefiles")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Descargador de Shapefiles de Códigos Postales SEPOMEX ===")
    print(f"Directorio de salida: {output_dir.absolute()}")
    print(f"Total de estados: {len(ESTADOS)}\n")

    # Estadísticas
    exitosos = 0
    fallidos = 0

    # Descargar cada archivo
    for estado, abrev in ESTADOS.items():
        filename = f"CP_{abrev}.zip"
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
                        print(f"[✓] {estado:30s} (ya descargado)")
                        exitosos += 1
                        continue
                    else:
                        # Archivo existe pero está corrupto - eliminar y re-descargar
                        print(f"[!] {estado:30s} (corrupto, re-descargando)")
                        output_path.unlink()
            except zipfile.BadZipFile:
                # Archivo existe pero no es ZIP válido - eliminar y re-descargar
                print(f"[!] {estado:30s} (inválido, re-descargando)")
                output_path.unlink()

        # Descargar archivo (solo si no existe o estaba corrupto)
        if download_file(url, output_path):
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
        sys.exit(0)


if __name__ == "__main__":
    main()
