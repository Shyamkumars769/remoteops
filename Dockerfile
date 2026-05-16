FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent ./agent
COPY cli ./cli
COPY server ./server
COPY web ./web
COPY docs ./docs

RUN mkdir -p /app/db /app/logs

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
