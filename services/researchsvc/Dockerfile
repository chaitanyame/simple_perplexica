FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY services/researchsvc/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/researchsvc /app

# Expose port
EXPOSE 3002

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3002"]
