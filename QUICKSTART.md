# Inicio Rápido

Guía para empezar a usar cp2ageb en 3 pasos.

> **Nota**: Si tienes Docker Desktop reciente, reemplaza `docker-compose` por `docker compose` (sin guión) en todos los comandos.

## 1. Iniciar el Sistema

```bash
docker-compose up -d
```

El sistema automáticamente:
- Descarga shapefiles de SEPOMEX e INEGI (si no existen)
- Carga los datos a PostGIS (por defecto: Jalisco, Edo Mex, CDMX, NL)
- Crea la función `buscar_agebs_por_cp()`

**Tiempo de carga**: ~1-2 horas para 4 estados (Jalisco, Edo Mex, CDMX, Nuevo León)

**Para cargar todos los estados** (~8-10 horas):
```bash
# Editar docker-compose.yml y cambiar:
LOAD_ESTADOS: "all"  # Todos los 32 estados
```

**Para probar solo Jalisco** (~20 minutos):
```bash
# Editar docker-compose.yml y cambiar:
LOAD_ESTADOS: "14"  # Solo Jalisco
```

## 2. Verificar el Estado

```bash
# Ver logs de carga
docker-compose logs -f

# Cuando veas "Sistema Listo - cp2ageb", ya puedes usar el sistema
```

## 3. Buscar AGEBs por Código Postal

### Opción A: Script Simple (Recomendado)

```bash
# Jalisco (Guadalajara)
./buscar_cp.sh 44100

# CDMX (Polanco)
./buscar_cp.sh 11560

# Edo México (Toluca)
./buscar_cp.sh 50000

# Nuevo León (Monterrey)
./buscar_cp.sh 64000
```

### Opción B: Comando Directo

```bash
docker-compose exec postgis psql -U geouser -d cp2ageb \
  -c "SELECT * FROM buscar_agebs_por_cp('44100');"
```

### Opción C: Query SQL Completo

```bash
docker-compose exec postgis psql -U geouser -d cp2ageb \
  -f /queries/cp_to_ageb_dynamic.sql
```

## Resultados Esperados

La función retorna:

| codigo_postal | clave_ageb      | tipo_ageb | porcentaje_interseccion |
|---------------|-----------------|-----------|-------------------------|
| 44100         | 140100010014A   | urbana    | 45.67                  |
| 44100         | 140100010015A   | urbana    | 32.18                  |
| ...           | ...             | ...       | ...                    |

- **codigo_postal**: El CP buscado
- **clave_ageb**: Clave del AGEB (formato INEGI)
- **tipo_ageb**: 'urbana' o 'rural'
- **porcentaje_interseccion**: % del CP que intersecta con el AGEB

## Conectarse a la Base de Datos

```bash
# Desde el host
psql -h localhost -U geouser -d cp2ageb

# Desde el contenedor
docker-compose exec postgis psql -U geouser -d cp2ageb
```

**Contraseña**: `geopassword`

## Configuración Avanzada

### Cargar Solo Ciertos Estados

Editar `docker-compose.yml`:

```yaml
environment:
  # Default: Jalisco, Edo Mex, CDMX, Nuevo León (~1-2 horas)
  LOAD_ESTADOS: "14,15,09,19"

  # Solo Jalisco para pruebas rápidas (~20 min)
  LOAD_ESTADOS: "14"

  # Más estados por código
  LOAD_ESTADOS: "14,15,09,19,20"  # + Oaxaca

  # O usar nombres
  LOAD_ESTADOS: "Jalisco,CDMX"

  # Todos los 32 estados (~8-10 horas)
  LOAD_ESTADOS: "all"
```

### Cargar Capas Adicionales de INEGI

Por defecto solo se cargan AGEBs. Para cargar más:

```yaml
environment:
  LOAD_MANZANAS: "true"      # Bloques urbanos
  LOAD_LOCALIDADES: "true"   # Pueblos/ciudades
  LOAD_MUNICIPIOS: "true"    # Municipios
  LOAD_ENTIDADES: "true"     # Estados
```

**Nota**: Cargar manzanas aumenta el tiempo ~50% (de 8h a 12h)

### Control Manual (Modo Benchmark)

```yaml
environment:
  AUTO_DOWNLOAD: "false"
  AUTO_LOAD: "false"
```

Luego cargar manualmente:
```bash
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

## Detener el Sistema

```bash
# Mantener los datos
docker-compose down

# Eliminar todo (incluyendo datos)
docker-compose down -v
```

## Troubleshooting

### "No se encontró el código postal"

El estado del CP no está cargado. Verifica `LOAD_ESTADOS` en `docker-compose.yml`.

### "Función buscar_agebs_por_cp no existe"

Crea la función manualmente:
```bash
docker-compose exec postgis psql -U geouser -d cp2ageb \
  -f /queries/cp_to_ageb_function.sql
```

### Ver qué estados están cargados

```sql
SELECT DISTINCT table_name
FROM information_schema.tables
WHERE table_schema = 'sepomex'
ORDER BY table_name;
```

## Siguientes Pasos

- Ver queries de ejemplo: `queries/cp_to_ageb.sql`
- Crear mapeo completo: `scripts/create_cp_ageb_mapping.py`
- Leer documentación completa: `README.md`
