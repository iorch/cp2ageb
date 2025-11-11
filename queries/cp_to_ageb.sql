-- ============================================================================
-- Queries para mapear Códigos Postales a AGEBs
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. EXPLORAR ESTRUCTURA DE DATOS
-- ----------------------------------------------------------------------------

-- Ver estructura de tabla de códigos postales (ejemplo Aguascalientes)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'sepomex'
  AND table_name LIKE 'cp_01%'
LIMIT 20;

-- Ver estructura de tabla de AGEBs urbanas (ejemplo Aguascalientes)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'inegi'
  AND table_name = 'ageb_urbana_01'
LIMIT 20;

-- Ver un registro de ejemplo de código postal
SELECT * FROM sepomex.cp_01_cp_ags LIMIT 1;

-- Ver un registro de ejemplo de AGEB
SELECT * FROM inegi.ageb_urbana_01 LIMIT 1;


-- ----------------------------------------------------------------------------
-- 2. QUERY BÁSICO: Encontrar AGEBs que intersectan un Código Postal
-- ----------------------------------------------------------------------------

-- Encontrar AGEBs urbanas que intersectan con un código postal específico
-- Ejemplo para Jalisco (Guadalajara, CP 44100), ajusta los nombres de tabla según tu estado
-- ⚠️ IMPORTANTE: Los shapefiles usan diferentes SRIDs
--    SEPOMEX: 900917, INEGI urbana: 900919, INEGI rural: 6372
--    Usar ST_Transform(..., 6372) para unificar a EPSG:6372

-- ⚙️ DEFINIR CÓDIGO POSTAL A BUSCAR:
WITH search_params AS (
    SELECT '44100' as codigo_postal_busqueda  -- Ejemplo: Guadalajara, Jalisco
)
SELECT
    cp.d_cp as codigo_postal,
    ageb.cvegeo as clave_ageb,
    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
    ST_Area(ST_Transform(cp.geom, 6372)) * 100 as porcentaje_interseccion
FROM
    sepomex.cp_14_cp_jal cp
CROSS JOIN
    inegi.ageb_urbana_14 ageb,
    search_params
WHERE
    ST_Intersects(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))
    AND cp.d_cp = search_params.codigo_postal_busqueda
ORDER BY
    porcentaje_interseccion DESC;


-- ----------------------------------------------------------------------------
-- 3. QUERY COMPLETO: CP a AGEBs (urbanas y rurales)
-- ----------------------------------------------------------------------------

-- Buscar en AGEBs urbanas Y rurales para un código postal
-- ⚠️ IMPORTANTE: Usar ST_Transform(..., 6372) para unificar SRIDs mixtos

-- ⚙️ DEFINIR CÓDIGO POSTAL A BUSCAR:
WITH search_params AS (
    SELECT '44100' as codigo_postal_busqueda  -- Ejemplo: Guadalajara, Jalisco
),
cp_geom AS (
    SELECT
        d_cp as codigo_postal,
        ST_Transform(geom, 6372) as geom
    FROM sepomex.cp_14_cp_jal
    WHERE d_cp = (SELECT codigo_postal_busqueda FROM search_params)
),
agebs_urbanas AS (
    SELECT
        'urbana' as tipo,
        ageb.cvegeo as clave_ageb,
        ST_Transform(ageb.geom, 6372) as geom,
        cp.codigo_postal
    FROM cp_geom cp
    CROSS JOIN inegi.ageb_urbana_14 ageb
    WHERE ST_Intersects(cp.geom, ST_Transform(ageb.geom, 6372))
),
agebs_rurales AS (
    SELECT
        'rural' as tipo,
        ageb.cvegeo as clave_ageb,
        ageb.geom,  -- Ya usa SRID 6372
        cp.codigo_postal
    FROM cp_geom cp
    CROSS JOIN inegi.ageb_rural_14 ageb
    WHERE ST_Intersects(cp.geom, ageb.geom)
)
SELECT
    codigo_postal,
    tipo,
    clave_ageb,
    ST_Area(ST_Intersection((SELECT geom FROM cp_geom), geom)) as area_interseccion_m2,
    ST_Area(ST_Intersection((SELECT geom FROM cp_geom), geom)) /
        ST_Area((SELECT geom FROM cp_geom)) * 100 as porcentaje_cp,
    ST_Area(ST_Intersection((SELECT geom FROM cp_geom), geom)) /
        ST_Area(geom) * 100 as porcentaje_ageb
FROM (
    SELECT * FROM agebs_urbanas
    UNION ALL
    SELECT * FROM agebs_rurales
) combined
ORDER BY area_interseccion_m2 DESC;


-- ----------------------------------------------------------------------------
-- 4. QUERY PARA MÚLTIPLES CÓDIGOS POSTALES
-- ----------------------------------------------------------------------------

-- Mapear TODOS los códigos postales a sus AGEBs correspondientes
-- Ejemplo para Jalisco - ajustar tablas según el estado deseado
-- ⚠️ IMPORTANTE: Usar ST_Transform(..., 6372) para unificar SRIDs mixtos
SELECT
    cp.d_cp as codigo_postal,
    ageb.cvegeo as clave_ageb,
    'urbana' as tipo_ageb,
    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
    ST_Area(ST_Transform(cp.geom, 6372)) * 100 as porcentaje_interseccion,
    CASE
        WHEN ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
             ST_Area(ST_Transform(cp.geom, 6372)) > 0.5
        THEN 'principal'
        ELSE 'parcial'
    END as tipo_relacion
FROM
    sepomex.cp_14_cp_jal cp
CROSS JOIN
    inegi.ageb_urbana_14 ageb
WHERE
    ST_Intersects(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))
    AND ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
        ST_Area(ST_Transform(cp.geom, 6372)) > 0.01  -- Al menos 1% de intersección

UNION ALL

SELECT
    cp.d_cp as codigo_postal,
    ageb.cvegeo as clave_ageb,
    'rural' as tipo_ageb,
    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) /
    ST_Area(ST_Transform(cp.geom, 6372)) * 100 as porcentaje_interseccion,
    CASE
        WHEN ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) /
             ST_Area(ST_Transform(cp.geom, 6372)) > 0.5
        THEN 'principal'
        ELSE 'parcial'
    END as tipo_relacion
FROM
    sepomex.cp_14_cp_jal cp
CROSS JOIN
    inegi.ageb_rural_14 ageb
WHERE
    ST_Intersects(ST_Transform(cp.geom, 6372), ageb.geom)
    AND ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) /
        ST_Area(ST_Transform(cp.geom, 6372)) > 0.01

ORDER BY codigo_postal, porcentaje_interseccion DESC;


-- ----------------------------------------------------------------------------
-- 5. CREAR TABLA DE MAPEO CP → AGEB
-- ----------------------------------------------------------------------------

-- Crear tabla permanente con el mapeo
CREATE TABLE IF NOT EXISTS public.cp_to_ageb_mapping (
    id SERIAL PRIMARY KEY,
    estado_cve VARCHAR(2),
    codigo_postal VARCHAR(10),
    clave_ageb VARCHAR(20),
    tipo_ageb VARCHAR(10),
    porcentaje_interseccion NUMERIC(5,2),
    tipo_relacion VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_to_ageb_cp ON public.cp_to_ageb_mapping(codigo_postal);
CREATE INDEX IF NOT EXISTS idx_cp_to_ageb_ageb ON public.cp_to_ageb_mapping(clave_ageb);
CREATE INDEX IF NOT EXISTS idx_cp_to_ageb_estado ON public.cp_to_ageb_mapping(estado_cve);

-- Insertar datos de Jalisco (replicar para cada estado)
-- ⚠️ IMPORTANTE: Usar ST_Transform(..., 6372) para unificar SRIDs mixtos
INSERT INTO public.cp_to_ageb_mapping (
    estado_cve, codigo_postal,
    clave_ageb, tipo_ageb, porcentaje_interseccion, tipo_relacion
)
SELECT
    '14' as estado_cve,
    cp.d_cp,
    ageb.cvegeo,
    'urbana',
    ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
    ST_Area(ST_Transform(cp.geom, 6372)) * 100,
    CASE
        WHEN ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
             ST_Area(ST_Transform(cp.geom, 6372)) > 0.5
        THEN 'principal'
        ELSE 'parcial'
    END
FROM
    sepomex.cp_14_cp_jal cp
CROSS JOIN
    inegi.ageb_urbana_14 ageb
WHERE
    ST_Intersects(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))
    AND ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
        ST_Area(ST_Transform(cp.geom, 6372)) > 0.01;

-- Repetir para AGEBs rurales y para cada estado


-- ----------------------------------------------------------------------------
-- 6. QUERIES DE CONSULTA SOBRE LA TABLA DE MAPEO
-- ----------------------------------------------------------------------------

-- Buscar AGEBs por código postal
SELECT * FROM public.cp_to_ageb_mapping
WHERE codigo_postal = '44100'  -- Ejemplo: Guadalajara, Jalisco
ORDER BY porcentaje_interseccion DESC;

-- Buscar códigos postales por AGEB
SELECT * FROM public.cp_to_ageb_mapping
WHERE clave_ageb = '140010001001A'  -- Ejemplo: AGEB en Jalisco
ORDER BY porcentaje_interseccion DESC;

-- Contar relaciones por estado
SELECT
    estado_cve,
    COUNT(DISTINCT codigo_postal) as total_cps,
    COUNT(DISTINCT clave_ageb) as total_agebs,
    COUNT(*) as total_relaciones
FROM public.cp_to_ageb_mapping
GROUP BY estado_cve
ORDER BY estado_cve;

-- Ver códigos postales que cubren múltiples AGEBs
SELECT
    codigo_postal,
    asentamiento,
    COUNT(*) as num_agebs,
    STRING_AGG(clave_ageb, ', ' ORDER BY porcentaje_interseccion DESC) as agebs
FROM public.cp_to_ageb_mapping
GROUP BY codigo_postal, asentamiento
HAVING COUNT(*) > 1
ORDER BY num_agebs DESC;
