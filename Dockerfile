# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the Cloud Run logs
ENV PYTHONUNBUFFERED=TRUE

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install production dependencies
# Use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port Gunicorn will run on
EXPOSE 8080

# Use Gunicorn to serve the application
# The timeout is set higher to handle potentially long-running adapter parsing
# Adjust the number of workers (-w) based on expected traffic and instance size
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"] 