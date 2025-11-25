FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create the data directory
RUN mkdir -p data

# Define volume location
VOLUME ["/app/data"]

# The command is handled in docker-compose
