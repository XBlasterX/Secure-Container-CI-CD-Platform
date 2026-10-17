FROM python:3.13-alpine

WORKDIR /app
COPY pyproject.toml ./

COPY src/ ./src/

RUN python -m pip install --no-cache-dir .

RUN python -m pip uninstall -y pip

RUN adduser -D -u 1000 -h /home/simpleuser simpleuser

USER simpleuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]