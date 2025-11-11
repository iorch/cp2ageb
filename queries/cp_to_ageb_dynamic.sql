-- ============================================================================
-- Query Dinámico: Detecta automáticamente la entidad del CP
-- ============================================================================

-- ⚙️ DEFINIR CÓDIGO POSTAL A BUSCAR:
DO $$
DECLARE
    codigo_postal_busqueda TEXT := '44100';  -- Cambiar aquí el CP a buscar
    estado_cve TEXT;
    tabla_cp TEXT;
    tabla_cp_final TEXT;
    tabla_ageb_urbana TEXT;
    tabla_ageb_rural TEXT;
    query_dinamico TEXT;
    tabla_record RECORD;
    cp_count INTEGER;
BEGIN
    -- Paso 1: Buscar en qué entidad está el código postal
    RAISE NOTICE 'Buscando código postal: %', codigo_postal_busqueda;

    -- Buscar en todas las tablas de SEPOMEX
    FOR tabla_record IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'sepomex'
          AND table_name LIKE 'cp_%'
        ORDER BY table_name
    LOOP
        tabla_cp := tabla_record.table_name;

        -- Verificar si el CP existe en esta tabla usando un contador
        EXECUTE format('SELECT COUNT(*) FROM sepomex.%I WHERE d_cp = %L',
                      tabla_cp, codigo_postal_busqueda)
        INTO cp_count;

        IF cp_count > 0 THEN
            -- Extraer el código de estado (2 dígitos después de cp_)
            estado_cve := substring(tabla_cp from 'cp_(\d{2})_');
            tabla_cp_final := tabla_cp;
            EXIT;
        END IF;
    END LOOP;

    IF estado_cve IS NULL THEN
        RAISE EXCEPTION 'Código postal % no encontrado en ninguna entidad', codigo_postal_busqueda;
    END IF;

    RAISE NOTICE 'Código postal encontrado en entidad: %', estado_cve;

    -- Paso 2: Construir nombres de tablas
    tabla_ageb_urbana := 'ageb_urbana_' || estado_cve;
    tabla_ageb_rural := 'ageb_rural_' || estado_cve;

    RAISE NOTICE 'Tablas a usar:';
    RAISE NOTICE '  CP: sepomex.%', tabla_cp_final;
    RAISE NOTICE '  AGEB Urbana: inegi.%', tabla_ageb_urbana;
    RAISE NOTICE '  AGEB Rural: inegi.%', tabla_ageb_rural;

    -- Paso 3: Ejecutar query dinámico
    query_dinamico := format($q$
        WITH cp_ageb_intersections AS (
          SELECT
              cp.d_cp as codigo_postal,
              ageb.cvegeo as clave_ageb,
              'urbana' as tipo_ageb,
              ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
              ST_Area(ST_Transform(cp.geom, 6372)) * 100 as porcentaje
          FROM sepomex.%I cp
          JOIN inegi.%I ageb
            ON ST_Intersects(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))
          WHERE cp.d_cp = %L

          UNION ALL

          SELECT
              cp.d_cp,
              ageb.cvegeo,
              'rural' as tipo_ageb,
              ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) /
              ST_Area(ST_Transform(cp.geom, 6372)) * 100 as porcentaje
          FROM sepomex.%I cp
          JOIN inegi.%I ageb
            ON ST_Intersects(ST_Transform(cp.geom, 6372), ageb.geom)
          WHERE cp.d_cp = %L
        )
        SELECT
            codigo_postal,
            clave_ageb,
            tipo_ageb,
            ROUND(porcentaje::numeric, 2) as porcentaje_interseccion
        FROM cp_ageb_intersections
        WHERE porcentaje > 0.01
        ORDER BY porcentaje DESC;
    $q$,
    tabla_cp_final, tabla_ageb_urbana, codigo_postal_busqueda,
    tabla_cp_final, tabla_ageb_rural, codigo_postal_busqueda);

    -- Ejecutar y mostrar resultados
    RAISE NOTICE 'Ejecutando query...';
    RAISE NOTICE '';

    -- Crear tabla temporal con resultados
    DROP TABLE IF EXISTS tmp_cp_agebs;
    CREATE TEMP TABLE tmp_cp_agebs (
        codigo_postal TEXT,
        clave_ageb TEXT,
        tipo_ageb TEXT,
        porcentaje_interseccion NUMERIC
    );

    -- Insertar resultados en tabla temporal
    EXECUTE format('INSERT INTO tmp_cp_agebs %s', query_dinamico);

END $$;

-- Mostrar resultados de la tabla temporal
SELECT * FROM tmp_cp_agebs;
