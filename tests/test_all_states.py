#!/usr/bin/env python3
"""
Tests con todos los estados mexicanos
Verifica que cada estado tiene datos correctos y la función buscar_agebs_por_cp funciona
"""

import pytest
import psycopg2
import os
from typing import Dict, List, Tuple


# Mapeo de todos los 32 estados mexicanos con CPs de prueba
ESTADOS_TEST_DATA = {
    '01': {'nombre': 'Aguascalientes', 'cp_test': '20000', 'abbrev': 'ags'},
    '02': {'nombre': 'Baja California', 'cp_test': '21000', 'abbrev': 'bc'},
    '03': {'nombre': 'Baja California Sur', 'cp_test': '23000', 'abbrev': 'bcs'},
    '04': {'nombre': 'Campeche', 'cp_test': '24000', 'abbrev': 'camp'},
    '05': {'nombre': 'Coahuila', 'cp_test': '25000', 'abbrev': 'coah'},
    '06': {'nombre': 'Colima', 'cp_test': '28000', 'abbrev': 'col'},
    '07': {'nombre': 'Chiapas', 'cp_test': '29000', 'abbrev': 'chis'},
    '08': {'nombre': 'Chihuahua', 'cp_test': '31000', 'abbrev': 'chih'},
    '09': {'nombre': 'Ciudad de México', 'cp_test': '11560', 'abbrev': 'cdmx'},
    '10': {'nombre': 'Durango', 'cp_test': '34000', 'abbrev': 'dgo'},
    '11': {'nombre': 'Guanajuato', 'cp_test': '36000', 'abbrev': 'gto'},
    '12': {'nombre': 'Guerrero', 'cp_test': '39000', 'abbrev': 'gro'},
    '13': {'nombre': 'Hidalgo', 'cp_test': '42000', 'abbrev': 'hgo'},
    '14': {'nombre': 'Jalisco', 'cp_test': '44100', 'abbrev': 'jal'},
    '15': {'nombre': 'Estado de México', 'cp_test': '50000', 'abbrev': 'mex'},
    '16': {'nombre': 'Michoacán', 'cp_test': '58000', 'abbrev': 'mich'},
    '17': {'nombre': 'Morelos', 'cp_test': '62000', 'abbrev': 'mor'},
    '18': {'nombre': 'Nayarit', 'cp_test': '63000', 'abbrev': 'nay'},
    '19': {'nombre': 'Nuevo León', 'cp_test': '64000', 'abbrev': 'nl'},
    '20': {'nombre': 'Oaxaca', 'cp_test': '68000', 'abbrev': 'oax'},
    '21': {'nombre': 'Puebla', 'cp_test': '72000', 'abbrev': 'pue'},
    '22': {'nombre': 'Querétaro', 'cp_test': '76000', 'abbrev': 'qro'},
    '23': {'nombre': 'Quintana Roo', 'cp_test': '77000', 'abbrev': 'qroo'},
    '24': {'nombre': 'San Luis Potosí', 'cp_test': '78000', 'abbrev': 'slp'},
    '25': {'nombre': 'Sinaloa', 'cp_test': '80000', 'abbrev': 'sin'},
    '26': {'nombre': 'Sonora', 'cp_test': '83000', 'abbrev': 'son'},
    '27': {'nombre': 'Tabasco', 'cp_test': '86000', 'abbrev': 'tab'},
    '28': {'nombre': 'Tamaulipas', 'cp_test': '87000', 'abbrev': 'tamps'},
    '29': {'nombre': 'Tlaxcala', 'cp_test': '90000', 'abbrev': 'tlax'},
    '30': {'nombre': 'Veracruz', 'cp_test': '91000', 'abbrev': 'ver'},
    '31': {'nombre': 'Yucatán', 'cp_test': '97000', 'abbrev': 'yuc'},
    '32': {'nombre': 'Zacatecas', 'cp_test': '98000', 'abbrev': 'zac'},
}


@pytest.fixture(scope="module")
def db_conn():
    """Fixture para conexión a la base de datos (módulo scope para eficiencia)"""
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


@pytest.fixture(scope="module")
def loaded_states(db_conn) -> List[str]:
    """Obtener lista de estados que están cargados en la BD"""
    with db_conn.cursor() as cur:
        # Estados con datos SEPOMEX
        cur.execute("""
            SELECT DISTINCT substring(table_name from 'cp_(\\d{2})_') as estado_cve
            FROM information_schema.tables
            WHERE table_schema = 'sepomex'
            AND table_name LIKE 'cp_%'
            ORDER BY estado_cve;
        """)
        sepomex_estados = {row[0] for row in cur.fetchall() if row[0]}

        # Estados con datos INEGI (urbanas)
        cur.execute("""
            SELECT DISTINCT substring(table_name from 'ageb_urbana_(\\d{2})') as estado_cve
            FROM information_schema.tables
            WHERE table_schema = 'inegi'
            AND table_name LIKE 'ageb_urbana_%'
            ORDER BY estado_cve;
        """)
        inegi_urbana = {row[0] for row in cur.fetchall() if row[0]}

        # Estados con datos INEGI (rurales)
        cur.execute("""
            SELECT DISTINCT substring(table_name from 'ageb_rural_(\\d{2})') as estado_cve
            FROM information_schema.tables
            WHERE table_schema = 'inegi'
            AND table_name LIKE 'ageb_rural_%'
            ORDER BY estado_cve;
        """)
        inegi_rural = {row[0] for row in cur.fetchall() if row[0]}

        # Estados completos = tienen SEPOMEX + INEGI urbana + INEGI rural
        estados_completos = sepomex_estados & inegi_urbana & inegi_rural

        return sorted(list(estados_completos))


class TestAllStatesLoaded:
    """Tests para verificar que todos los estados cargados tienen datos válidos"""

    def test_states_count(self, loaded_states):
        """Verificar que hay al menos un estado cargado"""
        assert len(loaded_states) > 0, "No hay estados cargados en la base de datos"
        print(f"\n✓ Estados cargados: {len(loaded_states)}/32")
        print(f"  Códigos: {', '.join(loaded_states)}")

    def test_each_state_has_sepomex_data(self, db_conn, loaded_states):
        """Verificar que cada estado cargado tiene datos SEPOMEX"""
        for estado_cve in loaded_states:
            with db_conn.cursor() as cur:
                # Encontrar tabla SEPOMEX del estado
                cur.execute(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name LIKE 'cp_{estado_cve}_%'
                    LIMIT 1;
                """)
                result = cur.fetchone()
                assert result is not None, f"Estado {estado_cve} no tiene tabla SEPOMEX"

                table_name = result[0]

                # Verificar que tiene datos
                cur.execute(f"SELECT COUNT(*) FROM sepomex.{table_name};")
                count = cur.fetchone()[0]
                assert count > 0, f"Tabla SEPOMEX {table_name} está vacía"

                estado_info = ESTADOS_TEST_DATA.get(estado_cve, {'nombre': 'Desconocido'})
                print(f"  ✓ {estado_cve} ({estado_info['nombre']}): {count:,} códigos postales")

    def test_each_state_has_inegi_urbana_data(self, db_conn, loaded_states):
        """Verificar que cada estado cargado tiene AGEBs urbanas"""
        for estado_cve in loaded_states:
            with db_conn.cursor() as cur:
                table_name = f'ageb_urbana_{estado_cve}'
                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM inegi.{table_name};
                """)
                count = cur.fetchone()[0]
                assert count > 0, f"Tabla INEGI urbana {table_name} está vacía"

                estado_info = ESTADOS_TEST_DATA.get(estado_cve, {'nombre': 'Desconocido'})
                print(f"  ✓ {estado_cve} ({estado_info['nombre']}): {count:,} AGEBs urbanas")

    def test_each_state_has_inegi_rural_data(self, db_conn, loaded_states):
        """Verificar que cada estado cargado tiene AGEBs rurales"""
        for estado_cve in loaded_states:
            with db_conn.cursor() as cur:
                table_name = f'ageb_rural_{estado_cve}'
                cur.execute(f"""
                    SELECT COUNT(*)
                    FROM inegi.{table_name};
                """)
                count = cur.fetchone()[0]
                # Algunos estados pueden tener 0 AGEBs rurales (ej: CDMX)
                # pero la tabla debe existir

                estado_info = ESTADOS_TEST_DATA.get(estado_cve, {'nombre': 'Desconocido'})
                if count > 0:
                    print(f"  ✓ {estado_cve} ({estado_info['nombre']}): {count:,} AGEBs rurales")
                else:
                    print(f"  ⚠ {estado_cve} ({estado_info['nombre']}): 0 AGEBs rurales (puede ser normal)")

    def test_each_state_table_structure(self, db_conn, loaded_states):
        """Verificar que cada tabla tiene las columnas correctas"""
        for estado_cve in loaded_states:
            with db_conn.cursor() as cur:
                # Verificar SEPOMEX
                cur.execute(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name LIKE 'cp_{estado_cve}_%'
                    LIMIT 1;
                """)
                sepomex_table = cur.fetchone()
                if sepomex_table:
                    cur.execute(f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'sepomex'
                        AND table_name = '{sepomex_table[0]}';
                    """)
                    columns = {row[0] for row in cur.fetchall()}
                    assert 'd_cp' in columns, f"Falta columna d_cp en {sepomex_table[0]}"
                    assert 'geom' in columns, f"Falta columna geom en {sepomex_table[0]}"

                # Verificar INEGI urbana
                table_urbana = f'ageb_urbana_{estado_cve}'
                cur.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'inegi'
                    AND table_name = '{table_urbana}';
                """)
                columns = {row[0] for row in cur.fetchall()}
                assert 'cvegeo' in columns, f"Falta columna cvegeo en {table_urbana}"
                assert 'geom' in columns, f"Falta columna geom en {table_urbana}"

                # Verificar INEGI rural
                table_rural = f'ageb_rural_{estado_cve}'
                cur.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'inegi'
                    AND table_name = '{table_rural}';
                """)
                columns = {row[0] for row in cur.fetchall()}
                assert 'cvegeo' in columns, f"Falta columna cvegeo en {table_rural}"
                assert 'geom' in columns, f"Falta columna geom en {table_rural}"


class TestAllStatesFunctionality:
    """Tests para verificar funcionalidad con cada estado"""

    def test_buscar_agebs_function_works_for_each_state(self, db_conn, loaded_states):
        """Verificar que la función buscar_agebs_por_cp funciona para cada estado"""
        estados_con_resultados = 0
        estados_sin_cp_test = 0

        for estado_cve in loaded_states:
            estado_info = ESTADOS_TEST_DATA[estado_cve]
            cp_test = estado_info['cp_test']

            with db_conn.cursor() as cur:
                try:
                    # Intentar buscar con el CP de prueba
                    cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp_test}');")
                    results = cur.fetchall()

                    if len(results) > 0:
                        # Verificar estructura básica
                        assert len(results[0]) == 4, \
                            f"Estructura incorrecta para {estado_info['nombre']} (CP: {cp_test})"

                        # Verificar que retorna el CP correcto
                        assert results[0][0] == cp_test, \
                            f"CP retornado incorrecto para {estado_info['nombre']}"

                        # Verificar tipos de AGEB
                        tipos = {row[2] for row in results}
                        assert tipos.issubset({'urbana', 'rural'}), \
                            f"Tipos de AGEB inválidos para {estado_info['nombre']}"

                        # Verificar porcentajes
                        total_porcentaje = sum(row[3] for row in results)
                        assert 95 <= total_porcentaje <= 105, \
                            f"Porcentajes incorrectos para {estado_info['nombre']}: {total_porcentaje}%"

                        estados_con_resultados += 1
                        print(f"  ✓ {estado_cve} ({estado_info['nombre']}) CP {cp_test}: "
                              f"{len(results)} AGEBs, {total_porcentaje:.1f}%")

                    else:
                        # El CP no existe en la base de datos
                        estados_sin_cp_test += 1
                        print(f"  ⚠ {estado_cve} ({estado_info['nombre']}) CP {cp_test}: "
                              f"No encontrado (probar con otro CP)")

                except psycopg2.Error as e:
                    if "no encontrado" in str(e):
                        estados_sin_cp_test += 1
                        print(f"  ⚠ {estado_cve} ({estado_info['nombre']}) CP {cp_test}: "
                              f"No encontrado en la BD")
                    else:
                        raise

        print(f"\nResumen:")
        print(f"  Estados con resultados: {estados_con_resultados}/{len(loaded_states)}")
        print(f"  Estados sin CP de prueba: {estados_sin_cp_test}/{len(loaded_states)}")

        # Al menos 50% de los estados cargados deben tener resultados válidos
        assert estados_con_resultados >= len(loaded_states) * 0.5, \
            f"Muy pocos estados con resultados válidos: {estados_con_resultados}/{len(loaded_states)}"

    def test_sample_cp_from_each_state(self, db_conn, loaded_states):
        """Probar con un CP real de cada estado (tomado de la BD)"""
        for estado_cve in loaded_states:
            estado_info = ESTADOS_TEST_DATA[estado_cve]

            with db_conn.cursor() as cur:
                # Obtener un CP aleatorio de este estado
                cur.execute(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name LIKE 'cp_{estado_cve}_%'
                    LIMIT 1;
                """)
                result = cur.fetchone()
                if not result:
                    continue

                table_name = result[0]

                # Obtener primer CP
                cur.execute(f"""
                    SELECT d_cp
                    FROM sepomex.{table_name}
                    LIMIT 1;
                """)
                cp_result = cur.fetchone()
                if not cp_result:
                    continue

                cp = cp_result[0]

                # Probar función
                cur.execute(f"SELECT * FROM buscar_agebs_por_cp('{cp}');")
                results = cur.fetchall()

                assert len(results) > 0, \
                    f"No hay resultados para CP {cp} de {estado_info['nombre']}"

                # Verificar calidad
                total_pct = sum(row[3] for row in results)
                assert 95 <= total_pct <= 105, \
                    f"Porcentajes incorrectos para {estado_info['nombre']} CP {cp}: {total_pct}%"

                print(f"  ✓ {estado_cve} ({estado_info['nombre']}) CP {cp}: "
                      f"{len(results)} AGEBs, {total_pct:.1f}%")


class TestAllStatesDataQuality:
    """Tests de calidad de datos para todos los estados"""

    def test_geometries_validity_all_states(self, db_conn, loaded_states):
        """Verificar validez de geometrías para todos los estados"""
        invalid_counts = {}

        for estado_cve in loaded_states:
            estado_info = ESTADOS_TEST_DATA[estado_cve]

            with db_conn.cursor() as cur:
                # Verificar SEPOMEX
                cur.execute(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name LIKE 'cp_{estado_cve}_%'
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
                    total, invalid = cur.fetchone()

                    if total > 0:
                        invalid_pct = (invalid / total) * 100
                        if invalid_pct > 0:
                            invalid_counts[f"{estado_cve}_sepomex"] = invalid_pct

                        assert invalid_pct < 5.0, \
                            f"Demasiadas geometrías inválidas en SEPOMEX {estado_cve}: {invalid}/{total} ({invalid_pct:.1f}%)"

                # Verificar INEGI urbana
                table_urbana = f'ageb_urbana_{estado_cve}'
                cur.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) as invalid
                    FROM inegi.{table_urbana};
                """)
                total, invalid = cur.fetchone()

                if total > 0:
                    invalid_pct = (invalid / total) * 100
                    if invalid_pct > 0:
                        invalid_counts[f"{estado_cve}_urbana"] = invalid_pct

                    assert invalid_pct < 5.0, \
                        f"Demasiadas geometrías inválidas en INEGI urbana {estado_cve}: {invalid}/{total} ({invalid_pct:.1f}%)"

        if invalid_counts:
            print(f"\n⚠ Estados con geometrías inválidas (<5%):")
            for key, pct in invalid_counts.items():
                print(f"  {key}: {pct:.2f}%")

    def test_srid_consistency_all_states(self, db_conn, loaded_states):
        """Verificar que todos los estados tienen SRIDs correctos"""
        for estado_cve in loaded_states:
            with db_conn.cursor() as cur:
                # Verificar SEPOMEX
                cur.execute(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'sepomex'
                    AND table_name LIKE 'cp_{estado_cve}_%'
                    LIMIT 1;
                """)
                sepomex_table = cur.fetchone()

                if sepomex_table:
                    cur.execute(f"""
                        SELECT DISTINCT ST_SRID(geom) as srid
                        FROM sepomex.{sepomex_table[0]}
                        WHERE geom IS NOT NULL
                        LIMIT 1;
                    """)
                    result = cur.fetchone()
                    if result:
                        srid = result[0]
                        # SRIDs válidos: 900917, 900918, 900919 (Lambert Conformal Conic variants), 6372 (INEGI official)
                        assert srid in [900917, 900918, 900919, 6372], \
                            f"SRID inesperado en SEPOMEX {estado_cve}: {srid}"

                # Verificar INEGI urbana
                table_urbana = f'ageb_urbana_{estado_cve}'
                cur.execute(f"""
                    SELECT DISTINCT ST_SRID(geom) as srid
                    FROM inegi.{table_urbana}
                    WHERE geom IS NOT NULL
                    LIMIT 1;
                """)
                result = cur.fetchone()
                if result:
                    srid = result[0]
                    assert srid in [900917, 900918, 900919, 6372], \
                        f"SRID inesperado en INEGI urbana {estado_cve}: {srid}"

                # Verificar INEGI rural
                table_rural = f'ageb_rural_{estado_cve}'
                cur.execute(f"""
                    SELECT DISTINCT ST_SRID(geom) as srid
                    FROM inegi.{table_rural}
                    WHERE geom IS NOT NULL
                    LIMIT 1;
                """)
                result = cur.fetchone()
                if result:
                    srid = result[0]
                    assert srid in [900917, 900918, 900919, 6372], \
                        f"SRID inesperado en INEGI rural {estado_cve}: {srid}"


@pytest.mark.slow
class TestAllStatesComprehensive:
    """Tests comprehensivos que pueden tardar varios minutos"""

    def test_all_32_states_if_loaded(self, db_conn):
        """Test comprehensivo: verificar todos los 32 estados si están cargados"""
        estados_esperados = set(ESTADOS_TEST_DATA.keys())

        with db_conn.cursor() as cur:
            # Obtener estados cargados
            cur.execute("""
                SELECT DISTINCT substring(table_name from 'cp_(\\d{2})_') as estado_cve
                FROM information_schema.tables
                WHERE table_schema = 'sepomex'
                AND table_name LIKE 'cp_%'
                ORDER BY estado_cve;
            """)
            estados_cargados = {row[0] for row in cur.fetchall() if row[0]}

            print(f"\n{'='*70}")
            print(f"REPORTE COMPLETO: ESTADOS MEXICANOS")
            print(f"{'='*70}")
            print(f"Estados esperados: {len(estados_esperados)}")
            print(f"Estados cargados: {len(estados_cargados)}")
            print(f"Porcentaje: {len(estados_cargados)/len(estados_esperados)*100:.1f}%")
            print(f"{'='*70}\n")

            # Listar estados cargados
            if estados_cargados:
                print("✓ ESTADOS CARGADOS:")
                for cve in sorted(estados_cargados):
                    info = ESTADOS_TEST_DATA.get(cve, {'nombre': 'Desconocido'})
                    print(f"  {cve} - {info['nombre']}")

            # Listar estados faltantes
            estados_faltantes = estados_esperados - estados_cargados
            if estados_faltantes:
                print(f"\n⚠ ESTADOS FALTANTES ({len(estados_faltantes)}):")
                for cve in sorted(estados_faltantes):
                    info = ESTADOS_TEST_DATA[cve]
                    print(f"  {cve} - {info['nombre']}")

            print(f"\n{'='*70}")

            # Si hay menos del 50% cargado, advertir pero no fallar
            if len(estados_cargados) < len(estados_esperados) * 0.5:
                pytest.skip(
                    f"Solo {len(estados_cargados)}/32 estados cargados. "
                    "Cargar más estados para ejecutar este test completo."
                )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
