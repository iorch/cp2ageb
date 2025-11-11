#!/usr/bin/env python3
"""
Configuración de pytest y fixtures compartidos
"""

import pytest
import psycopg2
import os
from pathlib import Path


def pytest_configure(config):
    """Configuración de pytest al inicio"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require database connection"
    )


@pytest.fixture(scope="session")
def docker_available():
    """Verificar si Docker está disponible y el contenedor está corriendo"""
    import subprocess
    try:
        result = subprocess.run(
            ['docker-compose', 'ps'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return 'cp2ageb-postgis' in result.stdout and 'Up' in result.stdout
    except Exception:
        return False


@pytest.fixture(scope="session")
def database_available(docker_available):
    """Verificar si la base de datos está disponible"""
    if not docker_available:
        pytest.skip("Docker container not running")

    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'cp2ageb'),
            user=os.getenv('POSTGRES_USER', 'geouser'),
            password=os.getenv('POSTGRES_PASSWORD', 'geopassword'),
            connect_timeout=3
        )
        conn.close()
        return True
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.fixture(scope="session")
def test_config():
    """Configuración de tests"""
    return {
        'postgres_host': os.getenv('POSTGRES_HOST', 'localhost'),
        'postgres_port': os.getenv('POSTGRES_PORT', '5432'),
        'postgres_db': os.getenv('POSTGRES_DB', 'cp2ageb'),
        'postgres_user': os.getenv('POSTGRES_USER', 'geouser'),
        'postgres_password': os.getenv('POSTGRES_PASSWORD', 'geopassword'),
        'test_cps': ['44100', '11560', '50000', '64000'],  # Jal, CDMX, Edo Mex, NL
        'test_estados': ['14', '15', '09', '19'],  # Jal, Edo Mex, CDMX, NL
    }


@pytest.fixture
def sample_cp():
    """Código postal de ejemplo para tests"""
    return '44100'  # Guadalajara, Jalisco


def pytest_collection_modifyitems(config, items):
    """Modificar items de la colección para agregar markers automáticamente"""
    for item in items:
        # Marcar tests de base de datos
        if "db_conn" in item.fixturenames or "database_available" in item.fixturenames:
            item.add_marker(pytest.mark.database)

        # Marcar tests de integración
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Marcar tests unitarios
        if "test_scripts" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Marcar tests lentos
        if any(keyword in item.name for keyword in ['performance', 'multiple', 'slow']):
            item.add_marker(pytest.mark.slow)
