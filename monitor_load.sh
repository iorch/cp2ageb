#!/bin/bash
# Script para monitorear la carga de shapefiles

echo "=========================================="
echo "  Monitor de Carga - cp2ageb"
echo "=========================================="
echo ""

# Verificar si el proceso de carga está corriendo
if pgrep -f "load_shapefiles.py" > /dev/null; then
    echo "✓ Proceso de carga activo"
else
    echo "⚠ Proceso de carga no detectado"
fi

echo ""
echo "Progreso en base de datos:"
docker-compose exec -T postgis psql -U geouser -d cp2ageb -c "
SELECT
    'SEPOMEX' as fuente,
    COUNT(*) as tablas
FROM information_schema.tables
WHERE table_schema='sepomex'
UNION ALL
SELECT
    'INEGI' as fuente,
    COUNT(*) as tablas
FROM information_schema.tables
WHERE table_schema='inegi';
"

echo ""
echo "Últimas 30 líneas del log:"
echo "=========================================="
tail -30 load_full.log

echo ""
echo "=========================================="
echo "Comandos útiles:"
echo "  ./monitor_load.sh          - Ver este resumen"
echo "  tail -f load_full.log      - Ver log en tiempo real"
echo "  docker-compose logs -f     - Ver logs del contenedor"
echo "=========================================="
