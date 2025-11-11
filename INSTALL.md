# Instalación Detallada - cp2ageb

Guía completa de instalación, configuración y troubleshooting.

## Tabla de Contenidos

- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación Paso a Paso](#instalación-paso-a-paso)
- [Configuración Avanzada](#configuración-avanzada)
- [Troubleshooting](#troubleshooting)
- [Operaciones Comunes](#operaciones-comunes)

## Requisitos del Sistema

### Software Requerido

- **Docker**: 20.10+ ([Instalar Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0+ ([Instalar Docker Compose](https://docs.docker.com/compose/install/))
- **Git**: Para clonar el repositorio
- **Python 3.8+**: (Opcional) Solo si ejecutas scripts fuera de Docker

#### Docker Compose v1 vs v2

Este proyecto funciona con ambas versiones:

- **v1 (standalone)**: Comando `docker-compose` (con guión)
- **v2 (plugin)**: Comando `docker compose` (sin guión)

**¿Cuál tengo?**

```bash
# Verificar v1
docker-compose --version
# Si funciona: Docker Compose version 1.29.x

# Verificar v2
docker compose version
# Si funciona: Docker Compose version v2.x.x
```

**Recomendación**: Docker Desktop incluye v2 por defecto. Si tienes Docker Desktop, usa `docker compose` (sin guión).

**En esta documentación**: Usamos `docker-compose`, pero puedes reemplazarlo por `docker compose` en todos los comandos.

### Hardware Recomendado

| Configuración | RAM | Disco | Tiempo Estimado |
|--------------|-----|-------|-----------------|
| Mínima (1 estado) | 4GB | 5GB | ~20 min |
| Estándar (4 estados) | 8GB | 15GB | ~1-2 horas |
| Completa (32 estados) | 16GB | 50GB | ~8-10 horas |

### Sistemas Operativos Soportados

- ✅ Linux (Ubuntu 20.04+, Debian 11+, etc.)
- ✅ macOS 10.15+
- ✅ Windows 10/11 con WSL2

## Instalación Paso a Paso

### 1. Clonar el Repositorio

```bash
# HTTPS
git clone https://github.com/iorch/cp2ageb.git

# SSH (recomendado si tienes SSH key configurada)
git clone git@github.com:iorch/cp2ageb.git

# Entrar al directorio
cd cp2ageb
```

### 2. Verificar Docker

```bash
# Verificar que Docker está instalado
docker --version
# Salida esperada: Docker version 20.10.x

# Verificar Docker Compose
docker-compose --version
# Salida esperada: Docker Compose version v2.x.x

# Verificar que Docker está corriendo
docker ps
# Si hay error, iniciar Docker Desktop o service docker start
```

### 3. Configuración Inicial (Opcional)

#### Editar Variables de Entorno

```bash
# Crear archivo .env (opcional)
cp .env.example .env

# Editar configuración
nano .env
```

#### Configurar Estados a Cargar

Edita `docker-compose.yml`:

```yaml
environment:
  # Opción 1: Solo Jalisco (testing rápido - ~20 min)
  LOAD_ESTADOS: "14"

  # Opción 2: Estados principales (default - ~1-2 horas)
  LOAD_ESTADOS: "14,15,09,19"

  # Opción 3: Todos los estados (~8-10 horas)
  LOAD_ESTADOS: "all"
```

#### Configurar Capas a Cargar

```yaml
environment:
  LOAD_AGEBS: "true"        # Requerido para CP→AGEB
  LOAD_MANZANAS: "false"    # Opcional, +50% tiempo
  LOAD_LOCALIDADES: "false" # Opcional
  LOAD_MUNICIPIOS: "false"  # Opcional
```

### 4. Levantar Contenedor

```bash
# Iniciar en background
docker-compose up -d

# Salida esperada:
# Creating network "cp2ageb_geonet" ... done
# Creating volume "cp2ageb_pgdata" ... done
# Creating cp2ageb-postgis ... done
```

### 5. Monitorear Progreso

```bash
# Ver logs en tiempo real
docker-compose logs -f postgis

# Presiona Ctrl+C para salir (el contenedor sigue corriendo)
```

**Mensajes importantes en logs:**

```
✓ PostgreSQL está listo
→ Descargando shapefiles de SEPOMEX (X/32 presentes)...
→ Descargando shapefiles de INEGI (X/32 presentes)...
→ Iniciando carga de shapefiles...
[01] Aguascalientes ✓
[14] Jalisco ✓
...
✓ Shapefiles cargados exitosamente
✓ Función buscar_agebs_por_cp creada
======================================
  🎉 Sistema Listo
======================================
```

### 6. Verificar Instalación

```bash
# Verificar que el contenedor está corriendo
docker-compose ps

# Conectar a la base de datos
docker-compose exec postgis psql -U geouser -d cp2ageb

# Dentro de psql:
# Ver tablas cargadas
\dt sepomex.*
\dt inegi.*

# Probar función
SELECT * FROM buscar_agebs_por_cp('44100');

# Salir
\q
```

## Configuración Avanzada

### Usar Descarga Manual de Shapefiles

Si la descarga automática falla:

```bash
# 1. Desactivar descarga automática
# En docker-compose.yml:
AUTO_DOWNLOAD: "false"

# 2. Descargar manualmente
mkdir -p data/cp_shapefiles data/ageb_shapefiles

# 3. Información de fuentes de datos:
# SEPOMEX: https://www.datos.gob.mx/dataset/codigos_postales_entidad_federativa
# INEGI: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173
# Nota: Los archivos se descargan automáticamente con los scripts del proyecto

# 4. Colocar archivos en:
# - data/cp_shapefiles/CP_*.zip
# - data/ageb_shapefiles/*.zip

# 5. Reiniciar contenedor
docker-compose restart postgis
```

### Cambiar Puerto de PostgreSQL

```yaml
# docker-compose.yml
ports:
  - "5433:5432"  # Cambiar puerto externo a 5433
```

### Persistencia de Datos

Los datos se guardan en un volumen Docker:

```bash
# Ver volúmenes
docker volume ls | grep cp2ageb

# Backup del volumen
docker run --rm -v cp2ageb_pgdata:/data -v $(pwd):/backup \
  busybox tar czf /backup/pgdata-backup.tar.gz /data

# Restaurar backup
docker run --rm -v cp2ageb_pgdata:/data -v $(pwd):/backup \
  busybox tar xzf /backup/pgdata-backup.tar.gz -C /
```

### Conectar desde Aplicaciones Externas

```python
# Python con psycopg2
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="cp2ageb",
    user="geouser",
    password="geopassword"
)

cur = conn.cursor()
cur.execute("SELECT * FROM buscar_agebs_por_cp('44100');")
results = cur.fetchall()
```

```javascript
// Node.js con pg
const { Client } = require('pg');

const client = new Client({
  host: 'localhost',
  port: 5432,
  database: 'cp2ageb',
  user: 'geouser',
  password: 'geopassword'
});

await client.connect();
const res = await client.query("SELECT * FROM buscar_agebs_por_cp('44100')");
```

## Troubleshooting

### Error: "docker-compose: command not found"

Si obtienes este error, tienes Docker Compose v2 (plugin):

```bash
# En lugar de:
docker-compose up -d

# Usa (sin guión):
docker compose up -d
```

O instala v1:
```bash
# Linux
sudo apt-get install docker-compose

# macOS con Homebrew
brew install docker-compose

# O usa alias en ~/.bashrc o ~/.zshrc
alias docker-compose='docker compose'
```

### Error: Puerto 5432 ya en uso

```bash
# Ver qué está usando el puerto
sudo lsof -i :5432
# o en Linux:
sudo netstat -nlp | grep 5432

# Opción 1: Detener el servicio conflictivo
sudo systemctl stop postgresql

# Opción 2: Cambiar puerto en docker-compose.yml
ports:
  - "5433:5432"
```

### Error: No hay espacio en disco

```bash
# Ver uso de disco
df -h

# Limpiar Docker
docker system prune -a

# Limpiar volúmenes no usados
docker volume prune

# Si es necesario, reducir estados a cargar
LOAD_ESTADOS="14" docker-compose up -d
```

### Error: Archivos ZIP corruptos

```bash
# Los scripts detectan y re-descargan automáticamente
# Si persiste, eliminar el archivo corrupto manualmente:
rm data/ageb_shapefiles/01_aguascalientes.zip

# Reiniciar (descarga automáticamente)
docker-compose restart postgis

# Los archivos se descargan automáticamente desde INEGI
# Información del dataset: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173
```

### Error: "Database not available" en tests

```bash
# Verificar que el contenedor está corriendo
docker-compose ps

# Ver logs
docker-compose logs postgis

# Reiniciar
docker-compose restart postgis

# Esperar a que esté listo
docker-compose logs -f postgis
# Buscar mensaje: "🎉 Sistema Listo"
```

### Performance: Carga muy lenta

```bash
# Verificar recursos Docker
docker stats cp2ageb-postgis

# Aumentar recursos en Docker Desktop:
# Settings → Resources → Memory: 8GB mínimo

# Reducir estados a cargar
LOAD_ESTADOS="14" docker-compose up -d

# Desactivar capas opcionales
LOAD_MANZANAS: "false"
LOAD_LOCALIDADES: "false"
LOAD_MUNICIPIOS: "false"
```

### Error: "Permission denied" en scripts

```bash
# Dar permisos de ejecución
chmod +x buscar_cp.sh
chmod +x benchmark.sh
chmod +x run_tests.sh
```

### Contenedor se detiene inesperadamente

```bash
# Ver logs completos
docker-compose logs postgis > logs.txt

# Verificar salud del contenedor
docker inspect cp2ageb-postgis

# Reiniciar desde cero
docker-compose down -v
docker-compose up -d
```

## Operaciones Comunes

### Reiniciar sin Perder Datos

```bash
# Detener contenedor
docker-compose stop

# Iniciar contenedor
docker-compose start

# O reiniciar directamente
docker-compose restart postgis
```

### Reiniciar desde Cero

```bash
# ADVERTENCIA: Esto elimina TODOS los datos
docker-compose down -v

# Iniciar nuevamente
docker-compose up -d
```

### Agregar Más Estados

```bash
# 1. Editar docker-compose.yml
nano docker-compose.yml

# Cambiar:
LOAD_ESTADOS: "14,15,09,19,20,21"  # Agregar estados

# 2. Detener contenedor
docker-compose down

# 3. Iniciar (carga solo los nuevos)
docker-compose up -d
```

### Backup y Restauración

#### Backup con pg_dump

```bash
# Backup completo
docker-compose exec postgis pg_dump -U geouser cp2ageb > backup_$(date +%Y%m%d).sql

# Backup solo schema
docker-compose exec postgis pg_dump -U geouser -s cp2ageb > schema.sql

# Backup comprimido
docker-compose exec postgis pg_dump -U geouser cp2ageb | gzip > backup.sql.gz
```

#### Restaurar Backup

```bash
# Restaurar desde SQL
docker-compose exec -T postgis psql -U geouser cp2ageb < backup.sql

# Restaurar desde comprimido
gunzip -c backup.sql.gz | docker-compose exec -T postgis psql -U geouser cp2ageb
```

### Actualizar a Nueva Versión

```bash
# 1. Hacer backup
docker-compose exec postgis pg_dump -U geouser cp2ageb > backup_before_update.sql

# 2. Detener contenedor
docker-compose down

# 3. Actualizar código
git pull origin main

# 4. Rebuild imagen (si hay cambios en Dockerfile)
docker-compose build --no-cache

# 5. Iniciar
docker-compose up -d
```

### Ver Estado de Carga

```bash
# Conectar a la BD
docker-compose exec postgis psql -U geouser -d cp2ageb

# Ver metadatos de carga
SELECT * FROM public.load_metadata ORDER BY loaded_at DESC;

# Ver estados cargados
\dt sepomex.*
\dt inegi.*

# Contar registros
SELECT 'SEPOMEX', COUNT(*) FROM sepomex.cp_14_cp_jal
UNION ALL
SELECT 'INEGI Urbana', COUNT(*) FROM inegi.ageb_urbana_14
UNION ALL
SELECT 'INEGI Rural', COUNT(*) FROM inegi.ageb_rural_14;
```

## Reportar Problemas

Si encuentras un problema no documentado:

1. **Revisar logs**: `docker-compose logs postgis > logs.txt`
2. **Verificar configuración**: `docker-compose config`
3. **Abrir issue**: [GitHub Issues](https://github.com/iorch/cp2ageb/issues)
4. **Incluir**:
   - Sistema operativo y versión
   - Versión de Docker y Docker Compose
   - Configuración de estados/capas
   - Logs relevantes

## Recursos Adicionales

- [QUICKSTART.md](QUICKSTART.md) - Guía de inicio rápido
- [README.md](README.md) - Documentación principal
- [tests/README.md](tests/README.md) - Documentación de tests
- [queries/README.md](queries/README.md) - Guía de queries SQL

---

**¿Necesitas ayuda?** Abre un [issue](https://github.com/iorch/cp2ageb/issues) o revisa las [discussions](https://github.com/iorch/cp2ageb/discussions)
