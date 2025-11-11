-- ============================================================================
-- Función: buscar_agebs_por_cp
-- Busca automáticamente los AGEBs de un código postal en cualquier entidad
-- ============================================================================

CREATE OR REPLACE FUNCTION buscar_agebs_por_cp(codigo_postal_busqueda TEXT)
RETURNS TABLE (
    codigo_postal TEXT,
    clave_ageb TEXT,
    tipo_ageb TEXT,
    porcentaje_interseccion NUMERIC
) AS $$
DECLARE
    estado_cve TEXT;
    tabla_cp TEXT;
    tabla_ageb_urbana TEXT;
    tabla_ageb_rural TEXT;
    query_dinamico TEXT;
    tabla_record RECORD;
    cp_count INTEGER;
BEGIN
    -- Paso 1: Buscar en qué entidad está el código postal
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
            EXIT;
        END IF;
    END LOOP;

    IF estado_cve IS NULL THEN
        RAISE EXCEPTION 'Código postal % no encontrado en ninguna entidad', codigo_postal_busqueda;
    END IF;

    -- Paso 2: Construir nombres de tablas
    tabla_ageb_urbana := 'ageb_urbana_' || estado_cve;
    tabla_ageb_rural := 'ageb_rural_' || estado_cve;

    -- Paso 3: Construir y ejecutar query dinámico
    query_dinamico := format($q$
        SELECT
            cp.d_cp::TEXT as codigo_postal,
            ageb.cvegeo::TEXT as clave_ageb,
            'urbana'::TEXT as tipo_ageb,
            ROUND((ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
            ST_Area(ST_Transform(cp.geom, 6372)) * 100)::numeric, 2) as porcentaje_interseccion
        FROM sepomex.%I cp
        JOIN inegi.%I ageb
          ON ST_Intersects(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))
        WHERE cp.d_cp = %L
          AND ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ST_Transform(ageb.geom, 6372))) /
              ST_Area(ST_Transform(cp.geom, 6372)) * 100 > 0.01

        UNION ALL

        SELECT
            cp.d_cp::TEXT,
            ageb.cvegeo::TEXT,
            'rural'::TEXT,
            ROUND((ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) /
            ST_Area(ST_Transform(cp.geom, 6372)) * 100)::numeric, 2)
        FROM sepomex.%I cp
        JOIN inegi.%I ageb
          ON ST_Intersects(ST_Transform(cp.geom, 6372), ageb.geom)
        WHERE cp.d_cp = %L
          AND ST_Area(ST_Intersection(ST_Transform(cp.geom, 6372), ageb.geom)) /
              ST_Area(ST_Transform(cp.geom, 6372)) * 100 > 0.01

        ORDER BY porcentaje_interseccion DESC
    $q$,
    tabla_cp, tabla_ageb_urbana, codigo_postal_busqueda,
    tabla_cp, tabla_ageb_rural, codigo_postal_busqueda);

    -- Retornar resultados
    RETURN QUERY EXECUTE query_dinamico;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Ejemplos de uso:
-- ============================================================================

-- Buscar AGEBs para un código postal en Guadalajara, Jalisco
SELECT * FROM buscar_agebs_por_cp('44100');

-- Buscar AGEBs para un código postal en CDMX
-- SELECT * FROM buscar_agebs_por_cp('06600');

-- Buscar AGEBs para cualquier código postal
-- SELECT * FROM buscar_agebs_por_cp('TU_CODIGO_POSTAL_AQUI');
