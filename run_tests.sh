#!/bin/bash
# Script para ejecutar tests de cp2ageb

show_help() {
    cat << EOF
Uso: $0 [opciones]

Ejecuta la suite de tests para cp2ageb.

OPCIONES:
    --all               Ejecutar todos los tests (default)
    --unit              Solo tests unitarios (no requieren base de datos)
    --integration       Solo tests de integración (requieren base de datos)
    --database          Solo tests de base de datos
    --slow              Incluir tests lentos
    --no-slow           Excluir tests lentos (default)
    --coverage          Generar reporte de coverage
    --parallel          Ejecutar tests en paralelo
    --verbose, -v       Output verboso
    --help, -h          Mostrar esta ayuda

EJEMPLOS:
    $0                          # Todos los tests (sin lentos)
    $0 --unit                   # Solo tests unitarios
    $0 --integration            # Solo tests de integración
    $0 --all --slow             # Todos incluyendo lentos
    $0 --coverage               # Con reporte de coverage
    $0 --parallel --no-slow     # En paralelo, sin lentos

REQUISITOS:
    - pytest instalado (pip install -r requirements-test.txt)
    - Para tests de integración: contenedor Docker corriendo
      (docker-compose up -d)

MARKERS DISPONIBLES:
    unit            Tests unitarios
    integration     Tests de integración
    database        Tests de base de datos
    slow            Tests lentos

EOF
    exit 0
}

# Defaults
RUN_MODE="all"
INCLUDE_SLOW=false
COVERAGE=false
PARALLEL=false
VERBOSE=""

# Procesar argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            ;;
        --all)
            RUN_MODE="all"
            shift
            ;;
        --unit)
            RUN_MODE="unit"
            shift
            ;;
        --integration)
            RUN_MODE="integration"
            shift
            ;;
        --database)
            RUN_MODE="database"
            shift
            ;;
        --slow)
            INCLUDE_SLOW=true
            shift
            ;;
        --no-slow)
            INCLUDE_SLOW=false
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --verbose|-v)
            VERBOSE="-vv"
            shift
            ;;
        *)
            echo "Error: Opción desconocida '$1'"
            echo ""
            echo "Para ver opciones disponibles: $0 --help"
            exit 1
            ;;
    esac
done

# Verificar que pytest está instalado
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest no está instalado"
    echo ""
    echo "Instalar con:"
    echo "  pip install -r requirements-test.txt"
    exit 1
fi

# Construir comando pytest
PYTEST_CMD="pytest"

# Agregar verbose si se especificó
if [ -n "$VERBOSE" ]; then
    PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

# Agregar coverage si se especificó
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=html --cov-report=term"
fi

# Agregar paralelización si se especificó
if [ "$PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

# Agregar markers según el modo
case $RUN_MODE in
    unit)
        PYTEST_CMD="$PYTEST_CMD -m unit"
        ;;
    integration)
        PYTEST_CMD="$PYTEST_CMD -m integration"
        ;;
    database)
        PYTEST_CMD="$PYTEST_CMD -m database"
        ;;
    all)
        # No agregar marker, ejecutar todos
        ;;
esac

# Manejar tests lentos
if [ "$INCLUDE_SLOW" = false ]; then
    PYTEST_CMD="$PYTEST_CMD -m 'not slow'"
fi

# Imprimir información
echo "========================================"
echo "  cp2ageb - Test Runner"
echo "========================================"
echo ""
echo "Modo: $RUN_MODE"
echo "Tests lentos: $(if $INCLUDE_SLOW; then echo 'incluidos'; else echo 'excluidos'; fi)"
echo "Coverage: $(if $COVERAGE; then echo 'habilitado'; else echo 'deshabilitado'; fi)"
echo "Paralelo: $(if $PARALLEL; then echo 'habilitado'; else echo 'deshabilitado'; fi)"
echo ""

# Verificar base de datos si es necesario
if [[ "$RUN_MODE" == "integration" || "$RUN_MODE" == "database" || "$RUN_MODE" == "all" ]]; then
    echo "Verificando conexión a base de datos..."
    if docker-compose ps | grep -q "cp2ageb-postgis.*Up"; then
        echo "✓ Contenedor PostgreSQL corriendo"
    else
        echo "⚠ Advertencia: Contenedor PostgreSQL no está corriendo"
        echo "  Algunos tests pueden fallar o ser omitidos"
        echo ""
        echo "  Para iniciar el contenedor:"
        echo "    docker-compose up -d"
        echo ""
    fi
fi

echo "Ejecutando: $PYTEST_CMD"
echo "========================================"
echo ""

# Ejecutar pytest
eval $PYTEST_CMD
EXIT_CODE=$?

# Mostrar resultado
echo ""
echo "========================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Tests completados exitosamente"
else
    echo "✗ Algunos tests fallaron"
fi
echo "========================================"

# Mostrar info de coverage si se generó
if [ "$COVERAGE" = true ]; then
    echo ""
    echo "Reporte de coverage generado en: htmlcov/index.html"
    echo "Abrir con: open htmlcov/index.html  (o tu navegador)"
fi

exit $EXIT_CODE
