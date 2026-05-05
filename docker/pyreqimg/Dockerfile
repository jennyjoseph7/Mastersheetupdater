FROM pyreqbaseimg

WORKDIR /root/

COPY requirements.txt /tmp
COPY spark_requirements.txt /tmp
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN /root/pyenv/bin/pip install -U pip setuptools
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/requirements.txt
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/spark_requirements.txt