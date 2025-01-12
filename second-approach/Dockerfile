# Use a lightweight Python base image
FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Copy requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port 5000 (Flask default)
EXPOSE 5000

# Run the app via main.py
CMD ["python", "-m", "app.main"]

