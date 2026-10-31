FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home biolens
COPY biolens_cloud ./biolens_cloud
COPY biolens ./biolens
USER 10001
ENV BIOLENS_CLOUD_DATA=/data PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["uvicorn","biolens_cloud.api:app","--host","0.0.0.0","--port","8765","--workers","1","--no-access-log"]
