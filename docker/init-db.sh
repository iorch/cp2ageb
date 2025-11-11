#!/bin/bash
set -e

# Script de inicialización de la base de datos PostGIS
# Se ejecuta automáticamente cuando se crea el contenedor por primera vez

echo "===== Inicializando base de datos cp2ageb ====="

# Crear extensión PostGIS
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Habilitar extensión PostGIS
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS postgis_topology;

    -- Verificar versión de PostGIS
    SELECT PostGIS_version();

    -- Crear schema para datos de SEPOMEX
    CREATE SCHEMA IF NOT EXISTS sepomex;

    -- Crear schema para datos de INEGI
    CREATE SCHEMA IF NOT EXISTS inegi;

    -- Comentarios en los schemas
    COMMENT ON SCHEMA sepomex IS 'Datos de códigos postales de SEPOMEX';
    COMMENT ON SCHEMA inegi IS 'Datos del Marco Geoestadístico de INEGI';

    -- Crear tabla para metadatos de carga
    CREATE TABLE IF NOT EXISTS public.load_metadata (
        id SERIAL PRIMARY KEY,
        table_name VARCHAR(100) NOT NULL,
        source VARCHAR(50) NOT NULL,
        file_name VARCHAR(255),
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        rows_count INTEGER,
        status VARCHAR(20) DEFAULT 'success'
    );

    COMMENT ON TABLE public.load_metadata IS 'Metadatos de las cargas de shapefiles';

    -- Agregar SRIDs personalizados (ESRI Web Mercator)
    -- SRID 900914: ESRI:102100 - Web Mercator usado por SEPOMEX
    INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext)
    VALUES (900914, 'ESRI', 102100,
        '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs',
        'PROJCS["WGS_1984_Web_Mercator",GEOGCS["GCS_WGS_1984_Major_Auxiliary_Sphere",DATUM["D_WGS_1984_Major_Auxiliary_Sphere",SPHEROID["WGS_1984_Major_Auxiliary_Sphere",6378137.0,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Mercator"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],PARAMETER["Standard_Parallel_1",0.0],UNIT["Meter",1.0]]')
    ON CONFLICT (srid) DO NOTHING;

    -- SRID 900916: Variante de Web Mercator usado por INEGI
    INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext)
    VALUES (900916, 'ESRI', 102100,
        '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs',
        'PROJCS["WGS_1984_Web_Mercator",GEOGCS["GCS_WGS_1984_Major_Auxiliary_Sphere",DATUM["D_WGS_1984_Major_Auxiliary_Sphere",SPHEROID["WGS_1984_Major_Auxiliary_Sphere",6378137.0,0.0]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Mercator"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",0.0],PARAMETER["Standard_Parallel_1",0.0],UNIT["Meter",1.0]]')
    ON CONFLICT (srid) DO NOTHING;
EOSQL

echo "✓ Base de datos inicializada correctamente"
echo "✓ Extensión PostGIS habilitada"
echo "✓ Schemas creados: sepomex, inegi"
echo "✓ SRIDs personalizados agregados: 900914, 900916"
echo ""
echo "Para cargar los shapefiles, ejecuta:"
echo "  docker exec -it cp2ageb-postgis bash"
echo "  python3 /scripts/load_shapefiles.py"
