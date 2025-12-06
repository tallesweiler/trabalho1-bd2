FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Mantém o container rodando para você entrar nele e executar o script
CMD ["tail", "-f", "/dev/null"]