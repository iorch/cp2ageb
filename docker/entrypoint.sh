#!/bin/bash
set -e

echo "========================================"
echo "  cp2ageb - PostGIS Container Startup"
echo "========================================"

# Variable de entorno para controlar el comportamiento automático
AUTO_DOWNLOAD=${AUTO_DOWNLOAD:-true}
AUTO_LOAD=${AUTO_LOAD:-true}

# Funciones auxiliares
wait_for_postgres() {
    echo "Esperando a que PostgreSQL esté listo..."
    until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; do
        echo "  PostgreSQL no está listo, esperando..."
        sleep 2
    done
    echo "✓ PostgreSQL está listo"
}

count_zip_files() {
    local dir=$1
    if [ -d "$dir" ]; then
        find "$dir" -name "*.zip" 2>/dev/null | wc -l
    else
        echo "0"
    fi
}

download_shapefiles() {
    echo ""
    echo "========================================"
    echo "  Descargando Shapefiles"
    echo "========================================"

    local cp_count=$(count_zip_files "/data/cp_shapefiles")
    local ageb_count=$(count_zip_files "/data/ageb_shapefiles")

    if [ "$cp_count" -lt 32 ]; then
        echo ""
        echo "→ Descargando shapefiles de SEPOMEX ($cp_count/32 presentes)..."
        python3 /app/download_shapefiles.py
    else
        echo "✓ Shapefiles de SEPOMEX ya presentes ($cp_count/32)"
    fi

    if [ "$ageb_count" -lt 32 ]; then
        echo ""
        echo "→ Descargando shapefiles de INEGI ($ageb_count/32 presentes)..."
        python3 /app/download_ageb_shapefiles.py
    else
        echo "✓ Shapefiles de INEGI ya presentes ($ageb_count/32)"
    fi
}

load_shapefiles() {
    echo ""
    echo "========================================"
    echo "  Cargando Shapefiles a PostGIS"
    echo "========================================"

    local sepomex_tables=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sepomex';" 2>/dev/null || echo "0")
    local inegi_tables=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='inegi';" 2>/dev/null || echo "0")

    if [ "$sepomex_tables" -gt 0 ] || [ "$inegi_tables" -gt 0 ]; then
        echo ""
        echo "⚠ Shapefiles ya cargados en la base de datos:"
        echo "  - SEPOMEX: $sepomex_tables tablas"
        echo "  - INEGI: $inegi_tables tablas"
        echo "✓ Omitiendo carga de shapefiles (ya existen datos)"
        return 0
    fi

    echo ""
    echo "→ Iniciando carga de shapefiles..."
    python3 /scripts/load_shapefiles.py

    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ Shapefiles cargados exitosamente"
    else
        echo ""
        echo "✗ Error al cargar shapefiles"
        return 1
    fi
}

create_functions() {
    echo ""
    echo "========================================"
    echo "  Creando Funciones SQL"
    echo "========================================"

    # Verificar si la función ya existe
    local function_exists=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM pg_proc WHERE proname='buscar_agebs_por_cp';" 2>/dev/null || echo "0")

    if [ "$function_exists" -gt 0 ]; then
        echo "✓ Función buscar_agebs_por_cp ya existe"
        return 0
    fi

    if [ -f /queries/cp_to_ageb_function.sql ]; then
        echo ""
        echo "→ Creando función buscar_agebs_por_cp..."
        psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /queries/cp_to_ageb_function.sql > /dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo "✓ Función buscar_agebs_por_cp creada exitosamente"
        else
            echo "✗ Error al crear función"
            return 1
        fi
    else
        echo "⚠ Archivo /queries/cp_to_ageb_function.sql no encontrado"
        return 0
    fi
}

show_summary() {
    echo ""
    echo "========================================"
    echo "  Sistema Listo - cp2ageb"
    echo "========================================"

    local sepomex_tables=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sepomex';" 2>/dev/null || echo "0")
    local inegi_tables=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='inegi';" 2>/dev/null || echo "0")
    local function_exists=$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT COUNT(*) FROM pg_proc WHERE proname='buscar_agebs_por_cp';" 2>/dev/null || echo "0")

    echo "Tablas cargadas:"
    echo "  - SEPOMEX: $sepomex_tables tablas"
    echo "  - INEGI: $inegi_tables tablas"

    if [ "$function_exists" -gt 0 ]; then
        echo "  - Función buscar_agebs_por_cp: ✓"
    fi

    echo ""
    echo "Base de datos: $POSTGRES_DB"
    echo "Usuario: $POSTGRES_USER"
    echo "Puerto: 5432"
    echo ""
    echo "Uso rápido:"
    echo "  ./buscar_cp.sh 44100"
    echo ""
    echo "Conectar a la base:"
    echo "  docker-compose exec postgis psql -U $POSTGRES_USER -d $POSTGRES_DB"
    echo ""
    echo "Buscar AGEBs de un CP:"
    echo "  docker-compose exec postgis psql -U $POSTGRES_USER -d $POSTGRES_DB \\"
    echo "    -c \"SELECT * FROM buscar_agebs_por_cp('44100');\""
    echo "========================================"
}

# MODO BENCHMARK: Si ambos están deshabilitados, solo iniciar postgres normalmente
if [ "$AUTO_DOWNLOAD" = "false" ] && [ "$AUTO_LOAD" = "false" ]; then
    echo "Modo benchmark detectado (AUTO_DOWNLOAD=false, AUTO_LOAD=false)"
    echo "Iniciando PostgreSQL en modo estándar..."
    echo ""
    echo "PostgreSQL estará disponible para conexiones externas"
    echo "Para cargar shapefiles manualmente ejecuta:"
    echo "  docker-compose exec postgis python3 /scripts/load_shapefiles.py"
    echo ""

    # Ejecutar postgres normalmente (reemplaza este proceso)
    exec docker-entrypoint.sh postgres
fi

# MODO AUTOMÁTICO: Esperar postgres, descargar y cargar
# Este modo se ejecuta en un subshell para no bloquear el inicio de postgres
(
    # Esperar a que postgres esté listo
    sleep 10  # Dar tiempo a que postgres inicie completamente
    wait_for_postgres

    # Descargar shapefiles si está habilitado
    if [ "$AUTO_DOWNLOAD" = "true" ]; then
        download_shapefiles
    fi

    # Cargar shapefiles si está habilitado
    if [ "$AUTO_LOAD" = "true" ]; then
        load_shapefiles
        create_functions
        show_summary
    fi

    echo ""
    echo "PostgreSQL está listo para conexiones"
    echo ""
) &

# Iniciar postgres en foreground
exec docker-entrypoint.sh postgres
