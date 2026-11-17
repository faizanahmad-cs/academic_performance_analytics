FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Initialize and seed database if not exists
RUN python -c "from backend.app.seed_data import seed_database; seed_database()"

# Expose Streamlit default port and FastAPI port
EXPOSE 8501 8000

# Start both services
CMD ["python", "run_system.py"]
