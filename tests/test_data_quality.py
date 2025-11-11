#!/usr/bin/env python3
"""
Tests de calidad de datos
Verifica que los datos cargados tienen calidad consistente y cumplen invariantes
"""

import pytest
import psycopg2
import os
from decimal import Decimal


@pytest.fixture(scope="module")
def db_conn():
    """Fixture para conexión a la base de datos"""
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'cp2ageb'),
        user=os.getenv('POSTGRES_USER', 'geouser'),
        password=os.getenv('POSTGRES_PASSWORD', 'geopassword')
    )
    # Usar autocommit para evitar problemas de transacciones abortadas
    conn.autocommit = True
    yield conn
    conn.close()


class TestPercentageTotals:
    """Tests para verificar que los porcentajes siempre suman ~100%"""

    def test_percentages_sum_to_100_sample(self, db_conn):
        """Verificar que porcentajes suman ~100% en una muestra de CPs"""
        with db_conn.cursor() as cur:
            # Obtener una muestra de CPs de diferentes tablas
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                AND table_name LIKE 'cp_%'
                LIMIT 5;
            """)
            tables = [row[0] for row in cur.fetchall()]

            if not tables:
                pytest.skip("No hay tablas SEPOMEX para probar")

            cps_probados = 0
            cps_con_error = []

            for table in tables:
                # Obtener 3 CPs de esta tabla
                cur.execute(f"""
                    SELECT d_cp
                    FROM sepomex.{table}
                    LIMIT 3;
                """)
                cps = [row[0] for row in cur.fetchall()]

                for cp in cps:
                    try:
                        cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                        results = cur.fetchall()

                        if results:
                            total_porcentaje = sum(float(row[3]) for row in results)

                            # Permitir 95-105% (5% de tolerancia para redondeo y pequeñas diferencias)
                            if not (95 <= total_porcentaje <= 105):
                                cps_con_error.append({
                                    'cp': cp,
                                    'total': total_porcentaje,
                                    'n_agebs': len(results)
                                })

                            cps_probados += 1

                    except psycopg2.Error:
                        # CP no encontrado, continuar
                        pass

            print(f"\nCPs probados: {cps_probados}")
            print(f"CPs con error de porcentaje: {len(cps_con_error)}")

            if cps_con_error:
                print("\nCPs con porcentajes incorrectos:")
                for item in cps_con_error[:5]:  # Mostrar solo primeros 5
                    print(f"  CP {item['cp']}: {item['total']:.2f}% ({item['n_agebs']} AGEBs)")

            # Permitir hasta 10% de CPs con errores menores
            assert len(cps_con_error) <= cps_probados * 0.1, \
                f"Demasiados CPs con porcentajes incorrectos: {len(cps_con_error)}/{cps_probados}"

    def test_no_zero_percentages_above_threshold(self, db_conn):
        """Verificar que no hay porcentajes de 0% (deben estar filtrados)"""
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

            if not result:
                pytest.skip("No hay datos para probar")

            cp = result[0]
            cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
            results = cur.fetchall()

            # Verificar que todos los porcentajes son > 0
            for row in results:
                porcentaje = float(row[3])
                assert porcentaje > 0, f"Porcentaje de 0% encontrado para AGEB {row[1]}"

            # Verificar que todos son >= 0.01 (umbral de filtrado)
            for row in results:
                porcentaje = float(row[3])
                assert porcentaje >= 0.01, \
                    f"Porcentaje {porcentaje}% menor al umbral (0.01%) para AGEB {row[1]}"


class TestNoDuplicates:
    """Tests para verificar que no hay duplicados en resultados"""

    def test_no_duplicate_agebs_in_results(self, db_conn):
        """Verificar que no hay AGEBs duplicados en resultados"""
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
                LIMIT 10;
            """)
            cps = [row[0] for row in cur.fetchall()]

            if not cps:
                pytest.skip("No hay datos para probar")

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    if results:
                        # Extraer claves AGEB
                        agebs = [row[1] for row in results]

                        # Verificar que no hay duplicados
                        assert len(agebs) == len(set(agebs)), \
                            f"AGEBs duplicados encontrados para CP {cp}: {len(agebs)} total, {len(set(agebs))} únicos"

                except psycopg2.Error:
                    # CP no encontrado, continuar
                    pass

    def test_no_duplicate_tipo_ageb_combination(self, db_conn):
        """Verificar que no hay duplicados AGEB+tipo en resultados"""
        with db_conn.cursor() as cur:
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

            if not cps:
                pytest.skip("No hay datos para probar")

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    if results:
                        # Crear tuplas (clave_ageb, tipo_ageb)
                        ageb_tipo_pairs = [(row[1], row[2]) for row in results]

                        # Verificar que no hay duplicados
                        assert len(ageb_tipo_pairs) == len(set(ageb_tipo_pairs)), \
                            f"Combinaciones AGEB+tipo duplicadas para CP {cp}"

                except psycopg2.Error:
                    pass


class TestAGEBCodeFormat:
    """Tests para verificar formato de claves AGEB"""

    def test_ageb_codes_start_with_state_code(self, db_conn):
        """Verificar que las claves AGEB empiezan con código de estado correcto"""
        with db_conn.cursor() as cur:
            # Obtener datos de Jalisco (estado 14)
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

            if not result:
                pytest.skip("No hay datos de Jalisco para probar")

            cp = result[0]
            cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
            results = cur.fetchall()

            for row in results:
                clave_ageb = row[1]
                # Las claves AGEB de Jalisco deben empezar con "14"
                assert clave_ageb.startswith('14'), \
                    f"Clave AGEB {clave_ageb} no empieza con código de estado 14"

    def test_ageb_codes_minimum_length(self, db_conn):
        """Verificar que las claves AGEB tienen longitud mínima válida"""
        with db_conn.cursor() as cur:
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

            if not cps:
                pytest.skip("No hay datos para probar")

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    for row in results:
                        clave_ageb = row[1]
                        # Claves AGEB mínimo 9 caracteres
                        assert len(clave_ageb) >= 9, \
                            f"Clave AGEB muy corta: {clave_ageb} ({len(clave_ageb)} chars)"

                        # Máximo razonable: 15 caracteres
                        assert len(clave_ageb) <= 15, \
                            f"Clave AGEB muy larga: {clave_ageb} ({len(clave_ageb)} chars)"

                except psycopg2.Error:
                    pass

    def test_ageb_codes_numeric_prefix(self, db_conn):
        """Verificar que las claves AGEB empiezan con dígitos"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT d_cp
                FROM sepomex.cp_14_cp_jal
                WHERE EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name = 'cp_14_cp_jal'
                )
                LIMIT 3;
            """)
            cps = [row[0] for row in cur.fetchall()]

            if not cps:
                pytest.skip("No hay datos para probar")

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    for row in results:
                        clave_ageb = row[1]
                        # Primeros 2 caracteres deben ser dígitos (código de estado)
                        assert clave_ageb[:2].isdigit(), \
                            f"Clave AGEB {clave_ageb} no empieza con dígitos"

                        # Primeros 5 caracteres deben ser dígitos (estado + municipio)
                        assert clave_ageb[:5].isdigit(), \
                            f"Clave AGEB {clave_ageb}: primeros 5 chars no son dígitos"

                except psycopg2.Error:
                    pass


class TestGeometryQuality:
    """Tests de calidad de geometrías"""

    def test_no_null_geometries(self, db_conn):
        """Verificar que no hay geometrías nulas en tablas cargadas"""
        with db_conn.cursor() as cur:
            # Verificar SEPOMEX
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                LIMIT 3;
            """)
            tables = [row[0] for row in cur.fetchall()]

            for table in tables:
                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM sepomex.{table}
                    WHERE geom IS NULL;
                """)
                null_count = cur.fetchone()[0]
                assert null_count == 0, \
                    f"Tabla {table} tiene {null_count} geometrías nulas"

            # Verificar INEGI
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'inegi'
                LIMIT 3;
            """)
            tables = [row[0] for row in cur.fetchall()]

            for table in tables:
                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM inegi.{table}
                    WHERE geom IS NULL;
                """)
                null_count = cur.fetchone()[0]
                assert null_count == 0, \
                    f"Tabla {table} tiene {null_count} geometrías nulas"

    def test_no_empty_geometries(self, db_conn):
        """Verificar que no hay geometrías vacías"""
        with db_conn.cursor() as cur:
            # Verificar SEPOMEX
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                LIMIT 3;
            """)
            tables = [row[0] for row in cur.fetchall()]

            for table in tables:
                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM sepomex.{table}
                    WHERE ST_IsEmpty(geom);
                """)
                empty_count = cur.fetchone()[0]
                assert empty_count == 0, \
                    f"Tabla {table} tiene {empty_count} geometrías vacías"

    def test_geometries_have_reasonable_area(self, db_conn):
        """Verificar que las geometrías tienen áreas razonables"""
        with db_conn.cursor() as cur:
            # Verificar que CPs tienen áreas > 0
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                LIMIT 1;
            """)
            result = cur.fetchone()

            if not result:
                pytest.skip("No hay datos SEPOMEX para probar")

            table = result[0]

            # Verificar que todas las áreas son > 0
            cur.execute(f"""
                SELECT COUNT(*)
                FROM sepomex.{table}
                WHERE ST_Area(geom) <= 0;
            """)
            zero_area_count = cur.fetchone()[0]
            assert zero_area_count == 0, \
                f"Tabla {table} tiene {zero_area_count} geometrías con área <= 0"


class TestResultsOrdering:
    """Tests para verificar que los resultados están correctamente ordenados"""

    def test_results_ordered_by_percentage_desc(self, db_conn):
        """Verificar que resultados están ordenados por porcentaje descendente"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT d_cp
                FROM sepomex.cp_14_cp_jal
                WHERE EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name = 'cp_14_cp_jal'
                )
                LIMIT 10;
            """)
            cps = [row[0] for row in cur.fetchall()]

            if not cps:
                pytest.skip("No hay datos para probar")

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    if len(results) > 1:
                        # Extraer porcentajes
                        porcentajes = [float(row[3]) for row in results]

                        # Verificar orden descendente
                        assert porcentajes == sorted(porcentajes, reverse=True), \
                            f"Resultados para CP {cp} no están ordenados por porcentaje descendente"

                except psycopg2.Error:
                    pass


class TestDataConsistency:
    """Tests de consistencia de datos"""

    def test_cp_matches_in_all_results(self, db_conn):
        """Verificar que todos los resultados retornan el CP correcto"""
        with db_conn.cursor() as cur:
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

            if not cps:
                pytest.skip("No hay datos para probar")

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    # Verificar que todos retornan el mismo CP
                    for row in results:
                        assert row[0] == cp, \
                            f"CP en resultado ({row[0]}) no coincide con CP buscado ({cp})"

                except psycopg2.Error:
                    pass

    def test_tipo_ageb_valid_values(self, db_conn):
        """Verificar que tipo_ageb solo tiene valores válidos"""
        with db_conn.cursor() as cur:
            cur.execute("""
                SELECT d_cp
                FROM sepomex.cp_14_cp_jal
                WHERE EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name = 'cp_14_cp_jal'
                )
                LIMIT 10;
            """)
            cps = [row[0] for row in cur.fetchall()]

            if not cps:
                pytest.skip("No hay datos para probar")

            valid_tipos = {'urbana', 'rural'}

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    for row in results:
                        tipo_ageb = row[2]
                        assert tipo_ageb in valid_tipos, \
                            f"Tipo AGEB inválido: {tipo_ageb} (debe ser 'urbana' o 'rural')"

                except psycopg2.Error:
                    pass

    def test_both_urban_and_rural_agebs_present(self, db_conn):
        """Verificar que hay AGEBs urbanas Y rurales en la BD (cuando aplique)"""
        with db_conn.cursor() as cur:
            # Obtener CPs de prueba
            cur.execute("""
                SELECT d_cp
                FROM sepomex.cp_14_cp_jal
                WHERE EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name = 'cp_14_cp_jal'
                )
                LIMIT 50;
            """)
            cps = [row[0] for row in cur.fetchall()]

            if not cps:
                pytest.skip("No hay datos para probar")

            has_urbana = False
            has_rural = False

            for cp in cps:
                try:
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                    results = cur.fetchall()

                    tipos = {row[2] for row in results}
                    if 'urbana' in tipos:
                        has_urbana = True
                    if 'rural' in tipos:
                        has_rural = True

                    if has_urbana and has_rural:
                        break

                except psycopg2.Error:
                    pass

            # Al menos debe haber AGEBs urbanas en los 50 CPs probados
            assert has_urbana, "No se encontraron AGEBs urbanas en los CPs de prueba"

            # Advertir si no hay rurales (puede ser normal en ciudades)
            if not has_rural:
                print("\n⚠ Advertencia: No se encontraron AGEBs rurales en los 50 CPs probados")
                print("  Esto puede ser normal en zonas urbanas, pero verificar si hay datos rurales en la BD")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
