# NOTE : ce Dockerfile installe seulement les dépendances actuelles du bot
# (discord.py, pydantic, python-dotenv). Quand la Phase 4 (scraper Playwright,
# voir docs/TASKS.md) sera codée, il faudra ajouter :
#   RUN playwright install --with-deps chromium
# après l'installation des paquets Python, pour que Chromium et ses
# dépendances système soient présents dans l'image.

FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cordesortie ./cordesortie

# DATA_DIR doit pointer vers un volume persistant en prod (Render Disk) —
# voir docs/ARCHITECTURE.md §6. Le disque est monté par Render via la config
# du service, pas ici dans l'image.
ENV DATA_DIR=/data

CMD ["python", "-m", "cordesortie"]
