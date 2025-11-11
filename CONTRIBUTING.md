# Guía de Contribución

Lineamientos para contribuir al proyecto cp2ageb.

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Contribuir](#cómo-contribuir)
- [Configuración del Entorno](#configuración-del-entorno)
- [Flujo de Trabajo](#flujo-de-trabajo)
- [Estándares de Código](#estándares-de-código)
- [Tests](#tests)
- [Documentación](#documentación)

## Código de Conducta

Se espera que mantengas un ambiente respetuoso y acogedor para todos.

## Cómo Contribuir

### Reportar Bugs

1. Busca en [issues existentes](https://github.com/iorch/cp2ageb/issues) para evitar duplicados
2. Abre un nuevo issue con:
   - Título descriptivo
   - Pasos para reproducir
   - Comportamiento esperado vs. real
   - Versión de Docker, SO, etc.
   - Logs relevantes

### Sugerir Mejoras

1. Abre un issue con la etiqueta `enhancement`
2. Describe el caso de uso
3. Explica por qué sería útil
4. Propón una implementación (opcional)

### Contribuir Código

1. Fork el repositorio
2. Crea una rama para tu feature
3. Implementa los cambios
4. Agrega tests
5. Actualiza la documentación
6. Abre un Pull Request

## Configuración del Entorno

### Requisitos

- Docker y Docker Compose
- Python 3.8+
- Git

> **Nota**: Los ejemplos usan `docker-compose` (v1), pero si tienes Docker Desktop con Compose v2, usa `docker compose` (sin guión).

### Setup Inicial

```bash
# 1. Fork y clonar
git clone https://github.com/iorch/cp2ageb.git
cd cp2ageb

# 2. Crear rama
git checkout -b feature/mi-funcionalidad

# 3. Instalar dependencias de desarrollo
pip install -r requirements-test.txt

# 4. Levantar entorno
docker-compose up -d

# 5. Verificar tests
./run_tests.sh
```

## Flujo de Trabajo

### 1. Crear Rama

```bash
# Features
git checkout -b feature/nombre-descriptivo

# Bugfixes
git checkout -b fix/nombre-del-bug

# Documentación
git checkout -b docs/tema
```

### 2. Hacer Cambios

- Escribe código claro y documentado
- Sigue los estándares del proyecto
- Agrega tests para nuevas funcionalidades
- Actualiza documentación si es necesario

### 3. Commit

```bash
# Commits descriptivos en español
git add .
git commit -m "feat: agregar función de exportación de resultados"

# Prefijos recomendados:
# feat: Nueva funcionalidad
# fix: Corrección de bug
# docs: Cambios en documentación
# test: Agregar o modificar tests
# refactor: Refactorización sin cambio funcional
# perf: Mejoras de performance
# chore: Cambios en build, CI, etc.
```

### 4. Push y Pull Request

```bash
# Push a tu fork
git push origin feature/mi-funcionalidad

# Abrir PR en GitHub con:
# - Título descriptivo
# - Descripción de cambios
# - Referencias a issues relacionados
# - Screenshots si aplica
```

## Estándares de Código

### Python

#### Estilo

- **PEP 8** para estilo de código
- **Type hints** para funciones públicas
- **Docstrings** en español para módulos, clases y funciones

```python
def buscar_agebs(codigo_postal: str) -> list[dict]:
    """
    Busca AGEBs para un código postal dado.

    Args:
        codigo_postal: Código postal de 5 dígitos

    Returns:
        Lista de diccionarios con información de AGEBs

    Raises:
        ValueError: Si el código postal es inválido
    """
    pass
```

#### Organización

```python
# 1. Imports estándar
import os
import sys

# 2. Imports de terceros
import psycopg2
from typing import List, Dict

# 3. Imports locales
from scripts.utils import normalize_estado
```

### SQL

#### Estilo

- **Mayúsculas** para keywords SQL
- **snake_case** para nombres de tablas y columnas
- **Comentarios** para queries complejos

```sql
-- Buscar AGEBs con intersección significativa
SELECT
    cp.d_cp AS codigo_postal,
    ageb.cvegeo AS clave_ageb,
    ROUND(
        ST_Area(ST_Intersection(cp.geom, ageb.geom)) /
        ST_Area(cp.geom) * 100,
        2
    ) AS porcentaje
FROM sepomex.cp_14_cp_jal cp
JOIN inegi.ageb_urbana_14 ageb
  ON ST_Intersects(cp.geom, ageb.geom)
WHERE porcentaje > 0.01
ORDER BY porcentaje DESC;
```

### Shell Scripts

- **Bash** con shebang `#!/bin/bash`
- **set -e** para detener en errores
- **Comentarios** descriptivos
- **Variables** en mayúsculas

```bash
#!/bin/bash
set -e

# Constantes
readonly POSTGRES_HOST="localhost"
readonly POSTGRES_PORT=5432

# Funciones con comentarios
function conectar_db() {
    # Conecta a la base de datos PostgreSQL
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U geouser -d cp2ageb
}
```

## Tests

### Ejecutar Tests

```bash
# Todos los tests
./run_tests.sh

# Solo unitarios
./run_tests.sh --unit

# Solo integración
./run_tests.sh --integration

# Con coverage
./run_tests.sh --coverage
```

### Escribir Tests

#### Tests Unitarios

```python
# tests/test_nuevo_modulo.py
import pytest

class TestNuevaFuncionalidad:
    """Tests para nueva funcionalidad"""

    def test_caso_basico(self):
        """Test de caso básico"""
        resultado = mi_funcion("input")
        assert resultado == "expected"

    def test_caso_edge(self):
        """Test de caso límite"""
        with pytest.raises(ValueError):
            mi_funcion("invalid")
```

#### Tests de Integración

```python
@pytest.mark.integration
class TestIntegracionDB:
    """Tests que requieren base de datos"""

    def test_query_funciona(self, db_conn):
        """Verificar query contra BD real"""
        with db_conn.cursor() as cur:
            cur.execute("SELECT * FROM buscar_agebs_por_cp('44100')")
            results = cur.fetchall()
            assert len(results) > 0
```

### Criterios de Aceptación

- ✅ Todos los tests deben pasar
- ✅ Coverage mínimo 80% para código nuevo
- ✅ Agregar tests para bugs corregidos
- ✅ Documentar casos edge en tests

## Documentación

### Actualizar README

Si tu cambio afecta la API pública o configuración:

1. **Actualizar** README.md con ejemplos
2. **Agregar** sección en INSTALL.md si es necesario
3. **Documentar** en CLAUDE.md para Claude Code

### Docstrings

```python
def funcion_compleja(
    param1: str,
    param2: int,
    param3: bool = False
) -> Dict[str, Any]:
    """
    Descripción breve de la función.

    Descripción más detallada si es necesario.
    Explica el propósito y casos de uso.

    Args:
        param1: Descripción del primer parámetro
        param2: Descripción del segundo parámetro
        param3: Parámetro opcional (default: False)

    Returns:
        Diccionario con estructura:
        {
            'key1': valor1,
            'key2': valor2
        }

    Raises:
        ValueError: Si param2 es negativo
        ConnectionError: Si no se puede conectar a BD

    Example:
        >>> resultado = funcion_compleja("test", 42)
        >>> print(resultado['key1'])
        'valor esperado'
    """
    pass
```

### Comentarios en Código

```python
# Buenos comentarios explican POR QUÉ, no QUÉ
# ✅ Bueno
# Transformar a SRID 6372 porque INEGI rural ya usa ese SRID
geom = ST_Transform(geom, 6372)

# ❌ Malo (obvio del código)
# Transformar geometría
geom = ST_Transform(geom, 6372)
```

## Code Review

### Qué Esperamos

Tu PR será revisado considerando:

1. **Funcionalidad**: ¿Resuelve el problema?
2. **Tests**: ¿Hay tests adecuados?
3. **Documentación**: ¿Está documentado?
4. **Estilo**: ¿Sigue los estándares?
5. **Performance**: ¿Es eficiente?
6. **Compatibilidad**: ¿Rompe código existente?

### Responder a Comentarios

- **Respetuoso**: Debate técnico constructivo
- **Claro**: Explica tus decisiones
- **Receptivo**: Acepta sugerencias razonables
- **Oportuno**: Responde en tiempo razonable

## Áreas de Contribución

### Funcionalidades Deseadas

- [ ] API REST para consultas
- [ ] Exportación de resultados (CSV, JSON, GeoJSON)
- [ ] Interfaz web de consulta
- [ ] Caché de resultados
- [ ] Soporte para búsqueda por colonia/localidad
- [ ] Visualización de resultados en mapa

### Mejoras Técnicas

- [ ] Optimización de queries espaciales
- [ ] Paralelización de carga de datos
- [ ] Compresión de geometrías
- [ ] Índices espaciales adicionales
- [ ] Monitoring y métricas

### Documentación

- [ ] Tutoriales paso a paso
- [ ] Videos explicativos
- [ ] Casos de uso reales
- [ ] Guía de performance tuning
- [ ] FAQ

## Comunicación

- **Issues**: Para bugs y features
- **Discussions**: Para preguntas y discusión general
- **Pull Requests**: Para contribuciones de código

## Reconocimiento

Los contribuidores son reconocidos en:

- Lista de contributors en GitHub
- Sección de créditos en README
- Release notes

---

**¿Dudas?** Abre un [issue](https://github.com/iorch/cp2ageb/issues) o participa en [discussions](https://github.com/iorch/cp2ageb/discussions)

**¡Gracias por contribuir!** 🎉
