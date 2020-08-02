FROM ubuntu:16.04

# Uncomment and fill out the following two lines if behind a proxy
#ENV http_proxy=http://proxy.example.com:80
#ENV https_proxy=http://proxy.example.com:80
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        curl \
        build-essential \
        cmake \
        zlib1g-dev \
        libncurses5-dev \
        libgdbm-dev \
        libnss3-dev \
        libssl-dev \
        libreadline-dev \
        libffi-dev \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*


# Install Python 3.8.3
RUN cd /tmp && \
    wget https://www.python.org/ftp/python/3.8.3/Python-3.8.3.tgz --no-check-certificate && \
    tar xvf Python-3.8.3.tgz && \
    cd Python-3.8.3 && \
    ./configure --enable-optimizations && \
    make && \
    make install && \
    cd .. && \
    rm -rf Python-3.8.3 Python-3.8.3.tgz

# Install 3rd party Python packages using pip
RUN if [[ $http_proxy != "" ]]; then \
        pip3 config set global.proxy $http_proxy && \
        pip3 config set global.trusted-host "pypi.org python.pypi.org files.pythonhosted.org"; fi; \
    pip3 install --upgrade pip && \
    pip3 install \
        google-api-python-client \
        oauth2client \
        Pillow \
        billboard.py

RUN mkdir /code
WORKDIR /code
