# Use a lightweight Python base image
FROM python:3.10-slim

# Set workdir
WORKDIR /app

# Copy app code
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["gunicorn", "--worker-class", "eventlet", "--bind", "0.0.0.0:5000", "app.main:app"]
