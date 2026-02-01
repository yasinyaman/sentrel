# Sentrel Test Uygulaması - Docker Image
FROM python:3.11-slim

WORKDIR /app

# Bağımlılıkları yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY *.py .

# Port (web UI için)
EXPOSE 8080

# Varsayılan komut (CLI modu)
ENTRYPOINT ["python", "error_generator.py"]
CMD ["--help"]
