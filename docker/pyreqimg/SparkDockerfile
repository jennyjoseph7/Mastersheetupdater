FROM asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:<baseimage_tag>

WORKDIR /root/

COPY spark_requirements.txt /tmp
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN /root/pyenv/bin/pip install -U pip setuptools
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/spark_requirements.txt

