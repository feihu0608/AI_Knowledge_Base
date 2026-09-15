FROM python:3.12-slim
WORKDIR /app/backend
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY . .
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend/apps/api:/app/backend/apps/worker:/app/backend/packages/domain:/app/backend/packages/application:/app/backend/packages/agent_harness:/app/backend/packages/graphs:/app/backend/packages/providers:/app/backend/packages/retrieval:/app/backend/packages/vector_store:/app/backend/packages/persistence:/app/backend/packages/mcp_gateway:/app/backend/packages/observability:/app/backend/packages/evaluation
EXPOSE 8080
CMD ["uvicorn", "knowledge_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
