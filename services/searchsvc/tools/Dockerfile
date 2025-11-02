FROM python:3.11-slim

WORKDIR /app

COPY services/searchsvc/tools/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services/searchsvc/tools /app/tools

ENV API_BASE_URL=http://localhost:3001
EXPOSE 8501

CMD ["streamlit", "run", "tools/streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
