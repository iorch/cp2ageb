# Guía de Descarga Manual - Marco Geoestadístico INEGI

Esta guía te ayudará a descargar manualmente los archivos ZIP de INEGI que no se pueden descargar automáticamente con el script.

## Estados que Requieren Descarga Manual

Los siguientes 8 estados típicamente requieren descarga manual:

1. **05** - Coahuila de Zaragoza
2. **08** - Chihuahua
3. **12** - Guerrero
4. **16** - Michoacán de Ocampo
5. **17** - Morelos
6. **22** - Querétaro
7. **25** - Sinaloa
8. **30** - Veracruz de Ignacio de la Llave

## Método 1: Descarga desde el Navegador

### Paso 1: Acceder al Sitio

Abre en tu navegador: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173

### Paso 2: Descargar Archivos

Haz clic derecho en los siguientes enlaces y selecciona "Guardar enlace como...":

- [05_coahuiladezaragoza.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/05_coahuiladezaragoza.zip)
- [08_chihuahua.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/08_chihuahua.zip)
- [12_guerrero.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/12_guerrero.zip)
- [16_michoacandeocampo.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/16_michoacandeocampo.zip)
- [17_morelos.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/17_morelos.zip)
- [22_queretaro.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/22_queretaro.zip)
- [25_sinaloa.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/25_sinaloa.zip)
- [30_veracruzignaciodelallave.zip](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/30_veracruzignaciodelallave.zip)

### Paso 3: Mover a la Ubicación Correcta

```bash
# Navegar al directorio del proyecto
cd /ruta/a/cp2ageb

# Mover archivos desde Downloads
mv ~/Downloads/05_coahuiladezaragoza.zip data/ageb_shapefiles/
mv ~/Downloads/08_chihuahua.zip data/ageb_shapefiles/
mv ~/Downloads/12_guerrero.zip data/ageb_shapefiles/
mv ~/Downloads/16_michoacandeocampo.zip data/ageb_shapefiles/
mv ~/Downloads/17_morelos.zip data/ageb_shapefiles/
mv ~/Downloads/22_queretaro.zip data/ageb_shapefiles/
mv ~/Downloads/25_sinaloa.zip data/ageb_shapefiles/
mv ~/Downloads/30_veracruzignaciodelallave.zip data/ageb_shapefiles/
```

## Método 2: Descarga con wget

```bash
# Navegar al directorio de datos
cd data/ageb_shapefiles/

# Descargar cada archivo
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/05_coahuiladezaragoza.zip
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/08_chihuahua.zip
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/12_guerrero.zip
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/16_michoacandeocampo.zip
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/17_morelos.zip
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/22_queretaro.zip
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/25_sinaloa.zip
wget https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/30_veracruzignaciodelallave.zip

# Regresar al directorio del proyecto
cd ../..
```

## Método 3: Descarga con curl

```bash
# Navegar al directorio de datos
cd data/ageb_shapefiles/

# Descargar todos los archivos problemáticos con curl
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/05_coahuiladezaragoza.zip
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/08_chihuahua.zip
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/12_guerrero.zip
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/16_michoacandeocampo.zip
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/17_morelos.zip
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/22_queretaro.zip
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/25_sinaloa.zip
curl -O https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/794551132173/30_veracruzignaciodelallave.zip

cd ../..
```

## Verificación de Integridad

Después de descargar, verifica que los archivos son válidos:

```bash
# Verificar todos los archivos
for zip in data/ageb_shapefiles/*.zip; do
    if python3 -m zipfile -t "$zip" > /dev/null 2>&1; then
        echo "✓ $(basename $zip) - VÁLIDO"
    else
        echo "✗ $(basename $zip) - CORRUPTO"
    fi
done
```

## Formato de Nombres de Archivo

**MUY IMPORTANTE**: Los nombres deben seguir este formato EXACTO:

```
{codigo}_{nombre}.zip
```

Donde:
- `{codigo}` = Código de 2 dígitos (01-32)
- `{nombre}` = Nombre del estado sin espacios, sin acentos, minúsculas

### Ejemplos Correctos ✅

- `05_coahuiladezaragoza.zip` (Coahuila de Zaragoza)
- `16_michoacandeocampo.zip` (Michoacán de Ocampo)
- `30_veracruzignaciodelallave.zip` (Veracruz de Ignacio de la Llave)

### Ejemplos Incorrectos ❌

- `05_coahuila.zip` ❌ (nombre incompleto)
- `05_Coahuila.zip` ❌ (mayúsculas)
- `05 coahuila.zip` ❌ (espacio en lugar de guion bajo)
- `coahuila.zip` ❌ (falta código)
- `05_coahuila_de_zaragoza.zip` ❌ (con guiones bajos adicionales)

## Cargar Datos a la Base de Datos

Una vez descargados los archivos:

### Opción 1: Carga Automática (Reiniciar Contenedor)

```bash
docker-compose restart postgis
docker-compose logs -f postgis
```

### Opción 2: Carga Manual

```bash
docker-compose exec postgis python3 /scripts/load_shapefiles.py
```

### Opción 3: Carga Individual

```bash
# Solo cargar Coahuila (por ejemplo)
docker-compose exec postgis python3 /scripts/load_single_state.py
```

## Troubleshooting

### Problema: "File not found" al cargar

**Causa**: El nombre del archivo no es correcto

**Solución**: Verificar que el nombre sigue el formato exacto:
```bash
ls -la data/ageb_shapefiles/ | grep -E "(05|08|12|16|17|22|25|30)"
```

### Problema: "ZIP corrupto" después de descargar

**Causa**: Descarga incompleta o error de red

**Solución**:
1. Eliminar el archivo corrupto
2. Limpiar caché del navegador
3. Reintentar con otro método (wget o curl)

### Problema: Error 404 en INEGI

**Causa**: URL incorrecta o archivo movido

**Solución**:
1. Visitar la página principal: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173
2. Buscar actualizaciones del Marco Geoestadístico
3. Verificar que los nombres de archivo son correctos

### Problema: Sin espacio en disco

**Causa**: Los 8 archivos ocupan ~800 MB

**Solución**:
```bash
# Verificar espacio disponible
df -h data/ageb_shapefiles/

# Liberar espacio si es necesario
docker system prune -a
```

## Lista de Verificación

- [ ] Descargar los 8 archivos problemáticos
- [ ] Verificar que los nombres son exactamente correctos
- [ ] Mover archivos a `data/ageb_shapefiles/`
- [ ] Verificar integridad con `python3 -m zipfile -t`
- [ ] Cargar a la base de datos
- [ ] Verificar que las tablas existen:
  ```bash
  docker-compose exec postgis psql -U geouser -d cp2ageb -c "\dt inegi.*"
  ```

## Tamaños de Archivo Esperados

| Estado | Código | Tamaño Aproximado |
|--------|--------|-------------------|
| Coahuila de Zaragoza | 05 | ~45 MB |
| Chihuahua | 08 | ~52 MB |
| Guerrero | 12 | ~68 MB |
| Michoacán de Ocampo | 16 | ~71 MB |
| Morelos | 17 | ~35 MB |
| Querétaro | 22 | ~40 MB |
| Sinaloa | 25 | ~55 MB |
| Veracruz de Ignacio de la Llave | 30 | ~125 MB |

**Total**: ~491 MB para los 8 archivos

## Recursos

- **Sitio oficial INEGI**: https://www.inegi.org.mx/
- **Marco Geoestadístico 2020**: https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=794551132173
- **Documentación completa**: Ver [ZIP_VALIDATION.md](ZIP_VALIDATION.md)
- **README principal**: Ver [README.md](README.md)

---

**Última actualización**: 2025-11-07
**Versión**: 1.0.0
