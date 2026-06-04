ARG BASEIMAGE_TAG

FROM asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:${BASEIMAGE_TAG}

WORKDIR /root/

COPY . .

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

RUN /root/pyenv/bin/pip install -U pip setuptools

ARG REQUIREMENTS_FILE

RUN /root/pyenv/bin/pip install --ignore-installed -r ${REQUIREMENTS_FILE}
