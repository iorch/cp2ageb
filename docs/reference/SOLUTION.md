# Solución: Query Espacial CP → AGEB

## Resumen

Sistema funcional para mapear Códigos Postales de SEPOMEX a AGEBs de INEGI usando PostGIS.

## Query Funcional

**IMPORTANTE:** Incluye AGEBs urbanas Y rurales. Si solo consultas uno, los porcentajes NO sumarán 100%.

```sql
-- Query completo: urbanas Y rurales
WITH cp_ageb_intersections AS (
  SELECT
      cp.d_cp as codigo_postal,
      ageb.cvegeo as clave_ageb,
      'urbana' as tipo_ageb,
      ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) * 100 as porcentaje
  FROM sepomex.cp_01_cp_ags cp
  JOIN inegi.ageb_urbana_01 ageb
    ON ST_Intersects(cp.geom, ageb.geom)
  WHERE cp.d_cp = '20358'

  UNION ALL

  SELECT
      cp.d_cp,
      ageb.cvegeo,
      'rural' as tipo_ageb,
      ST_Area(ST_Intersection(cp.geom, ageb.geom)) / ST_Area(cp.geom) * 100 as porcentaje
  FROM sepomex.cp_01_cp_ags cp
  JOIN inegi.ageb_rural_01 ageb
    ON ST_Intersects(cp.geom, ageb.geom)
  WHERE cp.d_cp = '20358'
)
SELECT
    codigo_postal,
    clave_ageb,
    tipo_ageb,
    ROUND(porcentaje::numeric, 2) as porcentaje_interseccion,
    CASE
        WHEN porcentaje > 50 THEN 'principal'
        ELSE 'parcial'
    END as tipo_relacion
FROM cp_ageb_intersections
WHERE porcentaje > 0.01
ORDER BY porcentaje DESC;
```

## Resultado Ejemplo

Código postal `20358` (Aguascalientes):

```
codigo_postal |  clave_ageb   | tipo_ageb | porcentaje | tipo_relacion
--------------+---------------+-----------+------------+---------------
 20358        | 010110102     | rural     |      76.00 | principal
 20358        | 010050035     | rural     |      14.50 | parcial
 20358        | 0101101380210 | urbana    |       2.48 | parcial
 20358        | 010110138023A | urbana    |       2.26 | parcial
 20358        | 0101101380225 | urbana    |       1.93 | parcial
 20358        | 0101101280136 | urbana    |       1.31 | parcial
 20358        | 0100504270798 | urbana    |       0.91 | parcial
 20358        | 0101101380244 | urbana    |       0.62 | parcial
```

**Interpretación:**
- AGEB principal rural (76%)
- Intersección secundaria rural (14.5%)
- 6 AGEBs urbanas en bordes (0.62% - 2.48%)
- Suma total ≈ 100%

## Consideraciones Técnicas

**SRID Unificado:**
- Ambos schemas usan SRID 900916 (Web Mercator variant)
- SEPOMEX se transforma automáticamente de 900914 a 900916 durante la carga
- No requiere `ST_Transform()` en queries

**Nombres de Columnas:**
- SEPOMEX: `d_cp` (código postal), `geom`
- INEGI: `cvegeo` (clave AGEB), `geom`

**Clasificación INEGI:**
- `{cve}a.shp` → AGEBs urbanas (ej: `01a.shp`)
- `{cve}ar.shp` → AGEBs rurales (ej: `01ar.shp`)
- `{cve}m.shp` → Manzanas
- `{cve}mun.shp` → Municipios
- `{cve}ent.shp` → Entidad

## Uso Rápido

```bash
# Conectar
docker-compose exec postgis psql -U geouser -d cp2ageb

# Ver datos
SELECT COUNT(*) FROM sepomex.cp_01_cp_ags;
SELECT COUNT(*) FROM inegi.ageb_urbana_01;
SELECT COUNT(*) FROM inegi.ageb_rural_01;
```

## Estadísticas Aguascalientes

- Códigos Postales: 379
- AGEBs Urbanas: 513
- AGEBs Rurales: 142
- Municipios: 11

## Scripts Disponibles

```bash
# Carga rápida (1 estado)
docker-compose exec postgis python3 /scripts/load_single_state.py

# Carga completa (32 estados)
docker-compose exec postgis python3 /scripts/load_shapefiles.py

# Crear mapeo consolidado
docker-compose exec postgis python3 /scripts/create_cp_ageb_mapping.py
```

## Exportar Resultados

```bash
docker-compose exec postgis psql -U geouser -d cp2ageb -c \
  "COPY (SELECT * FROM public.cp_to_ageb_mapping ORDER BY estado_cve, codigo_postal) \
   TO STDOUT CSV HEADER" > cp_to_ageb_mapping.csv
```

## Estado

- ✓ Docker + PostGIS funcionando
- ✓ Datos SEPOMEX cargados (32 estados)
- ✓ Datos INEGI cargados (1 estado de prueba)
- ✓ Query espacial validado
- ✓ Scripts de carga optimizados

---

Validado: 2025-11-05
