# Use the official Microsoft Playwright Python base image
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a volume mount point for the database to persist leads
VOLUME ["/app/data"]

# Copy application files
COPY . .

# Run the main execution loop
CMD ["python", "main.py"]
