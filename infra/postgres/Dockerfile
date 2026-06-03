FROM postgres:15

# opcjonalnie: instalacja dodatkowych rzeczy
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# kopiujemy init script
COPY init.sql /docker-entrypoint-initdb.d/