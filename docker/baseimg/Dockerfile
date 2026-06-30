FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -yy
RUN apt install build-essential software-properties-common zip unzip python3-pip python3.12-venv python3-dev curl libpq-dev jq -yy
RUN apt-get install ffmpeg -yy
RUN apt-get update && apt-get install portaudio19-dev -yy

RUN curl https://packages.fluentbit.io/fluentbit.key | gpg --dearmor > /usr/share/keyrings/fluentbit-keyring.gpg && \
	codename=$(grep -oP '(?<=VERSION_CODENAME=).*' /etc/os-release 2>/dev/null || lsb_release -cs 2>/dev/null) && \
	echo "deb [signed-by=/usr/share/keyrings/fluentbit-keyring.gpg] https://packages.fluentbit.io/ubuntu/$codename $codename main" | tee /etc/apt/sources.list.d/fluent-bit.list
RUN apt-get update
RUN apt install -y fluent-bit

WORKDIR /root/
RUN python3 -m venv pyenv
ENV PYENV_PATH=pyenv

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN /root/pyenv/bin/pip install -U pip setuptools google-auth google-cloud-aiplatform google-genai
RUN /root/pyenv/bin/pip install torch
