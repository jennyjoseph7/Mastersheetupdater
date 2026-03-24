FROM ubuntu:22.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -yy
RUN apt install software-properties-common zip unzip python3-pip redis-tools libpq-dev curl jq -yy
RUN apt-get install ffmpeg -yy
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-dev \
    build-essential \
    vim 
RUN pip install pyaudio

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN pip install -U pip setuptools
RUN pip install --ignore-installed -r requirements.txt
RUN pip install --ignore-installed -r spark_requirements.txt
