FROM postgis/postgis:16-3.4

# Instalar herramientas necesarias para trabajar con shapefiles
RUN apt-get update && apt-get install -y \
    postgis \
    gdal-bin \
    python3 \
    python3-pip \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip3 install --no-cache-dir \
    psycopg2-binary \
    requests

# Crear directorios para datos y aplicación
RUN mkdir -p /data/cp_shapefiles /data/ageb_shapefiles /scripts /app

# Copiar scripts de descarga a /app
COPY download_shapefiles.py /app/download_shapefiles.py
COPY download_ageb_shapefiles.py /app/download_ageb_shapefiles.py
RUN chmod +x /app/download_shapefiles.py /app/download_ageb_shapefiles.py

# Copiar script de carga a /scripts
COPY scripts/load_shapefiles.py /scripts/load_shapefiles.py
RUN chmod +x /scripts/load_shapefiles.py

# Copiar scripts de inicialización de DB
COPY docker/init-db.sh /docker-entrypoint-initdb.d/10-init-db.sh
RUN chmod +x /docker-entrypoint-initdb.d/10-init-db.sh

# Copiar y configurar entrypoint personalizado
COPY docker/entrypoint.sh /usr/local/bin/custom-entrypoint.sh
RUN chmod +x /usr/local/bin/custom-entrypoint.sh

# Usar entrypoint personalizado
ENTRYPOINT ["/usr/local/bin/custom-entrypoint.sh"]
CMD ["postgres"]

# Exponer puerto de PostgreSQL
EXPOSE 5432
