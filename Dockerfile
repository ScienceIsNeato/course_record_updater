# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Allow statements and log messages to immediately appear in the Cloud Run logs
ENV PYTHONUNBUFFERED=TRUE

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install production dependencies
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application files (avoid sensitive data)
COPY app.py .
COPY *.py .
COPY templates/ templates/
COPY static/ static/
COPY adapters/ adapters/
COPY session/ session/
COPY api/ api/
COPY bulk_email_models/ bulk_email_models/
COPY email_providers/ email_providers/

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port Gunicorn will run on
EXPOSE 8080

# Use Gunicorn to serve the application
# The timeout is set higher to handle potentially long-running adapter parsing
# Adjust the number of workers (-w) based on expected traffic and instance size
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]
