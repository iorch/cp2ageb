# cp2ageb

**Mapeo de Códigos Postales mexicanos (SEPOMEX) a Áreas Geoestadísticas Básicas (AGEBs) de INEGI usando PostGIS.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![PostGIS 3.4](https://img.shields.io/badge/PostGIS-3.4-green.svg)](https://postgis.net/)

## Características

- Infraestructura completa en Docker
- Descarga inteligente (solo archivos faltantes o corruptos)
- Carga automática con control granular por estados y capas
- Análisis espacial con transformaciones SRID automáticas
- Mapeo CP → AGEB con porcentajes de intersección
- Función SQL dinámica para búsqueda sin conocer el estado
- 67 tests de validación

## Inicio Rápido

### Requisitos
- Docker y Docker Compose
- 20GB+ espacio en disco (depende de estados a cargar)

> **Nota**: Este proyecto funciona con `docker-compose` (v1) o `docker compose` (v2). Si usas Docker Desktop reciente, usa `docker compose` (sin guión). Los ejemplos usan `docker-compose` pero puedes reemplazarlo por `docker compose` en todos los comandos.

### Instalación en 3 pasos

```bash
# 1. Clonar repositorio
git clone https://github.com/iorch/cp2ageb.git
cd cp2ageb

# 2. Levantar contenedor (descarga y carga datos automáticamente)
docker-compose up -d

# 3. Monitorear progreso
docker-compose logs -f postgis
```

### Primer uso

```bash
# Buscar AGEBs por código postal
./buscar_cp.sh 44100  # Guadalajara, Jalisco

# O desde SQL
docker-compose exec postgis psql -U geouser -d cp2ageb
SELECT * FROM buscar_agebs_por_cp('44100');
```

**Tiempo primera carga:**
- 4 estados (default): ~1-2 horas
- Solo Jalisco (testing): ~20 minutos
- Todos los estados (32): ~8-10 horas

Ver: [QUICKSTART.md](QUICKSTART.md) | [INSTALL.md](INSTALL.md)

## Ejemplo de Uso

### Función SQL (Recomendado)

```sql
-- Búsqueda automática por CP
SELECT * FROM buscar_agebs_por_cp('44100');
```

**Resultado:**
```
 codigo_postal |   clave_ageb   | tipo_ageb | porcentaje_interseccion
---------------+----------------+-----------+------------------------
 44100         | 140100010014A  | urbana    |                   45.23
 44100         | 140100010013A  | urbana    |                   32.15
 44100         | 140100010012A  | urbana    |                   22.62
```

### Query SQL Manual

```sql
-- Para usuarios avanzados que quieran personalizar el query
WITH search_params AS (
  SELECT '44100' as codigo_postal_busqueda
),
cp_ageb_intersections AS (
  -- AGEBs urbanas
  SELECT
      cp.d_cp as codigo_postal,
      ageb.cvegeo as clave_ageb,
      'urbana' as tipo_ageb,
      ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
      ST_Area(ST_Transform(cp.geom, 6372)) * 100 as porcentaje
  FROM sepomex.cp_14_cp_jal cp
  JOIN inegi.ageb_urbana_14 ageb
    ON ST_Intersects(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))
  WHERE cp.d_cp = (SELECT codigo_postal_busqueda FROM search_params)

  UNION ALL

  -- AGEBs rurales
  SELECT
      cp.d_cp,
      ageb.cvegeo,
      'rural' as tipo_ageb,
      ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) /
      ST_Area(ST_Transform(cp.geom, 6372)) * 100 as porcentaje
  FROM sepomex.cp_14_cp_jal cp
  JOIN inegi.ageb_rural_14 ageb
    ON ST_Intersects(ST_Transform(cp.geom, 6372), ageb.geom)
  WHERE cp.d_cp = (SELECT codigo_postal_busqueda FROM search_params)
)
SELECT
    codigo_postal,
    clave_ageb,
    tipo_ageb,
    ROUND(porcentaje::numeric, 2) as porcentaje_interseccion
FROM cp_ageb_intersections
WHERE porcentaje > 0.01
ORDER BY porcentaje DESC;
```

Ver más ejemplos en [`queries/`](queries/)

## Configuración

### Variables de Entorno

```yaml
# docker-compose.yml
environment:
  # Control de descarga y carga
  AUTO_DOWNLOAD: "true"     # Descargar automáticamente
  AUTO_LOAD: "true"         # Cargar automáticamente

  # Estados a cargar (optimiza tiempo)
  LOAD_ESTADOS: "14,15,09,19"  # Jal, Edo Mex, CDMX, NL
  # O cargar todos: LOAD_ESTADOS: "all"

  # Capas a cargar (optimiza espacio)
  LOAD_AGEBS: "true"        # Requerido para CP→AGEB
  LOAD_MANZANAS: "false"    # Opcional, +50% tiempo
  LOAD_LOCALIDADES: "false"
  LOAD_MUNICIPIOS: "false"
```

### Cargar Solo Estados Específicos

```bash
# Solo Jalisco (testing rápido)
LOAD_ESTADOS="14" docker-compose up -d

# Múltiples estados
LOAD_ESTADOS="14,09,19" docker-compose up -d

# Todos los estados
LOAD_ESTADOS="all" docker-compose up -d
```

## Tests

```bash
# Instalar dependencias
pip install -r requirements-test.txt

# Ejecutar todos los tests (67 tests)
./run_tests.sh

# Solo tests unitarios (no requieren BD)
./run_tests.sh --unit

# Tests de integración (requieren Docker)
./run_tests.sh --integration

# Con coverage
./run_tests.sh --coverage
```

Ver [tests/README.md](tests/README.md) para más información.

## Estructura del Proyecto

```
cp2ageb/
├── data/                    # Datos descargados (auto-generado)
│   ├── cp_shapefiles/       # SEPOMEX shapefiles
│   └── ageb_shapefiles/     # INEGI shapefiles
├── docker/                  # Configuración Docker
│   ├── entrypoint.sh        # Orquestador principal
│   └── init-db.sh           # Inicialización BD
├── scripts/                 # Scripts de carga
│   ├── load_shapefiles.py   # Cargador principal
│   └── ...
├── queries/                 # Queries SQL de ejemplo
├── tests/                   # Suite de tests (67 tests)
├── docker-compose.yml       # Configuración Docker Compose
└── README.md               # Este archivo
```

## Documentación

- [QUICKSTART.md](QUICKSTART.md) - Guía de inicio rápido
- [INSTALL.md](INSTALL.md) - Instalación detallada y troubleshooting
- [tests/README.md](tests/README.md) - Documentación de tests
- [queries/README.md](queries/README.md) - Guía de queries SQL

## Fuentes de Datos

### SEPOMEX - Códigos Postales
Servicio Postal Mexicano - Delimitación geográfica de códigos postales por entidad federativa.

- **Fuente**: [datos.gob.mx - Códigos Postales](https://www.datos.gob.mx/dataset/codigos_postales_entidad_federativa)
- **Organización**: SEPOMEX (Servicio Postal Mexicano)
- **Formato**: Shapefiles (.shp, .dbf, .shx, .prj) - 32 archivos (uno por estado)
- **Licencia**: Creative Commons Attribution 4.0
- **Última actualización**: Julio 2025

### INEGI - Marco Geoestadístico 2020
Instituto Nacional de Estadística y Geografía - Áreas Geoestadísticas Básicas y otras divisiones territoriales.

- **Información**: [INEGI - Ficha del Marco Geoestadístico 2020](https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173)
- **Organización**: INEGI (Instituto Nacional de Estadística y Geografía)
- **Formato**: Shapefiles - 32 archivos por capa (descarga automática vía script)
- **Capas disponibles**:
  - AGEBs urbanas (áreas geoestadísticas básicas)
  - AGEBs rurales
  - Manzanas urbanas
  - Localidades
  - Municipios
- **Edición**: Marco Geoestadístico Nacional, diciembre 2020
- **Nota**: La descarga es automática al ejecutar `docker-compose up -d`. No requiere descarga manual.

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para guías de contribución.

## Notas Técnicas

### SRIDs y Transformaciones

Los shapefiles usan diferentes sistemas de referencia espacial:
- **SEPOMEX**: SRID 900917, 900918 (Lambert Conformal Conic)
- **INEGI urbana**: SRID 900919 (Lambert Conformal Conic)
- **INEGI rural**: SRID 6372 (EPSG:6372 - proyección oficial INEGI)

**Solución**: Todas las geometrías se transforman a SRID 6372 usando `ST_Transform(geom, 6372)`

### Base de Datos

**Conexión externa (desde host):**
```
Host: localhost
Port: 5432
Database: cp2ageb
User: geouser
Password: geopassword
```

**Schemas:**
- `sepomex` - Códigos postales (tablas: `cp_{estado}_cp_{abbrev}`)
- `inegi` - AGEBs (tablas: `ageb_urbana_{estado}`, `ageb_rural_{estado}`)
- `public` - Metadatos y funciones

## Licencia

MIT License - ver [LICENSE](LICENSE)

## Créditos

- **SEPOMEX** - Servicio Postal Mexicano
- **INEGI** - Instituto Nacional de Estadística y Geografía
