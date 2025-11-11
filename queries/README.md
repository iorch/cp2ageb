# Queries de Mapeo CP → AGEB

Esta carpeta contiene queries SQL para mapear Códigos Postales de SEPOMEX a AGEBs de INEGI usando análisis espacial con PostGIS.

## Archivos

- **`cp_to_ageb.sql`** - Colección completa de queries SQL
- **`../scripts/create_cp_ageb_mapping.py`** - Script automatizado para crear el mapeo

## Uso Rápido

### Opción 1: Script Automatizado (Recomendado)

```bash
# Ejecutar desde el contenedor
docker-compose exec postgis python3 /scripts/create_cp_ageb_mapping.py

# O desde tu máquina local
python scripts/create_cp_ageb_mapping.py
```

Este script:
- Crea la tabla `public.cp_to_ageb_mapping`
- Procesa automáticamente los 32 estados
- Incluye AGEBs urbanas y rurales
- Calcula porcentajes de intersección
- Clasifica relaciones como "principal" o "parcial"

### Opción 2: Queries Manuales

```bash
# Conectar a la base de datos
docker-compose exec postgis psql -U geouser -d cp2ageb

# Ejecutar query para un código postal específico
\i /app/queries/cp_to_ageb.sql
```

## Tipos de Queries Disponibles

### 1. Query Básico: Un CP → Sus AGEBs

```sql
-- Encontrar todos los AGEBs que intersectan un código postal
SELECT
    cp.d_codigo as codigo_postal,
    ageb.cvegeo as clave_ageb,
    ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) * 100 as porcentaje
FROM sepomex.cp_01_cp_ags cp
CROSS JOIN inegi.ageb_urbana_01 ageb
WHERE ST_Intersects(cp.geom, ageb.geom)
  AND cp.d_codigo = '20000'
ORDER BY porcentaje DESC;
```

### 2. Query con AGEBs Urbanas y Rurales

```sql
-- Buscar en ambos tipos de AGEBs
SELECT
    cp.d_codigo,
    ageb.cvegeo,
    'urbana' as tipo,
    ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) * 100 as porcentaje
FROM sepomex.cp_01_cp_ags cp
JOIN inegi.ageb_urbana_01 ageb ON ST_Intersects(cp.geom, ageb.geom)
WHERE cp.d_codigo = '20000'

UNION ALL

SELECT
    cp.d_codigo,
    ageb.cvegeo,
    'rural' as tipo,
    ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) * 100 as porcentaje
FROM sepomex.cp_01_cp_ags cp
JOIN inegi.ageb_rural_01 ageb ON ST_Intersects(cp.geom, ageb.geom)
WHERE cp.d_codigo = '20000'

ORDER BY porcentaje DESC;
```

### 3. Query para Todos los CPs de un Estado

```sql
-- Crear mapeo completo para Aguascalientes
SELECT
    cp.d_codigo as codigo_postal,
    cp.d_asenta as asentamiento,
    ageb.cvegeo as clave_ageb,
    CASE
        WHEN ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) > 0.5
        THEN 'principal'
        ELSE 'parcial'
    END as tipo_relacion,
    ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) * 100 as porcentaje
FROM sepomex.cp_01_cp_ags cp
CROSS JOIN inegi.ageb_urbana_01 ageb
WHERE ST_Intersects(cp.geom, ageb.geom)
  AND ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) > 0.01
ORDER BY cp.d_codigo, porcentaje DESC;
```

## Tabla de Mapeo Consolidada

Después de ejecutar el script, tendrás una tabla `public.cp_to_ageb_mapping` con:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | ID único |
| `estado_cve` | VARCHAR(2) | Clave del estado (01-32) |
| `estado_nombre` | VARCHAR(100) | Nombre del estado |
| `codigo_postal` | VARCHAR(10) | Código postal |
| `asentamiento` | VARCHAR(255) | Nombre del asentamiento |
| `ciudad` | VARCHAR(255) | Ciudad |
| `clave_ageb` | VARCHAR(20) | Clave AGEB (CVEGEO) |
| `tipo_ageb` | VARCHAR(10) | "urbana" o "rural" |
| `area_interseccion_m2` | NUMERIC | Área de intersección en m² |
| `porcentaje_interseccion` | NUMERIC(5,2) | % del CP que intersecta |
| `tipo_relacion` | VARCHAR(20) | "principal" (>50%) o "parcial" (<50%) |

### Queries sobre la Tabla de Mapeo

```sql
-- Buscar AGEBs por código postal
SELECT * FROM public.cp_to_ageb_mapping
WHERE codigo_postal = '20000'
ORDER BY porcentaje_interseccion DESC;

-- Buscar CPs por AGEB
SELECT * FROM public.cp_to_ageb_mapping
WHERE clave_ageb = '010010001001A';

-- Contar relaciones por estado
SELECT
    estado_cve,
    estado_nombre,
    COUNT(DISTINCT codigo_postal) as total_cps,
    COUNT(DISTINCT clave_ageb) as total_agebs,
    COUNT(*) as total_relaciones
FROM public.cp_to_ageb_mapping
GROUP BY estado_cve, estado_nombre
ORDER BY estado_cve;

-- CPs que cubren múltiples AGEBs
SELECT
    codigo_postal,
    asentamiento,
    COUNT(*) as num_agebs,
    STRING_AGG(clave_ageb, ', ') as agebs
FROM public.cp_to_ageb_mapping
GROUP BY codigo_postal, asentamiento
HAVING COUNT(*) > 1
ORDER BY num_agebs DESC
LIMIT 20;

-- AGEBs que tienen múltiples CPs
SELECT
    clave_ageb,
    tipo_ageb,
    COUNT(*) as num_cps,
    STRING_AGG(codigo_postal, ', ') as cps
FROM public.cp_to_ageb_mapping
GROUP BY clave_ageb, tipo_ageb
HAVING COUNT(*) > 1
ORDER BY num_cps DESC
LIMIT 20;
```

## Estadísticas y Análisis

```sql
-- Distribución de tipos de relación
SELECT
    tipo_relacion,
    COUNT(*) as cantidad,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as porcentaje
FROM public.cp_to_ageb_mapping
GROUP BY tipo_relacion;

-- Promedio de AGEBs por CP
SELECT
    AVG(agebs_por_cp) as promedio_agebs,
    MIN(agebs_por_cp) as minimo,
    MAX(agebs_por_cp) as maximo
FROM (
    SELECT codigo_postal, COUNT(*) as agebs_por_cp
    FROM public.cp_to_ageb_mapping
    GROUP BY codigo_postal
) subq;

-- Promedio de CPs por AGEB
SELECT
    AVG(cps_por_ageb) as promedio_cps,
    MIN(cps_por_ageb) as minimo,
    MAX(cps_por_ageb) as maximo
FROM (
    SELECT clave_ageb, COUNT(*) as cps_por_ageb
    FROM public.cp_to_ageb_mapping
    GROUP BY clave_ageb
) subq;

-- Comparación urbano vs rural
SELECT
    tipo_ageb,
    COUNT(DISTINCT codigo_postal) as cps_unicos,
    COUNT(DISTINCT clave_ageb) as agebs_unicos,
    COUNT(*) as total_relaciones,
    ROUND(AVG(porcentaje_interseccion), 2) as promedio_interseccion
FROM public.cp_to_ageb_mapping
GROUP BY tipo_ageb;
```

## Casos de Uso

### 1. Encontrar AGEB Principal de un CP

```sql
-- AGEB que tiene la mayor intersección con el CP
SELECT clave_ageb, tipo_ageb, porcentaje_interseccion
FROM public.cp_to_ageb_mapping
WHERE codigo_postal = '20000'
  AND tipo_relacion = 'principal'
ORDER BY porcentaje_interseccion DESC
LIMIT 1;
```

### 2. Verificar Cobertura Completa

```sql
-- Ver si un CP está completamente cubierto por AGEBs
SELECT
    codigo_postal,
    SUM(porcentaje_interseccion) as cobertura_total
FROM public.cp_to_ageb_mapping
WHERE codigo_postal = '20000'
GROUP BY codigo_postal;
-- Si cobertura_total ≈ 100%, el CP está completamente cubierto
```

### 3. Exportar a CSV

```bash
# Desde el contenedor
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "COPY (SELECT * FROM public.cp_to_ageb_mapping ORDER BY estado_cve, codigo_postal) \
   TO STDOUT CSV HEADER" > cp_to_ageb_mapping.csv

# Exportar solo un estado
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "COPY (SELECT * FROM public.cp_to_ageb_mapping WHERE estado_cve = '01' ORDER BY codigo_postal) \
   TO STDOUT CSV HEADER" > aguascalientes_mapping.csv
```

## Funciones PostGIS Utilizadas

- **`ST_Intersects(geom1, geom2)`** - Verifica si dos geometrías se intersectan
- **`ST_Intersection(geom1, geom2)`** - Retorna la geometría de intersección
- **`ST_Area(geom)`** - Calcula el área de una geometría
- **`ST_Contains(geom1, geom2)`** - Verifica si geom1 contiene completamente a geom2
- **`ST_Within(geom1, geom2)`** - Verifica si geom1 está completamente dentro de geom2

## Optimización

Para mejorar el rendimiento de queries espaciales:

```sql
-- Crear índices espaciales (si no existen)
CREATE INDEX IF NOT EXISTS idx_cp_ags_geom ON sepomex.cp_01_cp_ags USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_ageb_urb_geom ON inegi.ageb_urbana_01 USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_ageb_rur_geom ON inegi.ageb_rural_01 USING GIST (geom);

-- Analizar tablas para actualizar estadísticas
ANALYZE sepomex.cp_01_cp_ags;
ANALYZE inegi.ageb_urbana_01;
ANALYZE inegi.ageb_rural_01;
```

## Notas

- **Intersecciones Parciales**: Un código postal puede intersectar con múltiples AGEBs
- **Threshold**: Se usa un mínimo de 1% de intersección para evitar toques mínimos
- **Tipo de Relación**:
  - `principal`: El AGEB cubre más del 50% del CP
  - `parcial`: El AGEB cubre menos del 50% del CP
- **Coordenadas**: Todas las geometrías deben estar en el mismo sistema de coordenadas (SRID)

## Troubleshooting

### Query muy lento

```sql
-- Verificar índices espaciales
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname IN ('sepomex', 'inegi')
  AND indexdef LIKE '%GIST%';

-- Verificar estadísticas
SELECT schemaname, tablename, last_analyze
FROM pg_stat_user_tables
WHERE schemaname IN ('sepomex', 'inegi')
ORDER BY last_analyze;
```

### Resultados inesperados

```sql
-- Verificar SRID de las geometrías
SELECT
    'sepomex' as schema,
    ST_SRID(geom) as srid
FROM sepomex.cp_01_cp_ags LIMIT 1

UNION

SELECT
    'inegi' as schema,
    ST_SRID(geom) as srid
FROM inegi.ageb_urbana_01 LIMIT 1;

-- Si son diferentes, necesitas transformar
SELECT ST_Transform(geom, 4326) FROM ...
```
