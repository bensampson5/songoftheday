FROM python:3.8

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install 3rd party Python packages required by songoftheday using pip
WORKDIR /songoftheday
RUN if [ "$http_proxy" != "" ]; then \
        pip config set global.proxy $http_proxy && \
        pip config set global.trusted-host "pypi.org python.pypi.org files.pythonhosted.org"; fi; \
    pip install --upgrade pip && \
    pip install \
        google-api-python-client \
        oauth2client \
        Pillow \
        billboard.py

RUN mkdir /code
WORKDIR /code
