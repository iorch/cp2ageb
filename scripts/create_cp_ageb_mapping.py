#!/usr/bin/env python3
"""
Script para crear el mapeo completo de Códigos Postales a AGEBs
Procesa todos los estados y crea una tabla consolidada
"""

import os
import sys
import psycopg2
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    'host': os.getenv('PGHOST', '/var/run/postgresql'),  # Unix socket directory
    'port': os.getenv('PGPORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'cp2ageb'),
    'user': os.getenv('POSTGRES_USER', 'geouser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'geopassword')
}

# Mapeo de estados
ESTADOS = {
    "01": "Aguascalientes",
    "02": "Baja California",
    "03": "Baja California Sur",
    "04": "Campeche",
    "05": "Coahuila",
    "06": "Colima",
    "07": "Chiapas",
    "08": "Chihuahua",
    "09": "Ciudad de México",
    "10": "Durango",
    "11": "Guanajuato",
    "12": "Guerrero",
    "13": "Hidalgo",
    "14": "Jalisco",
    "15": "Estado de México",
    "16": "Michoacán",
    "17": "Morelos",
    "18": "Nayarit",
    "19": "Nuevo León",
    "20": "Oaxaca",
    "21": "Puebla",
    "22": "Querétaro",
    "23": "Quintana Roo",
    "24": "San Luis Potosí",
    "25": "Sinaloa",
    "26": "Sonora",
    "27": "Tabasco",
    "28": "Tamaulipas",
    "29": "Tlaxcala",
    "30": "Veracruz",
    "31": "Yucatán",
    "32": "Zacatecas",
}


def get_connection():
    """Obtener conexión a la base de datos"""
    return psycopg2.connect(**DB_CONFIG)


def create_mapping_table(conn):
    """Crear tabla de mapeo si no existe"""
    print("Creando tabla de mapeo...")

    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.cp_to_ageb_mapping (
                id SERIAL PRIMARY KEY,
                estado_cve VARCHAR(2) NOT NULL,
                codigo_postal VARCHAR(10) NOT NULL,
                clave_ageb VARCHAR(20) NOT NULL,
                tipo_ageb VARCHAR(10) NOT NULL,
                area_interseccion_m2 NUMERIC(15,2),
                porcentaje_interseccion NUMERIC(5,2),
                tipo_relacion VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Índices para mejorar el rendimiento
            CREATE INDEX IF NOT EXISTS idx_cp_to_ageb_cp ON public.cp_to_ageb_mapping(codigo_postal);
            CREATE INDEX IF NOT EXISTS idx_cp_to_ageb_ageb ON public.cp_to_ageb_mapping(clave_ageb);
            CREATE INDEX IF NOT EXISTS idx_cp_to_ageb_estado ON public.cp_to_ageb_mapping(estado_cve);
            CREATE INDEX IF NOT EXISTS idx_cp_to_ageb_tipo ON public.cp_to_ageb_mapping(tipo_relacion);

            -- Comentarios
            COMMENT ON TABLE public.cp_to_ageb_mapping IS
                'Mapeo de Códigos Postales (SEPOMEX) a AGEBs (INEGI)';
            COMMENT ON COLUMN public.cp_to_ageb_mapping.porcentaje_interseccion IS
                'Porcentaje del área del CP que intersecta con el AGEB';
            COMMENT ON COLUMN public.cp_to_ageb_mapping.tipo_relacion IS
                'principal: >50% intersección, parcial: <50% intersección';
        """)

        conn.commit()
        print("✓ Tabla creada")


def get_available_tables(conn, schema, pattern):
    """Obtener tablas disponibles en un schema"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name LIKE %s
            ORDER BY table_name
        """, (schema, pattern))
        return [row[0] for row in cur.fetchall()]


def process_state(conn, cve_ent):
    """Procesar un estado completo (CPs + AGEBs urbanas y rurales)"""
    print(f"\n[{cve_ent}] Procesando estado {cve_ent}...")

    # Buscar tabla de códigos postales
    cp_tables = get_available_tables(conn, 'sepomex', f'cp_{cve_ent}_%')
    if not cp_tables:
        print(f"  ⚠ No se encontró tabla de CPs para estado {cve_ent}")
        return 0

    cp_table = cp_tables[0]  # Usar la primera tabla encontrada
    print(f"  Tabla CPs: {cp_table}")

    # Buscar tablas de AGEBs
    ageb_urbana_table = f"inegi.ageb_urbana_{cve_ent}"
    ageb_rural_table = f"inegi.ageb_rural_{cve_ent}"

    total_inserted = 0

    # Procesar AGEBs urbanas
    with conn.cursor() as cur:
        # Verificar si existe tabla de AGEBs urbanas
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'inegi'
                  AND table_name = %s
            )
        """, (f'ageb_urbana_{cve_ent}',))

        if cur.fetchone()[0]:
            print(f"  Procesando AGEBs urbanas...")
            cur.execute(f"""
                INSERT INTO public.cp_to_ageb_mapping (
                    estado_cve, codigo_postal,
                    clave_ageb, tipo_ageb, area_interseccion_m2,
                    porcentaje_interseccion, tipo_relacion
                )
                SELECT
                    %s,
                    cp.d_cp,
                    ageb.cvegeo,
                    'urbana',
                    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))),
                    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) / NULLIF(ST_Area(ST_Transform(cp.geom, 6372)), 0) * 100,
                    CASE
                        WHEN ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) / NULLIF(ST_Area(ST_Transform(cp.geom, 6372)), 0) > 0.5
                        THEN 'principal'
                        ELSE 'parcial'
                    END
                FROM
                    sepomex.{cp_table} cp
                CROSS JOIN
                    {ageb_urbana_table} ageb
                WHERE
                    ST_Intersects(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))
                    AND ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) / NULLIF(ST_Area(ST_Transform(cp.geom, 6372)), 0) > 0.01
            """, (cve_ent,))

            count = cur.rowcount
            total_inserted += count
            print(f"    ✓ {count} registros urbanos insertados")
        else:
            print(f"  ⚠ No se encontró tabla de AGEBs urbanas")

        # Procesar AGEBs rurales
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'inegi'
                  AND table_name = %s
            )
        """, (f'ageb_rural_{cve_ent}',))

        if cur.fetchone()[0]:
            print(f"  Procesando AGEBs rurales...")
            cur.execute(f"""
                INSERT INTO public.cp_to_ageb_mapping (
                    estado_cve, codigo_postal,
                    clave_ageb, tipo_ageb, area_interseccion_m2,
                    porcentaje_interseccion, tipo_relacion
                )
                SELECT
                    %s,
                    cp.d_cp,
                    ageb.cvegeo,
                    'rural',
                    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)),
                    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) / NULLIF(ST_Area(ST_Transform(cp.geom, 6372)), 0) * 100,
                    CASE
                        WHEN ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) / NULLIF(ST_Area(ST_Transform(cp.geom, 6372)), 0) > 0.5
                        THEN 'principal'
                        ELSE 'parcial'
                    END
                FROM
                    sepomex.{cp_table} cp
                CROSS JOIN
                    {ageb_rural_table} ageb
                WHERE
                    ST_Intersects(ST_Transform(cp.geom, 6372), ageb.geom)
                    AND ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) / NULLIF(ST_Area(ST_Transform(cp.geom, 6372)), 0) > 0.01
            """, (cve_ent,))

            count = cur.rowcount
            total_inserted += count
            print(f"    ✓ {count} registros rurales insertados")
        else:
            print(f"  ⚠ No se encontró tabla de AGEBs rurales")

    conn.commit()
    print(f"  Total: {total_inserted} registros")
    return total_inserted


def show_summary(conn):
    """Mostrar resumen del mapeo"""
    print("\n" + "=" * 70)
    print("  RESUMEN DEL MAPEO CP → AGEB")
    print("=" * 70)

    with conn.cursor() as cur:
        # Total de registros
        cur.execute("SELECT COUNT(*) FROM public.cp_to_ageb_mapping")
        total = cur.fetchone()[0]
        print(f"\nTotal de relaciones: {total:,}")

        # Por estado
        cur.execute("""
            SELECT
                estado_cve,
                COUNT(DISTINCT codigo_postal) as cps,
                COUNT(DISTINCT clave_ageb) as agebs,
                COUNT(*) as relaciones
            FROM public.cp_to_ageb_mapping
            GROUP BY estado_cve
            ORDER BY estado_cve
        """)

        print("\nPor estado:")
        print(f"{'CVE':<5} {'CPs':>8} {'AGEBs':>8} {'Relaciones':>12}")
        print("-" * 40)

        for row in cur.fetchall():
            print(f"{row[0]:<5} {row[1]:>8,} {row[2]:>8,} {row[3]:>12,}")

        # Tipo de relación
        cur.execute("""
            SELECT tipo_relacion, COUNT(*) as cantidad
            FROM public.cp_to_ageb_mapping
            GROUP BY tipo_relacion
            ORDER BY tipo_relacion
        """)

        print("\nPor tipo de relación:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

        # Tipo de AGEB
        cur.execute("""
            SELECT tipo_ageb, COUNT(*) as cantidad
            FROM public.cp_to_ageb_mapping
            GROUP BY tipo_ageb
            ORDER BY tipo_ageb
        """)

        print("\nPor tipo de AGEB:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]:,}")

    print("=" * 70)


def main():
    print("=" * 70)
    print("  Script de Mapeo CP → AGEB")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base de datos: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("=" * 70)

    # Conectar a la base de datos
    try:
        conn = get_connection()
        print("✓ Conexión exitosa\n")
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        sys.exit(1)

    # Crear tabla de mapeo
    create_mapping_table(conn)

    # Preguntar si limpiar tabla existente
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM public.cp_to_ageb_mapping")
        existing_count = cur.fetchone()[0]

        if existing_count > 0:
            print(f"\n⚠ La tabla ya contiene {existing_count:,} registros")
            response = input("¿Deseas limpiar la tabla antes de procesar? (s/N): ").strip().lower()
            if response == 's':
                cur.execute("TRUNCATE TABLE public.cp_to_ageb_mapping RESTART IDENTITY")
                conn.commit()
                print("✓ Tabla limpiada")

    # Procesar cada estado
    print("\nProcesando estados...")
    total_registros = 0

    for cve_ent in ESTADOS.keys():
        try:
            count = process_state(conn, cve_ent)
            total_registros += count
        except Exception as e:
            print(f"  ✗ Error procesando estado {cve_ent}: {e}")
            conn.rollback()  # Rollback para que la transacción no quede abortada
            continue

    # Mostrar resumen
    show_summary(conn)

    conn.close()
    print("\n✓ Proceso completado exitosamente")


if __name__ == "__main__":
    main()
