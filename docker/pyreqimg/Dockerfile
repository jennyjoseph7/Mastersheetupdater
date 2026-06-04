FROM asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:__BASEIMAGE_TAG__

WORKDIR /root/

COPY . .

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

RUN /root/pyenv/bin/pip install -U pip setuptools

__PIP_RUNS__
