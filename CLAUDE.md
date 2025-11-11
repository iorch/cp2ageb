# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Maps Mexican Postal Codes (SEPOMEX) to INEGI's AGEB geographic units using PostGIS spatial analysis in Docker.

**Domain Context:**
- **SEPOMEX** - Mexico's postal service (códigos postales)
- **INEGI** - National statistics institute (geographic divisions)
- **AGEB** - Áreas Geoestadísticas Básicas (basic census units)

## Architecture

**Database Structure:**
- PostGIS 16 + PostGIS 3.4 in Docker
- Schemas: `sepomex` (postal codes), `inegi` (AGEBs), `public` (metadata)
- Table naming: `cp_{state}_cp_{abbrev}`, `ageb_urbana_{state}`, `ageb_rural_{state}`
- State codes: 01-32 (01=Aguascalientes, 14=Jalisco, 09=CDMX, etc.)

**Key Components:**
- `docker/entrypoint.sh` - Orchestrates download → load → function creation on startup
- `docker/init-db.sh` - DB initialization (schemas, extensions, PostGIS)
- `scripts/load_shapefiles.py` - Main loader with ZIP validation and selective loading
- `download_*.py` - Smart downloaders with integrity checks
- `queries/cp_to_ageb_function.sql` - Dynamic PL/pgSQL function

**Data Flow:**
1. Auto-download shapefiles (if `AUTO_DOWNLOAD=true`, only missing/corrupt files)
2. Auto-load to PostGIS (if `AUTO_LOAD=true`, skip existing tables)
3. Create `buscar_agebs_por_cp()` function (if not exists)

## Critical Spatial Query Information

**Mixed SRIDs Require Transformation:**
- SEPOMEX: SRID 900917, 900918 (Lambert Conformal Conic variants)
- INEGI urbana: SRID 900919 (Lambert Conformal Conic variant)
- INEGI rural: SRID 6372 (EPSG:6372 - INEGI official)
- **Always use `ST_Transform(..., 6372)` to unify geometries**

**Important Columns:**
- SEPOMEX: `d_cp` (postal code text), `geom` (MultiPolygon)
- INEGI: `cvegeo` (AGEB identifier), `geom` (MultiPolygon)

**Always Query Both Urban AND Rural AGEBs:**
Querying only urban OR rural returns incomplete data. Use the provided function or UNION ALL pattern.

## Essential Development Commands

**Docker Operations:**
```bash
# Start with auto-download/load (default config: 4 main states)
docker-compose up -d

# View startup progress
docker-compose logs -f postgis

# Stop and preserve data
docker-compose down

# Stop and delete all data (fresh restart)
docker-compose down -v

# Connect to PostgreSQL
docker-compose exec postgis psql -U geouser -d cp2ageb

# Reload shapefiles manually
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

**Testing:**
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
./run_tests.sh

# Unit tests only (no DB required)
./run_tests.sh --unit

# Integration tests (requires Docker running)
./run_tests.sh --integration

# With coverage report
./run_tests.sh --coverage
```

**Search AGEBs by Postal Code:**
```bash
# Using wrapper script (recommended)
./buscar_cp.sh 44100

# Direct SQL function call
docker-compose exec postgis psql -U geouser -d cp2ageb \
  -c "SELECT * FROM buscar_agebs_por_cp('44100');"
```

**Manual Downloads (if auto-download fails):**
```bash
# Download SEPOMEX shapefiles
python3 download_shapefiles.py

# Download INEGI shapefiles (with corruption detection)
python3 download_ageb_shapefiles.py

# Inside Docker container
docker-compose exec postgis python3 /app/download_shapefiles.py
docker-compose exec postgis python3 /app/download_ageb_shapefiles.py
```

**Benchmark Performance:**
```bash
# Quick benchmark (Aguascalientes only)
./benchmark.sh

# Full benchmark (all 32 states)
./benchmark.sh --full

# Clean start (delete all cached data)
./benchmark.sh --clean --full
```

## Environment Variables

**In `docker-compose.yml`:**
```yaml
AUTO_DOWNLOAD: "true"   # Auto-download missing shapefiles on startup
AUTO_LOAD: "true"       # Auto-load shapefiles to PostGIS on startup

# Layer control (optimize load time)
LOAD_AGEBS: "true"      # Required for CP→AGEB mapping
LOAD_MANZANAS: "false"  # Optional, adds ~50% to load time
LOAD_LOCALIDADES: "false"
LOAD_MUNICIPIOS: "false"
LOAD_ENTIDADES: "false"

# State control (for testing or partial loads)
LOAD_ESTADOS: "all"     # Options: "all", "14", "14,15,09", "Jal,CDMX", etc.

# Advanced loader controls
VALIDATE_ZIPS: "quick"  # Options: "quick", "full", "none"
FORCE_RELOAD: "false"   # Skip existing tables (false) or reload all (true)
```

**Quick Test Setup:**
```bash
# Fast test: single state, only AGEBs (~20 min)
LOAD_ESTADOS="14" docker-compose up -d
```

## Core Spatial Query Pattern

**Use the Provided Function (Recommended):**
```sql
-- Automatically detects state and queries both urban/rural AGEBs
SELECT * FROM buscar_agebs_por_cp('44100');
```

**Manual Query Template (if modifying):**
```sql
WITH search_params AS (
  SELECT '44100' as codigo_postal_busqueda
),
cp_ageb_intersections AS (
  -- Urban AGEBs (transform both to SRID 6372)
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

  -- Rural AGEBs (rural already uses SRID 6372)
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
WHERE porcentaje > 0.01  -- Filter negligible intersections
ORDER BY porcentaje DESC;
```

## Test Architecture

**Test Markers (pytest):**
- `@pytest.mark.unit` - No database required
- `@pytest.mark.integration` - Requires Docker DB running
- `@pytest.mark.database` - Database structure/function tests
- `@pytest.mark.slow` - Tests taking >2 seconds

**Test Files:**
- `tests/test_scripts.py` - Python script validation (21 tests)
- `tests/test_database.py` - DB structure and SQL functions (16 tests)
- `tests/test_integration.py` - End-to-end workflows (7 tests)
- `tests/conftest.py` - Shared fixtures

**Running Specific Tests:**
```bash
# Single test file
pytest tests/test_database.py

# Single test function
pytest tests/test_database.py::test_buscar_agebs_por_cp_function

# Exclude slow tests (default)
./run_tests.sh --no-slow
```

## Common Development Scenarios

**Adding a New SQL Query:**
1. Create query in `queries/` directory
2. If it's a function, update `docker/entrypoint.sh` to load it
3. Add tests in `tests/test_database.py`
4. Test with `./run_tests.sh --integration`

**Modifying the Loader:**
1. Edit `scripts/load_shapefiles.py`
2. Test with single state: `LOAD_ESTADOS="01" docker-compose down -v && docker-compose up -d`
3. Add unit tests in `tests/test_scripts.py`
4. Run `./run_tests.sh --unit`

**ZIP Corruption Issues:**
- Scripts auto-detect and re-download corrupt ZIPs automatically
- Some INEGI state files may occasionally have download issues (handled by retry logic)
- `VALIDATE_ZIPS="full"` for exhaustive checking (slower)
- If persistent, delete corrupted file and restart: `rm data/ageb_shapefiles/XX_estado.zip && docker-compose restart`

**Performance Tuning:**
- Use `ST_Intersects()` for spatial joins (indexed)
- Filter tiny intersections: `WHERE porcentaje > 0.01`
- Load only needed layers: `LOAD_MANZANAS=false` saves ~50% time
- Test with single state first: `LOAD_ESTADOS="01"`

## Database Credentials

**Connection (external from host):**
- Host: localhost:5432
- Database: cp2ageb
- User: geouser
- Password: geopassword

**Connection (internal from scripts):**
- Uses Unix socket: `/var/run/postgresql`
- Faster than TCP/IP connection

## Data Sources

### SEPOMEX (Códigos Postales)
Servicio Postal Mexicano - Geographic postal code boundaries by state.

- **URL**: https://www.datos.gob.mx/dataset/codigos_postales_entidad_federativa
- **Download Base**: https://repodatos.atdt.gob.mx/api_update/sepomex/codigos_postales_entidad_federativa
- **Format**: Shapefiles (.shp, .dbf, .shx, .prj) - 32 files (one per state)
- **License**: Creative Commons Attribution 4.0
- **Updated**: July 2025

### INEGI (Marco Geoestadístico 2020)
Instituto Nacional de Estadística y Geografía - Basic Geostatistical Areas (AGEBs) and territorial divisions.

- **Information page**: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173
- **Format**: Shapefiles - 32 files per layer
- **Layers**: Urban AGEBs, Rural AGEBs, Manzanas, Localities, Municipalities
- **Edition**: Marco Geoestadístico Nacional, December 2020
- **Download**: Automatic via `download_ageb_shapefiles.py` script (direct file download, no web interface)

## Useful SQL Inspection Queries

```sql
-- List loaded tables
\dt sepomex.*
\dt inegi.*

-- Check load metadata
SELECT * FROM public.load_metadata ORDER BY loaded_at DESC;

-- Count postal codes per state
SELECT COUNT(*) FROM sepomex.cp_14_cp_jal;

-- Count AGEBs
SELECT COUNT(*) FROM inegi.ageb_urbana_14;
SELECT COUNT(*) FROM inegi.ageb_rural_14;

-- Check if function exists
\df buscar_agebs_por_cp

-- View function definition
\sf buscar_agebs_por_cp
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.
