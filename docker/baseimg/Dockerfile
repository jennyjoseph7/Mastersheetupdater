FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -yy
RUN apt install build-essential software-properties-common zip unzip python3-pip python3.12-venv python3-dev curl libpq-dev jq -yy
RUN apt-get install ffmpeg -yy
RUN apt-get update && apt-get install -y \
    portaudio19-dev 

RUN apt install nodejs npm -yy
RUN npm install -g log.io-file-input

WORKDIR /root/
RUN python3 -m venv pyenv
ENV PYENV_PATH=pyenv

COPY requirements.txt /tmp
COPY spark_requirements.txt /tmp
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN /root/pyenv/bin/pip install -U pip setuptools
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/requirements.txt
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/spark_requirements.txt
