# Image de base épinglée sur une version mineure (en entreprise : épingler le digest @sha256)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
# setuptools fourni par l'image embarque jaraco.context 5.3.0 (CVE-2026-23949) et
# wheel 0.45.1 (CVE-2026-24049), HIGH avec correctif : 84.0.0 embarque 6.1.0 et 0.46.3.
RUN pip install --no-cache-dir --upgrade setuptools==84.0.0
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN useradd -r -u 10001 appuser
USER appuser
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
