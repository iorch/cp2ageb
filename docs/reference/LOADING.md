# Proceso de Carga Automática

Documentación del proceso de descarga y carga automática de datos al iniciar el contenedor.

## Flujo de Inicialización

Cuando ejecutas `docker-compose up -d`, el sistema sigue este flujo:

```
1. Inicialización de PostgreSQL
   ├─ Crear extensión PostGIS
   ├─ Crear schemas (sepomex, inegi)
   ├─ Crear tabla de metadatos
   └─ Registrar SRIDs personalizados

2. Descarga de Shapefiles (si AUTO_DOWNLOAD=true)
   ├─ Verificar archivos existentes
   ├─ Descargar SEPOMEX (si faltan)
   └─ Descargar INEGI (si faltan)

3. Carga a PostGIS (si AUTO_LOAD=true)
   ├─ Cargar shapefiles de SEPOMEX
   ├─ Cargar shapefiles de INEGI
   └─ Registrar metadatos en load_metadata

4. Crear Funciones SQL
   └─ Crear función buscar_agebs_por_cp()

5. Sistema Listo
   └─ Mostrar resumen y comandos de uso
```

## Scripts Involucrados

### 1. `docker/init-db.sh`
**Ejecutado por**: PostgreSQL durante primer arranque
**Propósito**: Inicializar base de datos

- Crea extensión PostGIS
- Crea schemas `sepomex` e `inegi`
- Crea tabla `public.load_metadata`
- Registra SRIDs personalizados (900914, 900916)

### 2. `docker/entrypoint.sh`
**Ejecutado por**: Docker al iniciar contenedor
**Propósito**: Orquestar descarga y carga

Funciones principales:
- `wait_for_postgres()`: Espera a que PostgreSQL esté listo
- `download_shapefiles()`: Descarga archivos ZIP si no existen
- `load_shapefiles()`: Llama al script de Python para cargar datos
- `create_functions()`: Crea la función `buscar_agebs_por_cp()`
- `show_summary()`: Muestra resumen y comandos de uso

### 3. `scripts/load_shapefiles.py`
**Ejecutado por**: entrypoint.sh
**Propósito**: Cargar shapefiles a PostGIS

- Lee variables de entorno (LOAD_ESTADOS, LOAD_AGEBS, etc.)
- Normaliza nombres de estados (acepta códigos, abreviaturas, nombres)
- Usa `shp2pgsql` y `psql` para importar geometrías
- Registra metadatos en `load_metadata`

### 4. `queries/cp_to_ageb_function.sql`
**Ejecutado por**: entrypoint.sh
**Propósito**: Crear función de búsqueda

- Define la función `buscar_agebs_por_cp(codigo_postal TEXT)`
- Implementa detección automática del estado
- Ejecuta query espacial dinámico

## Variables de Entorno

### Control de Automatización

```yaml
AUTO_DOWNLOAD: "true"   # Descarga automática de shapefiles
AUTO_LOAD: "true"        # Carga automática a PostGIS
```

- `true/true`: Modo automático completo (por defecto)
- `false/false`: Modo manual (benchmark)
- `true/false`: Solo descarga, sin cargar
- `false/true`: Asume archivos ya descargados

### Control de Capas INEGI

```yaml
LOAD_AGEBS: "true"       # AGEBs urbanas y rurales
LOAD_MANZANAS: "false"   # Manzanas (bloques urbanos)
LOAD_LOCALIDADES: "false"
LOAD_MUNICIPIOS: "false"
LOAD_ENTIDADES: "false"
```

**Impacto en tiempo de carga:**
- Solo AGEBs: ~8-10 horas (32 estados)
- AGEBs + Manzanas: ~12-15 horas
- Todas las capas: ~20-25 horas

### Control de Estados

```yaml
LOAD_ESTADOS: "14,15,09,19"  # Default: Jal, Edo Mex, CDMX, NL
```

Formatos válidos:
- `"14,15,09,19"` - Default (Jalisco, Edo Mex, CDMX, Nuevo León)
- `"all"` - Todos los 32 estados
- `"14"` - Solo estado 14 (Jalisco)
- `"Jal,CDMX,BC"` - Por abreviatura
- `"Jalisco,Ciudad de México"` - Por nombre completo

**Tiempo estimado por configuración:**
- 1 estado (solo AGEBs): ~15-30 minutos
- 4 estados (default): ~1-2 horas
- 10 estados: ~3-4 horas
- 32 estados: ~8-10 horas

## Detección de Carga Existente

El sistema verifica antes de cargar:

```bash
# Contar tablas existentes
sepomex_tables=$(psql ... "SELECT COUNT(*) FROM information_schema.tables
                            WHERE table_schema='sepomex';")

# Si ya existen tablas, omitir carga
if [ "$sepomex_tables" -gt 0 ]; then
    echo "✓ Omitiendo carga (ya existen datos)"
fi
```

Esto permite:
- Reiniciar el contenedor sin recargar datos
- Datos persisten en volumen Docker `pgdata`
- Solo se recarga si el volumen se elimina (`docker-compose down -v`)

## Monitoreo del Progreso

```bash
# Ver logs en tiempo real
docker-compose logs -f postgis

# Buscar mensajes clave:
# "Esperando a que PostgreSQL esté listo..."
# "→ Descargando shapefiles..."
# "→ Iniciando carga de shapefiles..."
# "✓ Shapefiles cargados exitosamente"
# "→ Creando función buscar_agebs_por_cp..."
# "Sistema Listo - cp2ageb"
```

## Verificar Estado de Carga

```sql
-- Ver tablas cargadas
\dt sepomex.*
\dt inegi.*

-- Ver metadatos de carga
SELECT * FROM public.load_metadata ORDER BY loaded_at DESC;

-- Contar registros
SELECT 'sepomex', COUNT(*) FROM (
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'sepomex'
) t;

-- Verificar función
\df buscar_agebs_por_cp
```

## Troubleshooting

### Problema: Carga se quedó a la mitad

**Causa**: Error durante carga o contenedor reiniciado

**Solución**:
```bash
# Ver estado de tablas
docker-compose exec postgis psql -U geouser -d cp2ageb \
  -c "SELECT * FROM load_metadata ORDER BY loaded_at DESC LIMIT 20;"

# Limpiar y recargar
docker-compose down -v
docker-compose up -d
```

### Problema: "Función buscar_agebs_por_cp no existe"

**Causa**: Función no se creó o se eliminó

**Solución**:
```bash
docker-compose exec postgis psql -U geouser -d cp2ageb \
  -f /queries/cp_to_ageb_function.sql
```

### Problema: Muy lento, solo necesito algunos estados

**Solución**: Editar `docker-compose.yml`:
```yaml
environment:
  LOAD_ESTADOS: "14,09"  # Solo Jalisco y CDMX
```

### Problema: No encuentra código postal

**Causa**: El estado del CP no fue cargado

**Verificar**:
```sql
-- Ver qué estados están cargados
SELECT DISTINCT table_name FROM information_schema.tables
WHERE table_schema = 'sepomex' ORDER BY table_name;
```

**Solución**: Agregar el estado faltante a `LOAD_ESTADOS` y recargar:
```bash
docker-compose down -v
docker-compose up -d
```

## Modo Benchmark

Para hacer pruebas de rendimiento sin carga automática:

```yaml
environment:
  AUTO_DOWNLOAD: "false"
  AUTO_LOAD: "false"
```

Luego cargar manualmente:
```bash
# Cargar shapefiles con control fino
docker-compose exec postgis python3 /scripts/load_shapefiles.py

# Medir tiempos con benchmark
./benchmark.sh --full
```

## Persistencia de Datos

Los datos se almacenan en volumen Docker:

```yaml
volumes:
  pgdata:
    driver: local
```

**Datos se mantienen al:**
- `docker-compose down` (solo detiene contenedor)
- `docker-compose restart`
- Reiniciar el host

**Datos se eliminan con:**
- `docker-compose down -v` (elimina volúmenes)
- `docker volume rm cp2ageb_pgdata`

## Estructura de Directorios

```
cp2ageb/
├── data/
│   ├── cp_shapefiles/       # Shapefiles SEPOMEX (descargados)
│   └── ageb_shapefiles/     # Shapefiles INEGI (descargados)
├── docker/
│   ├── entrypoint.sh        # Script principal de inicialización
│   └── init-db.sh           # Script de PostgreSQL init
├── scripts/
│   └── load_shapefiles.py   # Script de carga Python
├── queries/
│   ├── cp_to_ageb.sql                # Queries de ejemplo
│   ├── cp_to_ageb_dynamic.sql        # Query dinámico
│   └── cp_to_ageb_function.sql       # Definición de función
├── download_shapefiles.py            # Descarga SEPOMEX
├── download_ageb_shapefiles.py       # Descarga INEGI
└── buscar_cp.sh                      # Wrapper simple
```

## Próximos Pasos

Una vez que el sistema esté listo:

1. Probar búsqueda: `./buscar_cp.sh 44100`
2. Explorar queries: `queries/cp_to_ageb.sql`
3. Crear mapeo completo: `scripts/create_cp_ageb_mapping.py`
4. Conectar aplicaciones externas: Puerto 5432
