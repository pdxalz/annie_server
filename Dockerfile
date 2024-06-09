# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10-slim

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Install nano
RUN apt-get update && apt-get install -y nano

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 1000 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

ENV SERVER_URL=http://192.168.68.113:8000

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "main:app"]
CMD sed -i 's|__SERVER_URL__|'"$SERVER_URL"'|g' ./web_assets/index.html && \
    sed -i 's|__SERVER_URL__|'"$SERVER_URL"'|g' ./web_assets/common.js && \
    exec gunicorn --bind 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker main:app