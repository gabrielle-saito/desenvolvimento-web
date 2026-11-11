FROM python:3.12-slim

# Sem .pyc no container e logs aparecendo na hora (sem buffer).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copia SÓ o requirements primeiro: se o código mudar mas as dependências não,
# o Docker reaproveita esta camada em cache e o build fica rápido.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
