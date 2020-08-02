FROM python:3.8

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Clone songoftheday repo from GitHub
RUN git clone https://github.com/bensampson5/songoftheday.git

# Install 3rd party Python packages required by songoftheday using pip
RUN if [ "$http_proxy" != "" ]; then \
        pip config set global.proxy $http_proxy && \
        pip config set global.trusted-host "pypi.org python.pypi.org files.pythonhosted.org"; fi; \
    pip install --upgrade pip && \
    cd songoftheday
# pip install -r requirements.txt

RUN mkdir /code
WORKDIR /code
