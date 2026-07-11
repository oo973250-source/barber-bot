FROM python:3.11-slim

WORKDIR /app

# System deps for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create upload directory
RUN mkdir -p uploads

EXPOSE 5000

CMD ["python", "barber.py"]