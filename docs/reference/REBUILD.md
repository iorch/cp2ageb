# 🔄 Guía de Reconstrucción y Mantenimiento

## 📋 Comportamiento del Sistema

### Inicio Normal (con datos existentes)
```bash
docker-compose up -d
```
- ✅ Usa datos existentes en el volumen
- ✅ Inicio rápido (~5 segundos)
- ✅ Datos persisten entre reinicios

### Primera Vez / Reconstrucción Completa
```bash
docker-compose down -v
docker-compose up -d
```
- 📥 Descarga automática de shapefiles (si no existen en `./data/`)
- 📊 Carga automática a PostgreSQL
- ⏱️ Tiempo estimado: 15-30 minutos (depende de conexión y CPU)

## 🔧 Escenarios Comunes

### 1. Reconstruir Base de Datos desde Cero

**Elimina el volumen de PostgreSQL pero mantiene los shapefiles descargados:**

```bash
# Detener contenedor y eliminar volumen
docker-compose down -v

# Iniciar de nuevo (usará shapefiles ya descargados)
docker-compose up -d

# Monitorear progreso
docker-compose logs -f postgis
```

**Resultado:**
- Shapefiles ya descargados en `./data/` se reutilizan
- Base de datos se recrea desde cero
- Datos se recargan automáticamente

### 2. Descargar Shapefiles Nuevamente

**Si los archivos ZIP están corruptos o desactualizados:**

```bash
# Eliminar shapefiles descargados
rm -rf data/cp_shapefiles/*
rm -rf data/ageb_shapefiles/*

# Reconstruir todo
docker-compose down -v
docker-compose up -d
```

### 3. Actualizar Solo Código/Scripts

**Sin perder datos ni shapefiles:**

```bash
# Detener contenedor (volumen se mantiene)
docker-compose down

# Reconstruir imagen con nuevo código
docker-compose build

# Iniciar (usa datos existentes)
docker-compose up -d
```

### 4. Cargar Solo Un Estado (Testing Rápido)

```bash
# Con contenedor corriendo
docker-compose exec postgis python3 /scripts/load_single_state.py
```

Este script:
- Carga solo Aguascalientes (estado 01)
- Tiempo: ~2-3 minutos
- Útil para desarrollo y pruebas

### 5. Cargar Todos los Estados

```bash
# Eliminar datos INEGI actuales (mantener SEPOMEX)
docker-compose exec postgis psql -U geouser -d cp2ageb -c "DROP SCHEMA inegi CASCADE; CREATE SCHEMA inegi;"

# Cargar los 32 estados
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

**Advertencia:** Esto puede tomar 2-4 horas.

## 🗂️ Estructura de Datos

### Directorios Locales (Host)
```
data/
├── cp_shapefiles/          # Shapefiles SEPOMEX (32 estados)
│   ├── CP_Ags.zip
│   ├── CP_BC.zip
│   └── ...
└── ageb_shapefiles/        # Shapefiles INEGI (32 estados)
    ├── 01_aguascalientes.zip
    ├── 02_bajacalifornia.zip
    └── ...
```

### Volumen Docker
```
postgres_data/              # Volumen Docker (base de datos)
└── [archivos PostgreSQL internos]
```

## 📊 Variables de Entorno

En `docker-compose.yml`:

```yaml
environment:
  AUTO_DOWNLOAD: "true"   # Descargar shapefiles si faltan
  AUTO_LOAD: "true"       # Cargar a PostgreSQL automáticamente
```

### Deshabilitar Carga Automática

```yaml
environment:
  AUTO_DOWNLOAD: "false"
  AUTO_LOAD: "false"
```

Luego cargar manualmente:
```bash
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

## 🧹 Limpieza Total

**Eliminar TODO (contenedor, volumen, imágenes, shapefiles):**

```bash
# Detener y eliminar contenedor + volumen
docker-compose down -v

# Eliminar shapefiles descargados
rm -rf data/cp_shapefiles/*
rm -rf data/ageb_shapefiles/*

# Eliminar imagen Docker (opcional)
docker rmi cp2ageb-postgis

# Verificar limpieza
docker volume ls | grep cp2ageb
docker images | grep cp2ageb
```

## 🔍 Verificar Estado del Sistema

### Verificar contenedor
```bash
docker-compose ps
```

Esperado:
```
NAME              STATUS
cp2ageb-postgis   Up (healthy)
```

### Verificar datos cargados
```bash
docker-compose exec postgis psql -U geouser -d cp2ageb -c "
SELECT
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sepomex') as sepomex_tables,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='inegi') as inegi_tables;
"
```

Esperado (solo Aguascalientes):
```
sepomex_tables | inegi_tables
---------------+--------------
            32 |            4
```

Esperado (todos los estados):
```
sepomex_tables | inegi_tables
---------------+--------------
            32 |          160+
```

### Verificar shapefiles descargados
```bash
# SEPOMEX (debe tener 32 archivos ZIP)
ls -1 data/cp_shapefiles/*.zip | wc -l

# INEGI (debe tener 32 archivos ZIP)
ls -1 data/ageb_shapefiles/*.zip | wc -l
```

## ⚡ Troubleshooting

### Contenedor no inicia
```bash
# Ver logs completos
docker-compose logs postgis

# Verificar puerto 5432
sudo lsof -i :5432

# Si está ocupado, cambiar puerto en docker-compose.yml
ports:
  - "5433:5432"  # Cambiar 5432 por 5433
```

### Carga muy lenta
```bash
# Verificar uso de CPU/Memoria
docker stats cp2ageb-postgis

# Si es necesario, aumentar recursos en docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

### Shapefile corrupto
```bash
# Ver cuál archivo falló en los logs
docker-compose logs postgis | grep "✗"

# Eliminar archivo corrupto y reconectar
rm data/ageb_shapefiles/XX_estado.zip

# Recargar
docker-compose exec postgis python3 /app/download_ageb_shapefiles.py
```

### Reconstrucción por archivo corrupto específico

Si solo un archivo está corrupto:

```bash
# Ejemplo: Coahuila (05) está corrupto
rm data/ageb_shapefiles/05_coahuila.zip

# Re-descargar ese estado específico
docker-compose exec postgis python3 /app/download_ageb_shapefiles.py

# Cargar manualmente
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

## 📝 Flujo de Trabajo Recomendado

### Desarrollo
```bash
# 1. Primera vez - carga rápida para testing
docker-compose up -d
docker-compose exec postgis python3 /scripts/load_single_state.py

# 2. Probar queries
docker-compose exec postgis psql -U geouser -d cp2ageb

# 3. Modificar código/queries según necesites

# 4. Si necesitas reconstruir datos de prueba
docker-compose down -v
docker-compose up -d
```

### Producción
```bash
# 1. Primera vez - carga completa
docker-compose down -v
docker-compose up -d

# Esperar 2-4 horas para carga completa
docker-compose logs -f postgis

# 2. Verificar datos
docker-compose exec postgis psql -U geouser -d cp2ageb

# 3. Crear backup
docker-compose exec postgis pg_dump -U geouser cp2ageb > backup_$(date +%Y%m%d).sql

# 4. Para reinicios normales (NO eliminar volumen)
docker-compose restart postgis
```

## 💾 Backup y Restore

### Crear Backup
```bash
# Backup completo
docker-compose exec postgis pg_dump -U geouser cp2ageb | gzip > backup_cp2ageb_$(date +%Y%m%d).sql.gz

# Backup solo esquema
docker-compose exec postgis pg_dump -U geouser -s cp2ageb > schema_backup.sql

# Backup solo datos de mapeo
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "COPY (SELECT * FROM public.cp_to_ageb_mapping) TO STDOUT CSV HEADER" | gzip > mapping_$(date +%Y%m%d).csv.gz
```

### Restaurar Backup
```bash
# 1. Crear base de datos limpia
docker-compose down -v
docker-compose up -d

# 2. Esperar a que PostgreSQL esté listo
sleep 10

# 3. Restaurar
gunzip -c backup_cp2ageb_20251105.sql.gz | \
  docker-compose exec -T postgis psql -U geouser -d cp2ageb
```

## ✅ Checklist de Reconstrucción Exitosa

- [ ] Contenedor está corriendo: `docker-compose ps`
- [ ] PostgreSQL acepta conexiones: `docker-compose exec postgis psql -U geouser -d cp2ageb -c "SELECT 1;"`
- [ ] Shapefiles descargados: `ls data/*/`
- [ ] Tablas SEPOMEX cargadas: `\dt sepomex.*` (32 tablas esperadas)
- [ ] Tablas INEGI cargadas: `\dt inegi.*` (4+ tablas para Ags, 160+ para todos)
- [ ] Query espacial funciona: Ver `SOLUTION.md` para query de prueba
- [ ] Extensión PostGIS activa: `SELECT PostGIS_Version();`

---

**Última actualización:** 2025-11-05
