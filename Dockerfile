FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY run_simulation.py .

# Les connexions (Aiven ou locales) et la clé OpenAI sont passées en variables d'environnement.
# Les certificats Kafka sont montés dans /app/certs (KAFKA_SSL_DIR=certs) ou remplacés par SASL.
EXPOSE 8000
CMD ["python", "-m", "app.main", "--reset"]
