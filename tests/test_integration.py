#!/usr/bin/env python3
"""
Tests de integración end-to-end
Verifica el flujo completo de búsqueda de AGEBs por código postal
"""

import pytest
import psycopg2
import os
from pathlib import Path


class TestEndToEndCPtoAGEB:
    """Tests end-to-end del flujo CP → AGEB"""

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

    def test_known_cp_returns_agebs(self, db_conn):
        """Test con códigos postales conocidos de los 4 estados principales"""
        test_cases = [
            ('44100', 'Jalisco'),      # Guadalajara
            ('11560', 'CDMX'),         # Polanco
            ('50000', 'Edo México'),   # Toluca
            ('64000', 'Nuevo León'),   # Monterrey
        ]

        with db_conn.cursor() as cur:
            for cp, nombre_estado in test_cases:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    if len(results) > 0:
                        # Verificar estructura básica
                        assert all(len(row) == 4 for row in results), \
                            f"Estructura incorrecta para CP {cp}"

                        # Verificar que todos retornan el mismo CP
                        assert all(row[0] == cp for row in results), \
                            f"CP inconsistente en resultados para {cp}"

                        # Verificar tipos de AGEB válidos
                        tipos_ageb = {row[2] for row in results}
                        assert tipos_ageb.issubset({'urbana', 'rural'}), \
                            f"Tipos de AGEB inválidos para CP {cp}: {tipos_ageb}"

                        # Verificar que porcentajes suman aproximadamente 100%
                        total_porcentaje = sum(row[3] for row in results)
                        assert 95 <= total_porcentaje <= 105, \
                            f"Porcentajes no suman ~100% para CP {cp}: {total_porcentaje}%"

                        # Verificar que porcentajes están ordenados descendentemente
                        porcentajes = [row[3] for row in results]
                        assert porcentajes == sorted(porcentajes, reverse=True), \
                            f"Resultados no están ordenados por porcentaje para CP {cp}"

                        print(f"✓ CP {cp} ({nombre_estado}): {len(results)} AGEBs encontrados")

                except psycopg2.Error as e:
                    if "no encontrado" in str(e):
                        pytest.skip(f"Estado de CP {cp} ({nombre_estado}) no está cargado")
                    else:
                        raise

    def test_spatial_intersection_quality(self, db_conn):
        """Verificar la calidad de las intersecciones espaciales"""
        with db_conn.cursor() as cur:
            # Obtener un CP de prueba
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
                pytest.skip("No hay datos para probar")

            cp = result[0]
            cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
            results = cur.fetchall()

            if len(results) > 0:
                # Verificar que el AGEB principal tiene porcentaje razonable
                principal_porcentaje = results[0][3]
                assert principal_porcentaje >= 10, \
                    f"AGEB principal tiene porcentaje muy bajo: {principal_porcentaje}%"

                # Verificar que no hay intersecciones triviales
                assert all(row[3] >= 0.01 for row in results), \
                    "Hay intersecciones menores al umbral mínimo"

    def test_ageb_codes_format(self, db_conn):
        """Verificar que las claves AGEB tienen el formato correcto"""
        with db_conn.cursor() as cur:
            # Obtener un CP de prueba
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
                pytest.skip("No hay datos para probar")

            cp = result[0]
            cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
            results = cur.fetchall()

            for row in results:
                clave_ageb = row[1]
                # Formato AGEB: varía entre 9-13 caracteres dependiendo del tipo
                # Urbanas: típicamente 13 caracteres (ej: 140100010014A)
                # Rurales: pueden ser más cortas (ej: 140981010)
                # Primeros 2: estado, siguientes: municipio, localidad, ageb
                assert len(clave_ageb) >= 9, \
                    f"Clave AGEB muy corta: {clave_ageb}"
                assert clave_ageb[:2].isdigit(), \
                    f"Primeros 2 dígitos de AGEB deben ser numéricos: {clave_ageb}"


class TestDataConsistency:
    """Tests de consistencia de datos entre SEPOMEX e INEGI"""

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

    def test_states_match_between_sources(self, db_conn):
        """Verificar que hay datos SEPOMEX e INEGI para los mismos estados"""
        with db_conn.cursor() as cur:
            # Obtener códigos de estado de SEPOMEX
            cur.execute("""
                SELECT DISTINCT substring(table_name from 'cp_(\\d{2})_') as estado_cve
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                AND table_name LIKE 'cp_%'
                ORDER BY estado_cve;
            """)
            sepomex_estados = {row[0] for row in cur.fetchall() if row[0]}

            # Obtener códigos de estado de INEGI
            cur.execute("""
                SELECT DISTINCT substring(table_name from 'ageb_urbana_(\\d{2})') as estado_cve
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                AND table_name LIKE 'ageb_urbana_%'
                ORDER BY estado_cve;
            """)
            inegi_urbana = {row[0] for row in cur.fetchall() if row[0]}

            cur.execute("""
                SELECT DISTINCT substring(table_name from 'ageb_rural_(\\d{2})') as estado_cve
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                AND table_name LIKE 'ageb_rural_%'
                ORDER BY estado_cve;
            """)
            inegi_rural = {row[0] for row in cur.fetchall() if row[0]}

            inegi_estados = inegi_urbana | inegi_rural

            # Los estados cargados deben coincidir
            assert sepomex_estados == inegi_estados, \
                f"Estados no coinciden. SEPOMEX: {sepomex_estados}, INEGI: {inegi_estados}"

    def test_ageb_pairs_exist(self, db_conn):
        """Verificar que cada estado tiene AGEBs urbanas Y rurales"""
        with db_conn.cursor() as cur:
            # Obtener estados con AGEBs urbanas
            cur.execute("""
                SELECT DISTINCT substring(table_name from 'ageb_urbana_(\\d{2})') as estado_cve
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                AND table_name LIKE 'ageb_urbana_%';
            """)
            urbanas = {row[0] for row in cur.fetchall() if row[0]}

            # Obtener estados con AGEBs rurales
            cur.execute("""
                SELECT DISTINCT substring(table_name from 'ageb_rural_(\\d{2})') as estado_cve
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                AND table_name LIKE 'ageb_rural_%';
            """)
            rurales = {row[0] for row in cur.fetchall() if row[0]}

            # Deben coincidir (cada estado tiene ambas)
            assert urbanas == rurales, \
                f"Estados con AGEBs urbanas y rurales no coinciden"


class TestPerformance:
    """Tests de rendimiento de queries"""

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

    def test_function_query_speed(self, db_conn):
        """Verificar que la función responde en tiempo razonable"""
        import time

        with db_conn.cursor() as cur:
            # Obtener un CP de prueba
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
                pytest.skip("No hay datos para probar")

            cp = result[0]

            # Medir tiempo
            start = time.time()
            cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
            results = cur.fetchall()
            elapsed = time.time() - start

            # La query debe ser rápida (< 2 segundos en la primera ejecución)
            assert elapsed < 2.0, \
                f"Query muy lenta: {elapsed:.2f}s"

            print(f"Query ejecutada en {elapsed:.3f}s, {len(results)} resultados")

    def test_multiple_queries_speed(self, db_conn):
        """Verificar rendimiento con múltiples queries"""
        import time

        with db_conn.cursor() as cur:
            # Obtener varios CPs de prueba
            cur.execute("""
                SELECT d_cp
                FROM sepomex.cp_14_cp_jal
                WHERE EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name = 'cp_14_cp_jal'
                )
                LIMIT 5;
            """)
            cps = [row[0] for row in cur.fetchall()]

            if len(cps) == 0:
                pytest.skip("No hay datos para probar")

            # Medir tiempo para múltiples queries
            start = time.time()
            for cp in cps:
                cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                results = cur.fetchall()
            elapsed = time.time() - start

            avg_time = elapsed / len(cps)

            # Promedio debe ser razonable
            assert avg_time < 1.0, \
                f"Promedio de queries muy lento: {avg_time:.2f}s"

            print(f"{len(cps)} queries en {elapsed:.3f}s (promedio: {avg_time:.3f}s)")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
