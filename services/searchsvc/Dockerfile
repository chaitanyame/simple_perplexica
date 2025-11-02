FROM python:3.11-slim

WORKDIR /app

COPY services/searchsvc/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Download SpaCy English model for NLP-based temporal detection
RUN python -m spacy download en_core_web_sm

COPY services/searchsvc /app

ENV PORT=3001
EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]
