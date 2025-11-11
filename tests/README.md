# Tests - cp2ageb

Suite de tests para el proyecto cp2ageb.

## Estructura de Tests

```
tests/
├── conftest.py              # Configuración de pytest y fixtures compartidos
├── test_database.py         # Tests de base de datos y conexión (16 tests)
├── test_scripts.py          # Tests de scripts Python (21 tests)
├── test_integration.py      # Tests de integración end-to-end (7 tests)
├── test_all_states.py       # Tests con todos los estados (NUEVO)
├── test_data_quality.py     # Tests de calidad de datos (NUEVO)
├── ANALISIS_TESTS.md        # Análisis de cobertura y gaps
└── README.md               # Este archivo
```

## Tipos de Tests

### 1. Tests Unitarios (`unit`)
Tests que no requieren base de datos ni infraestructura externa.

**Archivo**: `test_scripts.py`

**Cobertura**:
- Validación de diccionarios y listas de estados
- Funciones helper de normalización de estados
- Parsing de filtros de estados
- Lógica de construcción de paths

**Ejecutar**:
```bash
./run_tests.sh --unit
```

### 2. Tests de Base de Datos (`database`)
Tests que verifican la estructura y configuración de la base de datos.

**Archivo**: `test_database.py`

**Cobertura**:
- Conexión a PostgreSQL
- Extensión PostGIS instalada
- Schemas (sepomex, inegi) existen
- Tablas cargadas correctamente
- Estructura de columnas
- Geometrías válidas
- Índices espaciales
- SRIDs correctos

**Ejecutar**:
```bash
./run_tests.sh --database
```

### 3. Tests de Integración (`integration`)
Tests end-to-end que verifican el flujo completo CP → AGEB.

**Archivo**: `test_integration.py`

**Cobertura**:
- Función `buscar_agebs_por_cp()` con CPs conocidos
- Calidad de intersecciones espaciales
- Formato de claves AGEB
- Consistencia entre SEPOMEX e INEGI
- Performance de queries
- Tests con múltiples CPs

**Ejecutar**:
```bash
./run_tests.sh --integration
```

## Instalación

### 1. Instalar dependencias de tests:

```bash
pip install -r requirements-test.txt
```

### 2. Asegurar que el contenedor Docker está corriendo:

```bash
docker-compose up -d

# Verificar estado
docker-compose ps
```

## Ejecución de Tests

### Uso Básico

```bash
# Ejecutar todos los tests (excepto lentos)
./run_tests.sh

# O directamente con pytest
pytest
```

### Por Tipo de Test

```bash
# Solo tests unitarios (rápidos, no requieren DB)
./run_tests.sh --unit

# Solo tests de integración (requieren DB)
./run_tests.sh --integration

# Solo tests de base de datos
./run_tests.sh --database
```

### Con Coverage

```bash
# Generar reporte de coverage
./run_tests.sh --coverage

# Ver reporte HTML
open htmlcov/index.html
```

### Tests en Paralelo

```bash
# Ejecutar en paralelo (más rápido)
./run_tests.sh --parallel
```

### Incluir Tests Lentos

```bash
# Incluir tests de performance
./run_tests.sh --all --slow
```

### Combinaciones

```bash
# Integration con coverage en paralelo
./run_tests.sh --integration --coverage --parallel

# Todo con coverage y tests lentos
./run_tests.sh --all --slow --coverage
```

## Markers de Pytest

Los tests están organizados con markers de pytest:

- `@pytest.mark.unit` - Tests unitarios
- `@pytest.mark.integration` - Tests de integración
- `@pytest.mark.database` - Tests de base de datos
- `@pytest.mark.slow` - Tests que pueden tardar varios segundos

### Uso con pytest directamente:

```bash
# Solo tests unitarios
pytest -m unit

# Excluir tests lentos
pytest -m "not slow"

# Solo tests de base de datos
pytest -m database

# Combinaciones
pytest -m "integration and not slow"
```

## Fixtures Compartidos

**Definidos en**: `conftest.py`

### `docker_available`
Verifica si Docker está disponible y el contenedor corriendo.

### `database_available`
Verifica si la base de datos acepta conexiones.

### `db_conn`
Fixture para obtener conexión a la base de datos.
Automáticamente cierra la conexión al terminar el test.

### `test_config`
Diccionario con configuración de tests:
- Credenciales de PostgreSQL
- CPs de prueba
- Estados de prueba

### `sample_cp`
Código postal de ejemplo para tests (44100).

## Tests Específicos

### TestDatabaseConnection
Verifica configuración básica de PostgreSQL y PostGIS.

### TestDataLoading
Verifica que los datos estén cargados correctamente.

### TestSpatialQueries
Verifica funcionalidad espacial (geometrías, índices, SRIDs).

### TestBuscarAgebsPorCPFunction
Verifica la función principal de búsqueda.

### TestEndToEndCPtoAGEB
Tests end-to-end con CPs conocidos de los 4 estados principales.

### TestDataConsistency
Verifica consistencia entre datos SEPOMEX e INEGI.

### TestPerformance
Mide tiempos de respuesta de queries.

## Nuevos Tests (Extendidos)

### TestAllStatesLoaded (`test_all_states.py`)
**Descripción**: Verifica que TODOS los estados cargados tienen datos correctos.

**Tests incluidos**:
- `test_states_count` - Cuenta cuántos estados están cargados
- `test_each_state_has_sepomex_data` - Cada estado tiene CPs
- `test_each_state_has_inegi_urbana_data` - Cada estado tiene AGEBs urbanas
- `test_each_state_has_inegi_rural_data` - Cada estado tiene AGEBs rurales
- `test_each_state_table_structure` - Verifica columnas en todas las tablas
- `test_buscar_agebs_function_works_for_each_state` - Función funciona con los 32 estados
- `test_sample_cp_from_each_state` - Prueba con CP real de cada estado
- `test_geometries_validity_all_states` - Geometrías válidas en todos los estados
- `test_srid_consistency_all_states` - SRIDs correctos en todos los estados
- `test_all_32_states_if_loaded` - Reporte completo de los 32 estados

**Ejecutar**:
```bash
pytest tests/test_all_states.py -v
```

**Nota**: Este test es especialmente útil cuando se cargan todos los estados (`LOAD_ESTADOS="all"`).

### TestDataQuality (`test_data_quality.py`)
**Descripción**: Verifica la calidad e invariantes de los datos cargados.

**Categorías de tests**:

1. **TestPercentageTotals** - Porcentajes suman ~100%
   - `test_percentages_sum_to_100_sample` - Muestra de CPs suma correctamente
   - `test_no_zero_percentages_above_threshold` - No hay porcentajes de 0%

2. **TestNoDuplicates** - No hay duplicados
   - `test_no_duplicate_agebs_in_results` - No hay AGEBs duplicados
   - `test_no_duplicate_tipo_ageb_combination` - No hay pares AGEB+tipo duplicados

3. **TestAGEBCodeFormat** - Formato de claves AGEB
   - `test_ageb_codes_start_with_state_code` - Empiezan con código correcto
   - `test_ageb_codes_minimum_length` - Longitud válida (9-15 chars)
   - `test_ageb_codes_numeric_prefix` - Prefijo numérico válido

4. **TestGeometryQuality** - Calidad de geometrías
   - `test_no_null_geometries` - No hay geometrías nulas
   - `test_no_empty_geometries` - No hay geometrías vacías
   - `test_geometries_have_reasonable_area` - Áreas > 0

5. **TestResultsOrdering** - Orden correcto
   - `test_results_ordered_by_percentage_desc` - Ordenados por % descendente

6. **TestDataConsistency** - Consistencia
   - `test_cp_matches_in_all_results` - CP correcto en todos los resultados
   - `test_tipo_ageb_valid_values` - Solo 'urbana' o 'rural'
   - `test_both_urban_and_rural_agebs_present` - Ambos tipos presentes

**Ejecutar**:
```bash
pytest tests/test_data_quality.py -v
```

**Valor**: Estos tests detectan problemas de calidad de datos que los tests funcionales no cubren.

## Análisis de Cobertura

Ver archivo `ANALISIS_TESTS.md` para:
- Análisis detallado de gaps en cobertura actual
- Propuestas de tests adicionales (prioridad alta/media/baja)
- Estadísticas de cobertura por tipo de test
- Roadmap de mejoras futuras

## Interpretación de Resultados

### Éxito
```
============== 15 passed in 2.34s ==============
```

### Tests Omitidos
```
============== 10 passed, 5 skipped in 1.23s ==============
```
Tests omitidos generalmente significa que:
- El contenedor Docker no está corriendo
- Los datos para ese estado no están cargados
- Es esperado y válido

### Fallas
```
============== 2 failed, 13 passed in 3.45s ==============
```
Ver detalles del error para diagnosticar.

## Troubleshooting

### Error: "pytest: command not found"
```bash
pip install -r requirements-test.txt
```

### Error: "Database not available"
```bash
# Iniciar contenedor
docker-compose up -d

# Verificar que está corriendo
docker-compose ps

# Ver logs
docker-compose logs postgis
```

### Error: "No hay datos para probar"
Algunos tests requieren datos cargados. Si los tests se omiten (skip), es normal.

Para cargar datos:
```bash
# Verificar qué estados están cargados
docker-compose exec postgis psql -U geouser -d cp2ageb -c "\dt sepomex.*"

# Cargar más estados si es necesario (editar docker-compose.yml)
docker-compose down -v
docker-compose up -d
```

### Tests muy lentos
```bash
# Excluir tests lentos (default)
./run_tests.sh --no-slow

# Ejecutar en paralelo
./run_tests.sh --parallel
```

## Agregar Nuevos Tests

### 1. Crear archivo de test

```python
# tests/test_nuevo.py
import pytest

class TestNuevaFuncionalidad:
    def test_algo(self):
        assert True
```

### 2. Agregar markers apropiados

```python
@pytest.mark.unit
def test_funcion_helper():
    pass

@pytest.mark.integration
def test_flujo_completo():
    pass

@pytest.mark.slow
def test_performance():
    pass
```

### 3. Usar fixtures si es necesario

```python
def test_con_db(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT 1;")
        assert cur.fetchone()[0] == 1
```

## CI/CD Integration

Los tests están diseñados para integrarse con CI/CD:

```yaml
# Ejemplo GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements-test.txt
    docker-compose up -d
    ./run_tests.sh --all --coverage
```

## Métricas de Coverage

Objetivo: >80% coverage en código crítico

Ver reporte:
```bash
./run_tests.sh --coverage
open htmlcov/index.html
```

## Contacto y Contribuciones

Para reportar problemas con los tests o sugerir nuevos casos de prueba,
crear un issue en el repositorio.
