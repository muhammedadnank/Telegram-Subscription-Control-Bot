# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables to optimize Python execution in containers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/bot

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (build-essential helps compile native extensions if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run the bot application
CMD ["python", "bot/bot.py"]
