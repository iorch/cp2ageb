#!/bin/bash
# Wrapper script to search AGEBs by postal code
# Usage: ./buscar_cp.sh 44100

show_help() {
    cat << EOF
Uso: $0 <codigo_postal>

Busca los AGEBs (Áreas Geoestadísticas Básicas) que intersectan con un código postal.

ARGUMENTOS:
    codigo_postal    Código postal a buscar (5 dígitos)

OPCIONES:
    --help, -h       Muestra esta ayuda y sale

EJEMPLOS:
    $0 44100         # Buscar AGEBs en Guadalajara, Jalisco
    $0 11560         # Buscar AGEBs en Polanco, CDMX
    $0 50000         # Buscar AGEBs en Toluca, Edo México
    $0 64000         # Buscar AGEBs en Monterrey, Nuevo León

SALIDA:
    codigo_postal               Código postal buscado
    clave_ageb                  Clave del AGEB (formato INEGI)
    tipo_ageb                   'urbana' o 'rural'
    porcentaje_interseccion     % del CP que intersecta con el AGEB

NOTAS:
    - El sistema detecta automáticamente en qué estado está el CP
    - Solo muestra intersecciones significativas (>0.01%)
    - Requiere que el estado del CP esté cargado en la base de datos
    - Para verificar estados cargados, ejecuta:
      docker-compose exec postgis psql -U geouser -d cp2ageb -c "\dt sepomex.*"

EOF
    exit 0
}

# Procesar opciones
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

if [ -z "$1" ]; then
    echo "Error: Falta el código postal"
    echo ""
    echo "Uso: $0 <codigo_postal>"
    echo "Ejemplo: $0 44100"
    echo ""
    echo "Para más información, ejecuta: $0 --help"
    exit 1
fi

CP=$1

# Validar que sea numérico y tenga 5 dígitos
if ! [[ "$CP" =~ ^[0-9]{5}$ ]]; then
    echo "Error: El código postal debe ser numérico de 5 dígitos"
    echo "Recibido: '$CP'"
    echo ""
    echo "Ejemplos válidos: 44100, 11560, 50000, 64000"
    exit 1
fi

docker-compose exec postgis psql -U geouser -d cp2ageb -c "SELECT * FROM buscar_agebs_por_cp('${CP}');"
