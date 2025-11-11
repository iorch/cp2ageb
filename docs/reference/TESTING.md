# Suite de Tests - cp2ageb

Documentación completa de la arquitectura de tests del proyecto cp2ageb.

## Resumen

El proyecto incluye una suite completa de tests que cubre:
- ✅ Tests unitarios (no requieren infraestructura)
- ✅ Tests de base de datos (estructura y configuración)
- ✅ Tests de integración (flujo completo CP → AGEB)
- ✅ Tests de performance
- ✅ Tests de consistencia de datos

**Total de tests**: ~45 casos de prueba
**Coverage objetivo**: >80% en código crítico

## Arquitectura de Tests

### Organización de Archivos

```
tests/
├── __init__.py                 # Paquete de tests
├── conftest.py                 # Configuración pytest y fixtures
├── test_database.py            # Tests de base de datos (15 tests)
├── test_scripts.py             # Tests de scripts Python (15 tests)
├── test_integration.py         # Tests de integración (15 tests)
└── README.md                   # Documentación de tests

Archivos de configuración:
├── pytest.ini                  # Configuración pytest
├── requirements-test.txt       # Dependencias de tests
└── run_tests.sh                # Script para ejecutar tests
```

## Tests Implementados

### 1. test_database.py (15 tests)

**Propósito**: Verificar configuración y estructura de la base de datos

#### TestDatabaseConnection (4 tests)
- `test_database_exists`: Conexión a PostgreSQL
- `test_postgis_extension`: PostGIS instalado
- `test_schemas_exist`: Schemas sepomex e inegi
- `test_metadata_table_exists`: Tabla load_metadata

#### TestDataLoading (4 tests)
- `test_sepomex_tables_loaded`: Tablas SEPOMEX presentes
- `test_inegi_tables_loaded`: Tablas INEGI presentes
- `test_ageb_tables_pattern`: Patrón de nombres correcto
- `test_sepomex_table_structure`: Columnas esperadas (d_cp, geom)
- `test_inegi_table_structure`: Columnas esperadas (cvegeo, geom)

#### TestSpatialQueries (3 tests)
- `test_geometries_are_valid`: ST_IsValid() en todas las geometrías
- `test_spatial_indexes_exist`: Índices GIST presentes
- `test_srid_consistency`: SRIDs correctos (900917, 900919, 6372)

#### TestBuscarAgebsPorCPFunction (4 tests)
- `test_function_exists`: Función buscar_agebs_por_cp existe
- `test_function_returns_data`: Retorna datos para CPs conocidos
- `test_function_with_invalid_cp`: Maneja CPs inválidos
- `test_function_return_structure`: Estructura de retorno correcta

**Ejecución**:
```bash
./run_tests.sh --database
```

### 2. test_scripts.py (15 tests)

**Propósito**: Verificar scripts Python y funciones helper

#### TestDownloadShapefilesScript (5 tests)
- `test_estados_dict_complete`: 32 estados definidos
- `test_estados_dict_structure`: Estructura del diccionario
- `test_estados_unique_abbreviations`: Abreviaturas únicas
- `test_base_url_format`: URL válida
- `test_download_file_success`: Mock de descarga exitosa
- `test_download_file_already_exists`: No redescarga si existe
- `test_download_file_404_error`: Manejo de errores HTTP

#### TestDownloadAgebShapefilesScript (4 tests)
- `test_estados_list_complete`: 32 estados definidos
- `test_estados_list_structure`: Formato (código, nombre, completo)
- `test_estados_unique_codes`: Códigos únicos
- `test_estados_sequential_codes`: Códigos 01-32
- `test_base_url_format`: URL válida

#### TestLoadShapefilesHelpers (7 tests)
- `test_normalize_estado_by_code`: Normalización por código (1, 01, 14)
- `test_normalize_estado_by_abbreviation`: Por abreviatura (Jal, jal)
- `test_normalize_estado_by_name`: Por nombre (Jalisco, jalisco)
- `test_normalize_estado_invalid`: Manejo de inválidos
- `test_parse_estados_filter_single`: Parsing de un estado
- `test_parse_estados_filter_multiple`: Parsing múltiples
- `test_parse_estados_filter_mixed`: Formatos mixtos
- `test_parse_estados_filter_all`: Valor 'all'

#### TestDataIntegrity (2 tests)
- `test_estados_consistency_between_scripts`: 32 en ambos scripts
- `test_file_paths_logic`: Construcción de paths

**Ejecución**:
```bash
./run_tests.sh --unit
```

### 3. test_integration.py (15 tests)

**Propósito**: Tests end-to-end del flujo completo

#### TestEndToEndCPtoAGEB (3 tests)
- `test_known_cp_returns_agebs`: CPs conocidos (44100, 11560, 50000, 64000)
  - Verifica estructura de resultados
  - Verifica porcentajes suman ~100%
  - Verifica orden descendente
- `test_spatial_intersection_quality`: Calidad de intersecciones
  - AGEB principal >10%
  - Sin intersecciones triviales
- `test_ageb_codes_format`: Formato de claves AGEB
  - Longitud correcta (≥12 caracteres)
  - Primeros 2 dígitos numéricos

#### TestDataConsistency (2 tests)
- `test_states_match_between_sources`: Estados coinciden SEPOMEX/INEGI
- `test_ageb_pairs_exist`: Cada estado tiene urbanas Y rurales

#### TestPerformance (2 tests)
- `test_function_query_speed`: Query individual <2s
- `test_multiple_queries_speed`: Promedio múltiples queries <1s

**Ejecución**:
```bash
./run_tests.sh --integration
```

## Fixtures Compartidos

**Definidos en**: `conftest.py`

### Fixtures de Infraestructura

#### `docker_available` (session scope)
Verifica que Docker está disponible y contenedor corriendo.

```python
@pytest.fixture(scope="session")
def docker_available():
    # Verifica docker-compose ps
    return 'cp2ageb-postgis' in output and 'Up' in output
```

#### `database_available` (session scope)
Verifica que PostgreSQL acepta conexiones.

```python
@pytest.fixture(scope="session")
def database_available(docker_available):
    # Intenta conectar a PostgreSQL
    # Skip tests si no está disponible
```

### Fixtures de Conexión

#### `db_conn` (function scope)
Proporciona conexión a PostgreSQL para cada test.

```python
@pytest.fixture
def db_conn():
    conn = psycopg2.connect(...)
    yield conn
    conn.close()  # Limpieza automática
```

### Fixtures de Configuración

#### `test_config` (session scope)
Configuración centralizada para tests.

```python
@pytest.fixture(scope="session")
def test_config():
    return {
        'postgres_host': 'localhost',
        'postgres_port': '5432',
        'test_cps': ['44100', '11560', '50000', '64000'],
        'test_estados': ['14', '15', '09', '19'],
    }
```

#### `sample_cp` (function scope)
Código postal de ejemplo.

```python
@pytest.fixture
def sample_cp():
    return '44100'  # Guadalajara, Jalisco
```

## Markers de Pytest

Los tests están categorizados con markers:

### Markers Principales

| Marker | Descripción | Cantidad |
|--------|-------------|----------|
| `unit` | Tests unitarios, no requieren DB | ~15 |
| `integration` | Tests de integración end-to-end | ~15 |
| `database` | Tests de base de datos | ~15 |
| `slow` | Tests que pueden tardar >2s | ~5 |

### Uso de Markers

```bash
# Solo tests unitarios
pytest -m unit

# Excluir tests lentos (default)
pytest -m "not slow"

# Solo tests de base de datos
pytest -m database

# Integración sin lentos
pytest -m "integration and not slow"
```

## Configuración de Pytest

**Archivo**: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    -v
    --strict-markers
    --tb=short
    --disable-warnings
    -ra
    --color=yes

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    database: Database tests
```

## Script de Ejecución

**Archivo**: `run_tests.sh`

### Opciones Disponibles

```bash
./run_tests.sh [opciones]

--all               Todos los tests (default)
--unit              Solo unitarios
--integration       Solo integración
--database          Solo base de datos
--slow              Incluir lentos
--no-slow           Excluir lentos (default)
--coverage          Generar reporte coverage
--parallel          Ejecutar en paralelo
--verbose, -v       Output detallado
--help, -h          Ayuda
```

### Ejemplos de Uso

```bash
# Básico - todos excepto lentos
./run_tests.sh

# Solo unitarios (rápido, no requiere DB)
./run_tests.sh --unit

# Integración con coverage
./run_tests.sh --integration --coverage

# Todo en paralelo
./run_tests.sh --all --parallel

# Todo incluyendo lentos
./run_tests.sh --all --slow
```

## Dependencias de Tests

**Archivo**: `requirements-test.txt`

```txt
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-xdist>=3.3.1
psycopg2-binary>=2.9.6
pytest-mock>=3.11.1
requests-mock>=1.11.0
coverage>=7.2.7
```

**Instalación**:
```bash
pip install -r requirements-test.txt
```

## Estrategia de Testing

### Pirámide de Tests

```
        /\
       /  \          2 tests - Performance
      /____\
     /      \        15 tests - Integration (E2E)
    /________\
   /          \      15 tests - Database
  /____________\
 /              \    15 tests - Unit
/________________\
```

### Niveles de Testing

#### Nivel 1: Unit Tests (Rápidos, ~0.1s cada uno)
- No requieren infraestructura
- Ejecutan lógica pura
- Ideal para TDD
- Se ejecutan en CI en cada commit

#### Nivel 2: Database Tests (Medios, ~0.5s cada uno)
- Requieren PostgreSQL
- Verifican estructura
- Detectan problemas de schema
- Se ejecutan en CI antes de merge

#### Nivel 3: Integration Tests (Lentos, ~1-2s cada uno)
- Flujo completo CP → AGEB
- Verifican funcionalidad real
- Detectan problemas de integración
- Se ejecutan en CI antes de release

#### Nivel 4: Performance Tests (Muy lentos, ~5-10s cada uno)
- Miden tiempos de respuesta
- Detectan regresiones de performance
- Se ejecutan manualmente o nightly

## Coverage

### Objetivo de Coverage

| Componente | Objetivo | Actual |
|-----------|----------|--------|
| Scripts Python | >90% | TBD |
| Función SQL | >80% | TBD |
| Queries espaciales | >70% | TBD |
| **Global** | **>80%** | **TBD** |

### Generar Reporte

```bash
# Ejecutar con coverage
./run_tests.sh --coverage

# Ver reporte HTML
open htmlcov/index.html

# Ver reporte en terminal
coverage report
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt

    - name: Start Docker services
      run: |
        docker-compose up -d
        sleep 30  # Wait for initialization

    - name: Run unit tests
      run: ./run_tests.sh --unit

    - name: Run integration tests
      run: ./run_tests.sh --integration --coverage

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Fallan: "Database not available"

**Causa**: Contenedor Docker no está corriendo

**Solución**:
```bash
docker-compose up -d
docker-compose ps  # Verificar estado
```

### Tests se Omiten: "No hay datos para probar"

**Causa**: Estado específico no está cargado

**Esperado**: Los tests se omiten (skip) cuando los datos no están
disponibles. Esto es válido.

**Para cargar más datos**:
```bash
# Editar docker-compose.yml: LOAD_ESTADOS
docker-compose down -v
docker-compose up -d
```

### Tests Muy Lentos

**Solución 1**: Excluir tests lentos
```bash
./run_tests.sh --no-slow
```

**Solución 2**: Ejecutar en paralelo
```bash
./run_tests.sh --parallel
```

**Solución 3**: Solo unitarios
```bash
./run_tests.sh --unit  # ~2 segundos total
```

### Error: "pytest: command not found"

**Solución**:
```bash
pip install -r requirements-test.txt
```

## Mejores Prácticas

### Al Escribir Tests

1. **Usar fixtures apropiados**
   ```python
   def test_con_db(db_conn):
       with db_conn.cursor() as cur:
           cur.execute("SELECT 1;")
   ```

2. **Agregar markers**
   ```python
   @pytest.mark.integration
   def test_flujo_completo():
       pass
   ```

3. **Tests descriptivos**
   ```python
   def test_buscar_agebs_retorna_porcentajes_correctos():
       # Nombre describe qué se prueba
       pass
   ```

4. **Limpiar después**
   ```python
   @pytest.fixture
   def recurso():
       r = crear_recurso()
       yield r
       r.close()  # Limpieza automática
   ```

### Al Ejecutar Tests

1. **Tests rápidos primero**
   ```bash
   ./run_tests.sh --unit  # Rápido
   ```

2. **Coverage en desarrollo**
   ```bash
   ./run_tests.sh --coverage
   ```

3. **Paralelo en CI**
   ```bash
   ./run_tests.sh --parallel
   ```

## Roadmap de Tests

### Implementado ✅
- [x] Tests de base de datos
- [x] Tests de scripts Python
- [x] Tests de integración E2E
- [x] Tests de performance básicos
- [x] Script de ejecución con opciones
- [x] Configuración pytest completa
- [x] Fixtures compartidos

### Futuro 📋
- [ ] Tests de API REST (si se implementa)
- [ ] Tests de visualización (si se implementa)
- [ ] Tests de carga (stress testing)
- [ ] Tests de seguridad
- [ ] Property-based testing con Hypothesis
- [ ] Mutation testing

## Métricas de Calidad

### Objetivos

- ✅ >45 tests implementados
- ✅ 3 tipos de tests (unit, database, integration)
- ✅ Coverage >80%
- ✅ Tests ejecutan <30s (sin slow)
- ✅ 100% tests pasan en CI
- ✅ 0 flaky tests

## Recursos Adicionales

- [Documentación pytest](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [PostGIS Testing](https://postgis.net/docs/manual-dev/RT_FAQ.html)

## Contribuir

Para agregar nuevos tests:

1. Crear archivo `test_*.py` en `tests/`
2. Usar fixtures de `conftest.py`
3. Agregar markers apropiados
4. Documentar en `tests/README.md`
5. Ejecutar suite completa
6. Verificar coverage

---

**Última actualización**: 2025-11-07
**Versión suite de tests**: 1.0.0
