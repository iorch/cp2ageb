#!/bin/bash
set -e

show_help() {
    cat << EOF
Uso: $0 [opciones]

Script de benchmark para medir tiempos de construcción y carga de cp2ageb.

OPCIONES:
    --full          Carga completa de 32 estados
                    (por defecto: solo Aguascalientes)

    --no-cache      Reconstruir imagen Docker sin usar cache

    --clean         Limpiar todo y empezar desde cero
                    (elimina volumen de datos y estado previo)

    --resume        Continuar desde donde se quedó (por defecto)
                    El sistema guarda el progreso automáticamente

    --help, -h      Muestra esta ayuda y sale

EJEMPLOS:
    $0                      # Benchmark rápido (solo Aguascalientes, continuar si hay progreso)
    $0 --full               # Benchmark completo (32 estados, continuar si hay progreso)
    $0 --clean --full       # Benchmark completo desde cero
    $0 --no-cache           # Reconstruir imagen y ejecutar benchmark
    $0 --resume --full      # Explícitamente continuar un benchmark completo

FUNCIONAMIENTO:
    El script mide y registra el tiempo de:
    1. Construcción de imagen Docker
    2. Inicio del contenedor y PostgreSQL
    3. Descarga de shapefiles
    4. Carga de shapefiles a PostGIS

    Los tiempos se guardan en:
    - benchmark_results_YYYYMMDD_HHMMSS.txt
    - .benchmark_state (estado de progreso)

    Si el proceso se interrumpe, puede continuar con el mismo comando.
    Los tiempos se acumulan de todas las sesiones necesarias.

NOTAS:
    - El modo --resume es el comportamiento por defecto
    - Usar --clean para empezar de cero elimina:
      * Volumen de datos de PostgreSQL
      * Archivo de estado (.benchmark_state)
    - Los shapefiles descargados NO se eliminan con --clean
    - Tiempo estimado completo (--full): 8-10 horas

EOF
    exit 0
}

FULL_LOAD=false
NO_CACHE=""
CLEAN=false
STATE_FILE=".benchmark_state"
BENCHMARK_FILE="benchmark_results_$(date +%Y%m%d_%H%M%S).txt"

# Procesar argumentos
for arg in "$@"; do
    case $arg in
        --help|-h)
            show_help
            ;;
        --full)
            FULL_LOAD=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        --resume)
            # Por defecto, no hace nada extra
            shift
            ;;
        *)
            echo "Error: Opción desconocida '$arg'"
            echo ""
            echo "Para ver opciones disponibles: $0 --help"
            exit 1
            ;;
    esac
done

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para formatear tiempo
format_time() {
    local seconds=$1
    local minutes=$((seconds / 60))
    local secs=$((seconds % 60))
    echo "${minutes}m ${secs}s"
}

# Función para cargar estado previo
load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        ACCUMULATED_BUILD_TIME=${ACCUMULATED_BUILD_TIME:-0}
        ACCUMULATED_STARTUP_TIME=${ACCUMULATED_STARTUP_TIME:-0}
        ACCUMULATED_DOWNLOAD_TIME=${ACCUMULATED_DOWNLOAD_TIME:-0}
        ACCUMULATED_LOAD_TIME=${ACCUMULATED_LOAD_TIME:-0}
        COMPLETED_BUILD=${COMPLETED_BUILD:-false}
        COMPLETED_STARTUP=${COMPLETED_STARTUP:-false}
        COMPLETED_DOWNLOAD=${COMPLETED_DOWNLOAD:-false}
        COMPLETED_LOAD=${COMPLETED_LOAD:-false}
    else
        ACCUMULATED_BUILD_TIME=0
        ACCUMULATED_STARTUP_TIME=0
        ACCUMULATED_DOWNLOAD_TIME=0
        ACCUMULATED_LOAD_TIME=0
        COMPLETED_BUILD=false
        COMPLETED_STARTUP=false
        COMPLETED_DOWNLOAD=false
        COMPLETED_LOAD=false
    fi
}

# Función para guardar estado
save_state() {
    cat > "$STATE_FILE" <<EOF
ACCUMULATED_BUILD_TIME=$ACCUMULATED_BUILD_TIME
ACCUMULATED_STARTUP_TIME=$ACCUMULATED_STARTUP_TIME
ACCUMULATED_DOWNLOAD_TIME=$ACCUMULATED_DOWNLOAD_TIME
ACCUMULATED_LOAD_TIME=$ACCUMULATED_LOAD_TIME
COMPLETED_BUILD=$COMPLETED_BUILD
COMPLETED_STARTUP=$COMPLETED_STARTUP
COMPLETED_DOWNLOAD=$COMPLETED_DOWNLOAD
COMPLETED_LOAD=$COMPLETED_LOAD
EOF
}

# Limpiar estado si --clean
if $CLEAN && [ -f "$STATE_FILE" ]; then
    rm -f "$STATE_FILE"
fi

# Cargar estado previo
load_state

echo "========================================"
echo "  cp2ageb - Benchmark"
echo "========================================"
echo ""
echo "Modo: $(if $FULL_LOAD; then echo 'Carga completa (32 estados)'; else echo 'Carga rápida (Aguascalientes)'; fi)"
if $CLEAN; then
    echo "Limpieza: Habilitada (empezar desde cero)"
else
    echo "Limpieza: Deshabilitada (continuar donde se quedó)"
    if [ -f "$STATE_FILE" ]; then
        echo "Estado previo: Encontrado"
        echo "  - Build: $(if $COMPLETED_BUILD; then echo 'completado'; else echo 'pendiente'; fi) ($(format_time $ACCUMULATED_BUILD_TIME))"
        echo "  - Startup: $(if $COMPLETED_STARTUP; then echo 'completado'; else echo 'pendiente'; fi) ($(format_time $ACCUMULATED_STARTUP_TIME))"
        echo "  - Download: $(if $COMPLETED_DOWNLOAD; then echo 'completado'; else echo 'pendiente'; fi) ($(format_time $ACCUMULATED_DOWNLOAD_TIME))"
        echo "  - Load: $(if $COMPLETED_LOAD; then echo 'completado'; else echo 'pendiente'; fi) ($(format_time $ACCUMULATED_LOAD_TIME))"
    fi
fi
echo "Resultados: $BENCHMARK_FILE"
echo ""

# Iniciar reporte
cat > "$BENCHMARK_FILE" <<EOF
======================================
cp2ageb - Benchmark Results
======================================
Fecha: $(date)
Modo: $(if $FULL_LOAD; then echo 'Carga completa (32 estados)'; else echo 'Carga rápida (Aguascalientes)'; fi)
Limpieza: $(if $CLEAN; then echo 'Habilitada'; else echo 'Deshabilitada (resume)'; fi)

EOF

# Variables para tracking de etapas
SKIP_BUILD=false
SKIP_STARTUP=false
SKIP_DOWNLOAD=false
SKIP_LOAD=false

# Detectar estado actual (solo si no estamos empezando desde cero)
if ! $CLEAN; then
    echo -e "${BLUE}Detectando estado actual...${NC}"

    # Usar flags del estado guardado
    SKIP_BUILD=$COMPLETED_BUILD
    SKIP_STARTUP=$COMPLETED_STARTUP
    SKIP_DOWNLOAD=$COMPLETED_DOWNLOAD
    SKIP_LOAD=$COMPLETED_LOAD

    # Verificar contenedor si aún no está marcado como completado
    if ! $COMPLETED_STARTUP; then
        if docker-compose ps | grep -q "cp2ageb-postgis.*Up"; then
            echo "  ✓ Contenedor ya está corriendo"
            SKIP_STARTUP=true
        fi
    fi

    # Verificar datos cargados si aún no está marcado como completado
    if ! $COMPLETED_LOAD; then
        if docker-compose exec -T postgis pg_isready -U geouser -d cp2ageb > /dev/null 2>&1; then
            SEPOMEX_TABLES=$(docker-compose exec -T postgis psql -U geouser -d cp2ageb -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sepomex';" 2>/dev/null || echo "0")
            INEGI_TABLES=$(docker-compose exec -T postgis psql -U geouser -d cp2ageb -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='inegi';" 2>/dev/null || echo "0")

            if [ "$SEPOMEX_TABLES" -gt 0 ] || [ "$INEGI_TABLES" -gt 0 ]; then
                echo "  ✓ Datos ya cargados (SEPOMEX: $SEPOMEX_TABLES tablas, INEGI: $INEGI_TABLES tablas)"
                SKIP_LOAD=true
            fi
        fi
    fi

    # Verificar shapefiles si aún no están marcados como completados
    if ! $COMPLETED_DOWNLOAD; then
        if [ -d "data/cp_shapefiles" ] && [ -d "data/ageb_shapefiles" ]; then
            CP_COUNT=$(find data/cp_shapefiles -name "*.zip" 2>/dev/null | wc -l)
            AGEB_COUNT=$(find data/ageb_shapefiles -name "*.zip" 2>/dev/null | wc -l)

            if $FULL_LOAD; then
                if [ "$CP_COUNT" -eq 32 ] && [ "$AGEB_COUNT" -eq 32 ]; then
                    echo "  ✓ Shapefiles ya descargados (32/32 estados)"
                    SKIP_DOWNLOAD=true
                fi
            else
                if [ -f "data/cp_shapefiles/CP_Ags.zip" ] && [ -f "data/ageb_shapefiles/01_aguascalientes.zip" ]; then
                    echo "  ✓ Shapefiles de Aguascalientes ya descargados"
                    SKIP_DOWNLOAD=true
                fi
            fi
        fi
    fi

    echo ""
else
    # Si --clean, empezar todo de nuevo
    SKIP_BUILD=false
    SKIP_STARTUP=false
    SKIP_DOWNLOAD=false
    SKIP_LOAD=false
fi

# 1. Limpiar entorno anterior (solo si --clean)
if $CLEAN; then
    echo -e "${BLUE}[1/6]${NC} Limpiando entorno anterior..."
    docker-compose down -v > /dev/null 2>&1 || true
    echo "✓ Entorno limpio"
    echo ""
    SKIP_BUILD=false
    SKIP_STARTUP=false
    SKIP_DOWNLOAD=false
    SKIP_LOAD=false
else
    echo -e "${BLUE}[1/6]${NC} Saltando limpieza (modo resume)"
    echo ""
fi

# 2. Construcción de imagen Docker
if $SKIP_BUILD; then
    echo -e "${BLUE}[2/6]${NC} Saltando construcción (ya completada previamente: $(format_time $ACCUMULATED_BUILD_TIME))"
    BUILD_TIME=0
    echo ""
else
    echo -e "${BLUE}[2/6]${NC} Construyendo imagen Docker..."
    START_BUILD=$(date +%s)
    docker-compose build $NO_CACHE
    END_BUILD=$(date +%s)
    BUILD_TIME=$((END_BUILD - START_BUILD))
    ACCUMULATED_BUILD_TIME=$((ACCUMULATED_BUILD_TIME + BUILD_TIME))
    COMPLETED_BUILD=true
    save_state
    echo -e "${GREEN}✓ Construcción completada en $(format_time $BUILD_TIME) (acumulado: $(format_time $ACCUMULATED_BUILD_TIME))${NC}"
    echo ""
fi

# 3. Iniciar contenedor (con AUTO_LOAD=false para medir manualmente)
if $SKIP_STARTUP; then
    echo -e "${BLUE}[3/6]${NC} Saltando inicio (ya completado previamente: $(format_time $ACCUMULATED_STARTUP_TIME))"
    STARTUP_TIME=0
    echo ""
else
    echo -e "${BLUE}[3/6]${NC} Iniciando contenedor..."
    START_STARTUP=$(date +%s)
    AUTO_DOWNLOAD=false AUTO_LOAD=false docker-compose up -d

    # Esperar a que PostgreSQL esté listo
    echo "  Esperando PostgreSQL..."
    RETRY_COUNT=0
    MAX_RETRIES=60
    until docker-compose exec -T postgis pg_isready -U geouser -d cp2ageb > /dev/null 2>&1; do
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo -e "${YELLOW}⚠ PostgreSQL tardó más de lo esperado${NC}"
            echo "Ver logs: docker-compose logs postgis"
            exit 1
        fi
    done

    # Verificar que la base de datos acepta conexiones (no solo que el servidor esté up)
    echo "  Verificando que la base de datos acepta conexiones..."
    RETRY_COUNT=0
    until docker-compose exec -T postgis psql -U geouser -d cp2ageb -c "SELECT 1;" > /dev/null 2>&1; do
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo -e "${YELLOW}⚠ Base de datos no acepta conexiones${NC}"
            echo "Ver logs: docker-compose logs postgis"
            exit 1
        fi
    done

    # Esperar a que los scripts de inicialización terminen (verificar que schemas existan)
    echo "  Esperando finalización de scripts de inicialización..."
    RETRY_COUNT=0
    until docker-compose exec -T postgis psql -U geouser -d cp2ageb -c "SELECT 1 FROM information_schema.schemata WHERE schema_name='sepomex';" 2>/dev/null | grep -q "1"; do
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo -e "${YELLOW}⚠ Scripts de inicialización no completaron${NC}"
            echo "Ver logs: docker-compose logs postgis"
            exit 1
        fi
    done

    # Esperar más tiempo para asegurar estabilidad después del reinicio de PostgreSQL
    echo "  Esperando estabilización después del reinicio..."
    sleep 15

    # Verificar nuevamente que acepta conexiones después del reinicio
    RETRY_COUNT=0
    until docker-compose exec -T postgis psql -U geouser -d cp2ageb -c "SELECT 1;" > /dev/null 2>&1; do
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge 30 ]; then
            echo -e "${YELLOW}⚠ Base de datos no responde después del reinicio${NC}"
            exit 1
        fi
    done

    echo "  PostgreSQL completamente listo"

    END_STARTUP=$(date +%s)
    STARTUP_TIME=$((END_STARTUP - START_STARTUP))
    ACCUMULATED_STARTUP_TIME=$((ACCUMULATED_STARTUP_TIME + STARTUP_TIME))
    COMPLETED_STARTUP=true
    save_state
    echo -e "${GREEN}✓ Contenedor y PostgreSQL listos en $(format_time $STARTUP_TIME) (acumulado: $(format_time $ACCUMULATED_STARTUP_TIME))${NC}"
    echo ""
fi

# 4. Descarga de shapefiles
if $SKIP_DOWNLOAD; then
    echo -e "${BLUE}[5/6]${NC} Saltando descarga (ya completada previamente: $(format_time $ACCUMULATED_DOWNLOAD_TIME))"
    DOWNLOAD_TIME=0
    echo ""
else
    echo -e "${BLUE}[5/6]${NC} Descargando shapefiles..."
    START_DOWNLOAD=$(date +%s)

    if $FULL_LOAD; then
        # Descargar todos
        docker-compose exec -T postgis python3 /app/download_shapefiles.py
        docker-compose exec -T postgis python3 /app/download_ageb_shapefiles.py
    else
        # Solo verificar que existan los de Aguascalientes
        if [ ! -f "data/cp_shapefiles/CP_Ags.zip" ]; then
            docker-compose exec -T postgis python3 /app/download_shapefiles.py
        fi
        if [ ! -f "data/ageb_shapefiles/01_aguascalientes.zip" ]; then
            docker-compose exec -T postgis python3 /app/download_ageb_shapefiles.py
        fi
    fi

    END_DOWNLOAD=$(date +%s)
    DOWNLOAD_TIME=$((END_DOWNLOAD - START_DOWNLOAD))
    ACCUMULATED_DOWNLOAD_TIME=$((ACCUMULATED_DOWNLOAD_TIME + DOWNLOAD_TIME))
    COMPLETED_DOWNLOAD=true
    save_state
    echo -e "${GREEN}✓ Descarga completada en $(format_time $DOWNLOAD_TIME) (acumulado: $(format_time $ACCUMULATED_DOWNLOAD_TIME))${NC}"
    echo ""
fi

# 5. Carga de shapefiles a PostGIS
if $SKIP_LOAD; then
    echo -e "${BLUE}[6/6]${NC} Saltando carga (ya completada previamente: $(format_time $ACCUMULATED_LOAD_TIME))"
    LOAD_TIME=0
    echo ""
else
    echo -e "${BLUE}[6/6]${NC} Cargando shapefiles a PostGIS..."
    START_LOAD=$(date +%s)

    if $FULL_LOAD; then
        docker-compose exec -T postgis python3 /scripts/load_shapefiles.py | tee -a "$BENCHMARK_FILE.load.log"
    else
        docker-compose exec -T postgis python3 /scripts/load_single_state.py | tee -a "$BENCHMARK_FILE.load.log"
    fi

    END_LOAD=$(date +%s)
    LOAD_TIME=$((END_LOAD - START_LOAD))
    ACCUMULATED_LOAD_TIME=$((ACCUMULATED_LOAD_TIME + LOAD_TIME))
    COMPLETED_LOAD=true
    save_state
    echo -e "${GREEN}✓ Carga completada en $(format_time $LOAD_TIME) (acumulado: $(format_time $ACCUMULATED_LOAD_TIME))${NC}"
    echo ""
fi

# Calcular tiempo total (usar tiempos acumulados)
TOTAL_TIME=$((ACCUMULATED_BUILD_TIME + ACCUMULATED_STARTUP_TIME + ACCUMULATED_DOWNLOAD_TIME + ACCUMULATED_LOAD_TIME))

# Generar reporte final
cat >> "$BENCHMARK_FILE" <<EOF

======================================
RESUMEN (Tiempos Acumulados)
======================================
Construcción Docker:  $(format_time $ACCUMULATED_BUILD_TIME)
Inicio contenedor:    $(format_time $ACCUMULATED_STARTUP_TIME)
Descarga shapefiles:  $(format_time $ACCUMULATED_DOWNLOAD_TIME)
Carga a PostGIS:      $(format_time $ACCUMULATED_LOAD_TIME)
--------------------------------------
TIEMPO TOTAL:         $(format_time $TOTAL_TIME)
======================================

Nota: Los tiempos son acumulados de todas las sesiones
necesarias para completar el benchmark.

EOF

# Obtener estadísticas de la base de datos
echo -e "${YELLOW}Obteniendo estadísticas...${NC}"
docker-compose exec -T postgis psql -U geouser -d cp2ageb -c "
SELECT
    'SEPOMEX' as schema,
    COUNT(*) as tablas
FROM information_schema.tables
WHERE table_schema='sepomex'
UNION ALL
SELECT
    'INEGI' as schema,
    COUNT(*) as tablas
FROM information_schema.tables
WHERE table_schema='inegi';
" >> "$BENCHMARK_FILE"

echo ""
echo "========================================"
echo -e "${GREEN}BENCHMARK COMPLETADO${NC}"
echo "========================================"
echo ""
echo "Tiempos Acumulados (todas las sesiones):"
echo "----------------------------------------"
echo "Construcción Docker:  $(format_time $ACCUMULATED_BUILD_TIME)"
echo "Inicio contenedor:    $(format_time $ACCUMULATED_STARTUP_TIME)"
echo "Descarga shapefiles:  $(format_time $ACCUMULATED_DOWNLOAD_TIME)"
echo "Carga a PostGIS:      $(format_time $ACCUMULATED_LOAD_TIME)"
echo "--------------------------------------"
echo -e "${GREEN}TIEMPO TOTAL:         $(format_time $TOTAL_TIME)${NC}"
echo "========================================"
echo ""
echo "Resultados guardados en: $BENCHMARK_FILE"
if [ -f "$BENCHMARK_FILE.load.log" ]; then
    echo "Log de carga: $BENCHMARK_FILE.load.log"
fi
echo "Estado guardado en: $STATE_FILE"
echo ""
echo "Para reiniciar desde cero: ./benchmark.sh --clean"
echo ""
