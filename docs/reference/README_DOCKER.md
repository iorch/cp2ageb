# 🐳 Guía de Docker para cp2ageb

## 📋 Descripción

Este contenedor PostGIS tiene **descarga y carga automática** de shapefiles. Al iniciar el contenedor por primera vez:

1. ✅ Verifica si los shapefiles están descargados localmente
2. 📥 Si no están presentes, los descarga automáticamente (SEPOMEX + INEGI)
3. 💾 Carga todos los shapefiles a la base de datos PostGIS
4. 🚀 La base de datos queda lista para usar

## 🎛️ Variables de Entorno

Puedes controlar el comportamiento automático con estas variables:

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `AUTO_DOWNLOAD` | `true` | Descarga automática de shapefiles si no existen |
| `AUTO_LOAD` | `true` | Carga automática de shapefiles a PostGIS |
| `POSTGRES_DB` | `cp2ageb` | Nombre de la base de datos |
| `POSTGRES_USER` | `geouser` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `geopassword` | Contraseña de PostgreSQL |

## 🚀 Inicio Rápido

### Opción 1: Con descarga y carga automática (recomendado)

```bash
# Simplemente levantar el contenedor
docker-compose up -d

# Ver el progreso de descarga y carga
docker-compose logs -f postgis

# Una vez terminado, conectar
docker-compose exec postgis psql -U geouser -d cp2ageb
```

**Tiempo estimado:** 15-30 minutos dependiendo de tu conexión a Internet

### Opción 2: Solo descarga automática

```bash
# Editar docker-compose.yml o crear .env
# AUTO_DOWNLOAD=true
# AUTO_LOAD=false

docker-compose up -d

# Cargar manualmente después
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

### Opción 3: Todo manual

```bash
# Deshabilitar descarga y carga automática
# En docker-compose.yml:
# AUTO_DOWNLOAD: "false"
# AUTO_LOAD: "false"

docker-compose up -d

# Descargar en tu máquina
python download_shapefiles.py
python download_ageb_shapefiles.py

# Cargar desde el contenedor
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

## 📂 Estructura de Datos

Los shapefiles se guardan en:

```
data/
├── cp_shapefiles/          # Códigos Postales de SEPOMEX (32 ZIPs)
└── ageb_shapefiles/        # AGEBs de INEGI (32 ZIPs)
```

Después de la carga, la base de datos contiene:

```
PostgreSQL
├── sepomex.*               # ~32+ tablas de códigos postales
└── inegi.*                 # ~150+ tablas de AGEBs, manzanas, etc.
```

## 🔍 Verificación

### Ver el progreso de carga

```bash
# Logs en tiempo real
docker-compose logs -f postgis

# Verificar tablas cargadas
docker-compose exec postgis psql -U geouser -d cp2ageb -c "\\dt sepomex.*"
docker-compose exec postgis psql -U geouser -d cp2ageb -c "\\dt inegi.*"

# Ver metadatos de carga
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "SELECT * FROM public.load_metadata ORDER BY loaded_at DESC;"
```

## 🛠️ Comandos Útiles

### Reiniciar con datos limpios

```bash
# Detener y eliminar todo (incluyendo volúmenes)
docker-compose down -v

# Eliminar shapefiles descargados (opcional)
rm -rf data/cp_shapefiles/* data/ageb_shapefiles/*

# Volver a iniciar (descargará y cargará todo de nuevo)
docker-compose up -d
```

### Reconstruir imagen

```bash
# Después de cambios en Dockerfile o scripts
docker-compose build --no-cache
docker-compose up -d
```

### Backup y Restore

```bash
# Backup completo
docker-compose exec postgis pg_dump -U geouser cp2ageb > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgis psql -U geouser cp2ageb < backup_20241104.sql

# Backup solo schemas específicos
docker-compose exec postgis pg_dump -U geouser -n sepomex -n inegi cp2ageb > backup_schemas.sql
```

## 🐛 Troubleshooting

### El contenedor no inicia

```bash
# Ver logs detallados
docker-compose logs postgis

# Verificar que no haya otro PostgreSQL en el puerto 5432
lsof -i :5432
```

### La descarga falla

```bash
# Descargar manualmente en tu máquina
python download_shapefiles.py
python download_ageb_shapefiles.py

# Luego solo cargar (deshabilitar AUTO_DOWNLOAD)
# En docker-compose.yml: AUTO_DOWNLOAD: "false"
docker-compose up -d
```

### La carga falla o se interrumpe

```bash
# Volver a cargar manualmente
docker-compose exec postgis python3 /scripts/load_shapefiles.py

# Ver errores específicos
docker-compose exec postgis python3 /scripts/load_shapefiles.py 2>&1 | tee load.log
```

### Espacio en disco insuficiente

Los shapefiles ocupan aproximadamente:
- SEPOMEX: ~500 MB
- INEGI: ~2-3 GB
- Base de datos PostGIS: ~4-5 GB después de cargar

Total necesario: **~8-10 GB libres**

```bash
# Verificar espacio
df -h

# Limpiar imágenes Docker antiguas
docker system prune -a
```

## 🔐 Seguridad

⚠️ **IMPORTANTE**: Las credenciales por defecto son para desarrollo local solamente.

Para producción:

1. Cambia las credenciales en `.env`:
   ```bash
   POSTGRES_PASSWORD=tu_contraseña_segura
   ```

2. No expongas el puerto 5432 públicamente:
   ```yaml
   ports:
     - "127.0.0.1:5432:5432"  # Solo localhost
   ```

3. Usa variables de entorno seguras:
   ```bash
   export POSTGRES_PASSWORD=$(openssl rand -base64 32)
   docker-compose up -d
   ```

## 📊 Monitoreo

```bash
# Ver uso de recursos
docker stats cp2ageb-postgis

# Conexiones activas
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "SELECT * FROM pg_stat_activity WHERE datname = 'cp2ageb';"

# Tamaño de la base de datos
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "SELECT pg_size_pretty(pg_database_size('cp2ageb'));"

# Tamaño de schemas
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "SELECT schema_name,
   pg_size_pretty(SUM(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)))::bigint)
   FROM pg_tables
   WHERE schemaname IN ('sepomex', 'inegi')
   GROUP BY schema_name;"
```

## 🎯 Próximos Pasos

Una vez que la base de datos esté lista:

1. Explorar los datos:
   ```sql
   \dt sepomex.*
   \dt inegi.*
   ```

2. Hacer consultas espaciales
3. Crear el mapping CP → AGEB
4. Exportar resultados

Ver [README.md](README.md) para más información sobre el proyecto.
