# Validación de Integridad de Archivos ZIP

## Resumen

El sistema ahora incluye validación automática de integridad para todos los archivos ZIP descargados y cargados.

## Cambios Implementados

### 1. Verificación Pre-Descarga (NUEVO)

Los scripts ahora **verifican si el archivo ya existe** antes de descargarlo:

**Comportamiento**:
- ✅ **Archivo existe y es válido**: Se salta la descarga
- ⚠️ **Archivo existe pero está corrupto**: Se elimina y se descarga de nuevo
- 📥 **Archivo no existe**: Se descarga normalmente

**Ejemplo de output**:
```
[✓] Aguascalientes                  (ya descargado)
[✓] Baja California                 (ya descargado)
[!] Coahuila                        (corrupto, re-descargando)
Descargando Coahuila ... ✓ (45.2 MB)
Descargando Chihuahua ... ✓ (52.1 MB)
```

### 2. Validación Durante la Descarga

Los scripts de descarga verifican cada archivo ZIP inmediatamente después de descargarlo:

**`download_shapefiles.py`** (SEPOMEX Códigos Postales):
- Verifica que el ZIP se puede abrir correctamente
- Ejecuta `testzip()` para detectar archivos corruptos dentro del ZIP
- Si el ZIP es inválido, lo elimina automáticamente
- Si hay error durante la descarga, elimina archivos parciales

**`download_ageb_shapefiles.py`** (INEGI Marco Geoestadístico):
- Misma validación que download_shapefiles.py
- Verifica archivos inmediatamente después de descargarlos
- Elimina ZIPs corruptos o parciales automáticamente

### 3. Validación Durante la Carga (Load Time)

**`scripts/load_shapefiles.py`**:
- La función `extract_zip()` ahora verifica integridad antes de extraer
- Si detecta un ZIP corrupto:
  1. Muestra mensaje claro de error
  2. **Elimina el archivo ZIP corrupto**
  3. Permite que la próxima ejecución lo descargue de nuevo
  4. Continúa con los siguientes archivos

## Comportamiento

### Ejemplo 1: ZIP Corrupto Durante Descarga

```bash
$ python3 download_ageb_shapefiles.py

Descargando Coahuila ... ✗ ZIP inválido
# El archivo se elimina automáticamente
```

### Ejemplo 2: ZIP Corrupto Durante Carga

```bash
$ docker-compose exec postgis python3 /scripts/load_shapefiles.py

[05] Coahuila
  Extrayendo 05_coahuila.zip... ✗ Archivo ZIP corrupto o inválido
    Eliminando 05_coahuila.zip para permitir re-descarga...
    ✓ Archivo eliminado. Re-ejecute para descargar de nuevo.
```

### Ejemplo 3: Re-descarga Automática

```bash
# Primera ejecución - detecta archivo corrupto
$ ./benchmark.sh --full
[05] Coahuila
  Extrayendo 05_coahuila.zip... ✗ Archivo ZIP corrupto o inválido
    Eliminando 05_coahuila.zip para permitir re-descarga...

# Segunda ejecución - descarga de nuevo automáticamente
$ ./benchmark.sh --full
[05] Coahuila
  Descargando Coahuila ... ✓ (45.2 MB)
  Extrayendo 05_coahuila.zip... ✓ (15 shapefiles)
```

## Archivos Corruptos Detectados en el Benchmark

En el benchmark completo se detectaron estos estados con ZIPs corruptos:

1. **05** - Coahuila
2. **08** - Chihuahua
3. **12** - Guerrero
4. **16** - Michoacán
5. **17** - Morelos
6. **22** - Querétaro
7. **25** - Sinaloa
8. **30** - Veracruz

## Cómo Resolver Archivos Corruptos

### Opción 1: Re-ejecución Automática (Recomendado)

Los archivos corruptos se eliminan automáticamente. Simplemente vuelva a ejecutar:

```bash
# Si está usando docker-compose
docker-compose restart postgis

# Si está usando el benchmark
./benchmark.sh --resume
```

### Opción 2: Re-descarga Manual

```bash
# Eliminar archivos específicos corruptos
rm data/ageb_shapefiles/05_coahuila.zip
rm data/ageb_shapefiles/08_chihuahua.zip
# ... etc

# Descargar de nuevo
python3 download_ageb_shapefiles.py
```

### Opción 3: Descarga Manual desde INEGI

Si los archivos no se descargan correctamente con el script automático, descárgalos manualmente:

#### Paso 1: Acceder al sitio de INEGI

Visita: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173

**Marco Geoestadístico 2020**

#### Paso 2: Descargar Estados Problemáticos

Los estados que típicamente requieren descarga manual son:

| Estado | Código | Nombre de Archivo | URL del Archivo |
|--------|--------|-------------------|-----------------|
| Coahuila de Zaragoza | 05 | `05_coahuiladezaragoza.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/05_coahuiladezaragoza.zip) |
| Chihuahua | 08 | `08_chihuahua.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/08_chihuahua.zip) |
| Guerrero | 12 | `12_guerrero.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/12_guerrero.zip) |
| Michoacán de Ocampo | 16 | `16_michoacandeocampo.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/16_michoacandeocampo.zip) |
| Morelos | 17 | `17_morelos.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/17_morelos.zip) |
| Querétaro | 22 | `22_queretaro.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/22_queretaro.zip) |
| Sinaloa | 25 | `25_sinaloa.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/25_sinaloa.zip) |
| Veracruz de Ignacio de la Llave | 30 | `30_veracruzignaciodelallave.zip` | [Descargar](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/30_veracruzignaciodelallave.zip) |

#### Paso 3: Guardar en el Directorio Correcto

```bash
# Mover archivos descargados al directorio de datos
mv ~/Downloads/05_coahuiladezaragoza.zip data/ageb_shapefiles/
mv ~/Downloads/08_chihuahua.zip data/ageb_shapefiles/
mv ~/Downloads/12_guerrero.zip data/ageb_shapefiles/
mv ~/Downloads/16_michoacandeocampo.zip data/ageb_shapefiles/
mv ~/Downloads/17_morelos.zip data/ageb_shapefiles/
mv ~/Downloads/22_queretaro.zip data/ageb_shapefiles/
mv ~/Downloads/25_sinaloa.zip data/ageb_shapefiles/
mv ~/Downloads/30_veracruzignaciodelallave.zip data/ageb_shapefiles/

# Verificar que los archivos existen
ls -lh data/ageb_shapefiles/*.zip
```

#### Paso 4: Verificar Integridad

```bash
# Verificar que los ZIPs son válidos
for zip in data/ageb_shapefiles/*.zip; do
    if python3 -m zipfile -t "$zip" > /dev/null 2>&1; then
        echo "✓ $(basename $zip)"
    else
        echo "✗ $(basename $zip) - CORRUPTO"
    fi
done
```

#### Paso 5: Cargar a la Base de Datos

```bash
# Método 1: Desde el contenedor Docker
docker-compose exec postgis python3 /scripts/load_shapefiles.py

# Método 2: Reiniciar para carga automática
docker-compose restart postgis
docker-compose logs -f postgis
```

#### Formato de Nombres de Archivo

**IMPORTANTE**: Los archivos deben seguir este formato exacto:

```
{codigo}_{nombre}.zip
```

Donde:
- `{codigo}` = Código de 2 dígitos (01-32)
- `{nombre}` = Nombre del estado en minúsculas, sin espacios, sin acentos

**Ejemplos correctos**:
- ✅ `05_coahuiladezaragoza.zip`
- ✅ `16_michoacandeocampo.zip`
- ✅ `30_veracruzignaciodelallave.zip`

**Ejemplos incorrectos**:
- ❌ `05_coahuila.zip` (nombre incompleto)
- ❌ `05_Coahuila.zip` (mayúsculas)
- ❌ `05 coahuila.zip` (espacio en lugar de guion bajo)
- ❌ `coahuila.zip` (falta código)

#### Troubleshooting Descarga Manual

**Problema**: El archivo descargado está corrupto

**Solución**:
1. Eliminar el archivo corrupto
2. Limpiar caché del navegador
3. Intentar con otro navegador (Firefox, Chrome, Edge)
4. Usar `wget` o `curl`:

```bash
# Usando wget
wget -O data/ageb_shapefiles/05_coahuiladezaragoza.zip \
  https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/05_coahuiladezaragoza.zip

# Usando curl
curl -o data/ageb_shapefiles/05_coahuiladezaragoza.zip \
  https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/05_coahuiladezaragoza.zip
```

**Problema**: INEGI muestra error 404

**Solución**:
1. Verificar que el nombre del archivo es correcto
2. Visitar la página principal del Marco Geoestadístico
3. Buscar actualizaciones o nuevas versiones del dataset

## Verificación Manual de Integridad

Si desea verificar manualmente la integridad de un archivo ZIP:

```bash
# Método 1: Python
python3 -m zipfile -t data/ageb_shapefiles/05_coahuila.zip

# Método 2: unzip
unzip -t data/ageb_shapefiles/05_coahuila.zip

# Método 3: Dentro del contenedor Docker
docker-compose exec postgis python3 -c "
import zipfile
from pathlib import Path
zip_path = Path('/data/ageb_shapefiles/05_coahuila.zip')
with zipfile.ZipFile(zip_path, 'r') as z:
    bad = z.testzip()
    if bad:
        print(f'Archivo corrupto: {bad}')
    else:
        print('ZIP válido')
"
```

## Checksums (Futuro)

Actualmente no tenemos checksums oficiales de INEGI para validar los archivos. Las opciones futuras incluyen:

1. **Checksums generados localmente**: Después de la primera descarga exitosa, guardar checksums para validaciones futuras
2. **Checksums de comunidad**: Mantener un repositorio de checksums verificados
3. **Validación de contenido**: Además de la integridad del ZIP, verificar que los shapefiles contienen las columnas esperadas

## Impacto en el Benchmark

Con la validación de integridad:
- **Tiempo de descarga**: +2-5 segundos por estado (overhead de validación)
- **Confiabilidad**: 100% - No se cargan archivos corruptos
- **Recuperación automática**: Sí - Los archivos corruptos se eliminan para permitir re-descarga

## Logs y Debugging

Los mensajes de error ahora son más claros:

```
✗ ZIP inválido                              # No es un archivo ZIP válido
✗ ZIP corrupto (archivo dañado: file.shp)   # ZIP válido pero contiene archivos dañados
✗ Error: HTTP 404                           # Archivo no encontrado en servidor
✗ Error: Timeout                            # Descarga interrumpida
```

## Testing

Para probar la validación de integridad:

```bash
# Crear un archivo ZIP inválido para testing
echo "not a zip" > data/ageb_shapefiles/99_test.zip

# Intentar cargarlo
docker-compose exec postgis python3 /scripts/load_shapefiles.py

# El sistema debe:
# 1. Detectar que es inválido
# 2. Mostrar mensaje de error
# 3. Eliminar el archivo
# 4. Continuar con los demás estados
```

## Contribuciones

Si encuentra archivos consistentemente corruptos o tiene checksums verificados, por favor:
1. Abra un issue en el repositorio
2. Incluya el código del estado y el mensaje de error
3. Si tiene un checksum verificado, compártalo

---

**Última actualización**: 2025-11-07
**Versión**: 1.0.0
