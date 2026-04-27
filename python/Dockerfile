FROM python:3.11-slim

WORKDIR /app

# Install dependencies from explicit requirements file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
