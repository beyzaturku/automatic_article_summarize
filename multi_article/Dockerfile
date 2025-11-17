FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt1-dev \
    libpq-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY main.py .
COPY app.py .
COPY .env . # Ortam değişkeni dosyanızı da kopyalayın (API anahtarı vb.)

EXPOSE 8000
EXPOSE 8501

ENTRYPOINT ["./start.sh"]