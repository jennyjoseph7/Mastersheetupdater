FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -yy
RUN apt install build-essential software-properties-common zip unzip python3-pip python3.12-venv python3-dev curl libpq-dev jq -yy
RUN apt-get install ffmpeg -yy
RUN apt-get update && apt-get install portaudio19-dev nodejs npm -yy
RUN npm install -g log.io-file-input
#ADD https://astral.sh/uv/install.sh /uv-installer.sh
#RUN sh /uv-installer.sh && rm /uv-installer.sh
#ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /root/
RUN python3 -m venv pyenv
ENV PYENV_PATH=pyenv

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN /root/pyenv/bin/pip install -U pip setuptools google-auth google-cloud-aiplatform google-genai
RUN /root/pyenv/bin/pip install torch
