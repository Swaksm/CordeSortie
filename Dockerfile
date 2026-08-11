FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

COPY cordesortie ./cordesortie

# DATA_DIR doit pointer vers un volume persistant en prod (Render Disk) —
# voir docs/ARCHITECTURE.md §6. Le disque est monté par Render via la config
# du service, pas ici dans l'image.
ENV DATA_DIR=/data

CMD ["python", "-m", "cordesortie"]
