FROM asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:__BASEIMAGE_TAG__

WORKDIR /root/

COPY . .

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10

RUN /root/pyenv/bin/pip install -U pip setuptools

#RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/requirements.txt
#RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/spark_requirements.txt

RUN /root/pyenv/bin/pip install --upgrade --force-reinstall --no-cache-dir -r /tmp/requirements.txt
RUN /root/pyenv/bin/pip install --upgrade --force-reinstall --no-cache-dir -r /tmp/spark_requirements.txt
