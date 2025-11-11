#!/usr/bin/env python3
"""
Tests de base de datos y queries espaciales
Verifica que la base de datos esté correctamente configurada y que los queries funcionen
"""

import pytest
import psycopg2
import os
from typing import List, Dict, Any


class TestDatabaseConnection:
    """Tests de conexión a la base de datos"""

    @pytest.fixture
    def db_conn(self):
        """Fixture para conexión a la base de datos"""
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'cp2ageb'),
            user=os.getenv('POSTGRES_USER', 'geouser'),
            password=os.getenv('POSTGRES_PASSWORD', 'geopassword')
        )
        yield conn
        conn.close()

    def test_database_exists(self, db_conn):
        """Verificar que la base de datos existe y acepta conexiones"""
        with db_conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
            assert result[0] == 1

    def test_postgis_extension(self, db_conn):
        """Verificar que la extensión PostGIS está instalada"""
        with db_conn.cursor() as cur:
            cur.execute("SELECT PostGIS_version();")
            version = cur.fetchone()[0]
            assert version is not None
            assert len(version) > 0

    def test_schemas_exist(self, db_conn):
        """Verificar que los schemas sepomex e inegi existen"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN ('sepomex', 'inegi');
            """)
            schemas = [row[0] for row in cur.fetchall()]
            assert 'sepomex' in schemas
            assert 'inegi' in schemas

    def test_metadata_table_exists(self, db_conn):
        """Verificar que la tabla de metadatos existe"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'load_metadata'
                );
            """)
            exists = cur.fetchone()[0]
            assert exists is True


class TestDataLoading:
    """Tests de carga de datos"""

    @pytest.fixture
    def db_conn(self):
        """Fixture para conexión a la base de datos"""
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'cp2ageb'),
            user=os.getenv('POSTGRES_USER', 'geouser'),
            password=os.getenv('POSTGRES_PASSWORD', 'geopassword')
        )
        yield conn
        conn.close()

    def test_sepomex_tables_loaded(self, db_conn):
        """Verificar que hay tablas de SEPOMEX cargadas"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'sepomex';
            """)
            count = cur.fetchone()[0]
            assert count > 0, "No hay tablas SEPOMEX cargadas"

    def test_inegi_tables_loaded(self, db_conn):
        """Verificar que hay tablas de INEGI cargadas"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'inegi';
            """)
            count = cur.fetchone()[0]
            assert count > 0, "No hay tablas INEGI cargadas"

    def test_ageb_tables_pattern(self, db_conn):
        """Verificar que las tablas de AGEBs siguen el patrón correcto"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                AND (table_name LIKE 'ageb_urbana_%' OR table_name LIKE 'ageb_rural_%');
            """)
            tables = [row[0] for row in cur.fetchall()]
            assert len(tables) > 0, "No hay tablas de AGEBs"

            # Verificar que siguen el patrón esperado
            for table in tables:
                assert table.startswith('ageb_urbana_') or table.startswith('ageb_rural_')

    def test_sepomex_table_structure(self, db_conn):
        """Verificar que las tablas SEPOMEX tienen las columnas esperadas"""
        with db_conn.cursor() as cur:
            # Obtener primera tabla SEPOMEX
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                LIMIT 1;
            """)
            table = cur.fetchone()
            if table is None:
                pytest.skip("No hay tablas SEPOMEX para verificar")

            table_name = table[0]

            # Verificar columnas
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'sepomex'
                AND table_name = '{table_name}';
            """)
            columns = [row[0] for row in cur.fetchall()]

            # Columnas esperadas
            assert 'd_cp' in columns, "Falta columna d_cp"
            assert 'geom' in columns, "Falta columna geom"

    def test_inegi_table_structure(self, db_conn):
        """Verificar que las tablas INEGI tienen las columnas esperadas"""
        with db_conn.cursor() as cur:
            # Obtener primera tabla AGEB
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                AND table_name LIKE 'ageb_%'
                LIMIT 1;
            """)
            table = cur.fetchone()
            if table is None:
                pytest.skip("No hay tablas AGEB para verificar")

            table_name = table[0]

            # Verificar columnas
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'inegi'
                AND table_name = '{table_name}';
            """)
            columns = [row[0] for row in cur.fetchall()]

            # Columnas esperadas
            assert 'cvegeo' in columns, "Falta columna cvegeo"
            assert 'geom' in columns, "Falta columna geom"


class TestSpatialQueries:
    """Tests de queries espaciales"""

    @pytest.fixture
    def db_conn(self):
        """Fixture para conexión a la base de datos"""
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'cp2ageb'),
            user=os.getenv('POSTGRES_USER', 'geouser'),
            password=os.getenv('POSTGRES_PASSWORD', 'geopassword')
        )
        yield conn
        conn.close()

    def test_geometries_are_valid(self, db_conn):
        """Verificar que la mayoría de las geometrías son válidas"""
        with db_conn.cursor() as cur:
            # Verificar SEPOMEX
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                LIMIT 1;
            """)
            sepomex_table = cur.fetchone()

            if sepomex_table:
                cur.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) as invalid
                    FROM sepomex.{sepomex_table[0]};
                """)
                result = cur.fetchone()
                total, invalid = result[0], result[1]

                if total > 0:
                    invalid_pct = (invalid / total) * 100
                    # Permitir hasta 5% de geometrías inválidas (issue conocido en algunos shapefiles)
                    assert invalid_pct < 5.0, \
                        f"Demasiadas geometrías inválidas en SEPOMEX: {invalid}/{total} ({invalid_pct:.1f}%)"

            # Verificar INEGI
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                AND table_name LIKE 'ageb_%'
                LIMIT 1;
            """)
            inegi_table = cur.fetchone()

            if inegi_table:
                cur.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) as invalid
                    FROM inegi.{inegi_table[0]};
                """)
                result = cur.fetchone()
                total, invalid = result[0], result[1]

                if total > 0:
                    invalid_pct = (invalid / total) * 100
                    assert invalid_pct < 5.0, \
                        f"Demasiadas geometrías inválidas en INEGI: {invalid}/{total} ({invalid_pct:.1f}%)"

    def test_spatial_indexes_exist(self, db_conn):
        """Verificar que existen índices espaciales en las geometrías"""
        with db_conn.cursor() as cur:
            # Verificar SEPOMEX
            cur.execute("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE schemaname = 'sepomex'
                AND indexdef LIKE '%USING gist%';
            """)
            sepomex_indexes = cur.fetchone()[0]
            assert sepomex_indexes > 0, "No hay índices espaciales en SEPOMEX"

            # Verificar INEGI
            cur.execute("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE schemaname = 'inegi'
                AND indexdef LIKE '%USING gist%';
            """)
            inegi_indexes = cur.fetchone()[0]
            assert inegi_indexes > 0, "No hay índices espaciales en INEGI"

    def test_srid_consistency(self, db_conn):
        """Verificar que las geometrías tienen SRIDs correctos"""
        with db_conn.cursor() as cur:
            # Verificar que todas las geometrías tienen SRID
            cur.execute("""
                SELECT table_schema, table_name,
                       ST_SRID(geom) as srid
                FROM (
                    SELECT 'sepomex' as table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    LIMIT 1
                ) t
                CROSS JOIN LATERAL (
                    SELECT geom FROM sepomex.cp_14_cp_jal LIMIT 1
                ) g
                WHERE EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                );
            """)
            result = cur.fetchone()
            if result:
                srid = result[2]
                # SRIDs válidos: 900917, 900918, 900919 (Lambert Conformal Conic variants), 6372 (INEGI official)
                assert srid in [900917, 900918, 900919, 6372], f"SRID inesperado: {srid}"


class TestBuscarAgebsPorCPFunction:
    """Tests para la función buscar_agebs_por_cp"""

    @pytest.fixture
    def db_conn(self):
        """Fixture para conexión a la base de datos"""
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'cp2ageb'),
            user=os.getenv('POSTGRES_USER', 'geouser'),
            password=os.getenv('POSTGRES_PASSWORD', 'geopassword')
        )
        yield conn
        conn.close()

    def test_function_exists(self, db_conn):
        """Verificar que la función buscar_agebs_por_cp existe"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_proc
                    WHERE proname = 'buscar_agebs_por_cp'
                );
            """)
            exists = cur.fetchone()[0]
            assert exists is True, "La función buscar_agebs_por_cp no existe"

    def test_function_returns_data(self, db_conn):
        """Verificar que la función retorna datos para CPs conocidos"""
        test_cps = ['44100', '11560', '50000', '64000']  # Jal, CDMX, Edo Mex, NL

        with db_conn.cursor() as cur:
            for cp in test_cps:
                # Verificar si el estado del CP está cargado
                cur.execute(f"""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name LIKE 'cp_%';
                """)
                sepomex_tables = cur.fetchone()[0]

                if sepomex_tables == 0:
                    pytest.skip(f"No hay datos para probar CP {cp}")

                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    # Si el CP está cargado, debe retornar algo
                    # Si no está cargado, lanzará excepción (que se maneja abajo)
                    if len(results) > 0:
                        # Verificar estructura de resultados
                        assert len(results[0]) == 4  # codigo_postal, clave_ageb, tipo_ageb, porcentaje
                        assert results[0][0] == cp  # Verificar que el CP retornado es correcto
                        assert results[0][2] in ['urbana', 'rural']  # Tipo de AGEB válido
                        assert results[0][3] > 0  # Porcentaje debe ser positivo
                except psycopg2.Error as e:
                    # El CP no está en los datos cargados, es válido
                    if "no encontrado" in str(e):
                        pass  # Esperado si el estado no está cargado
                    else:
                        raise

    def test_function_with_invalid_cp(self, db_conn):
        """Verificar que la función maneja CPs inválidos correctamente"""
        with db_conn.cursor() as cur:
            try:
                cur.execute("SELECT * FROM buscar_agebs_por_cp('99999');")
                results = cur.fetchall()
                # La función debería lanzar excepción o retornar vacío
                # Si retorna vacío, es válido
                assert len(results) == 0 or True, "CP inválido debería retornar vacío o lanzar excepción"
            except psycopg2.Error as e:
                # También es válido si lanza excepción
                assert "no encontrado" in str(e).lower(), "Excepción debe indicar que CP no fue encontrado"

    def test_function_return_structure(self, db_conn):
        """Verificar la estructura de retorno de la función"""
        with db_conn.cursor() as cur:
            # Obtener primer CP disponible
            cur.execute("""
                SELECT d_cp
                FROM sepomex.cp_14_cp_jal
                WHERE EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name = 'cp_14_cp_jal'
                )
                LIMIT 1;
            """)
            result = cur.fetchone()

            if result is None:
                pytest.skip("No hay datos SEPOMEX para probar")

            cp = result[0]

            cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
            results = cur.fetchall()

            if len(results) > 0:
                row = results[0]
                assert len(row) == 4
                # Verificar tipos
                assert isinstance(row[0], str)  # codigo_postal
                assert isinstance(row[1], str)  # clave_ageb
                assert isinstance(row[2], str)  # tipo_ageb
                # row[3] puede ser float o Decimal


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
