# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy source code and SQL
COPY ./src /app/src
COPY ./sql /app/sql
COPY requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Set environment variables for Airflow (if needed)
ENV AIRFLOW_HOME=/app/airflow

# Default command (change as needed)
CMD ["python", "src/generate_data.py"] 