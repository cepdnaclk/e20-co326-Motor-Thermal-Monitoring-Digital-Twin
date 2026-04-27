FROM python:3.11-slim

WORKDIR /app

# AI-Ready image: includes full data science stack per lecturer spec
# (paho-mqtt, numpy, pandas, scikit-learn, matplotlib)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the simulated sensor device
# Override in docker-compose with: command: python edge_ai.py
# Or run interactively:  docker exec -it python-edge python edge_ai.py
CMD ["python", "mqtt_publisher.py"]
