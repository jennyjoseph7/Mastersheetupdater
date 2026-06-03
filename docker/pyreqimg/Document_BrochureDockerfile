FROM asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:<baseimage_tag>

WORKDIR /root/

COPY document_processor_requirements.txt /tmp
COPY brochure_pipeline_requirements.txt /tmp

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN /root/pyenv/bin/pip install -U pip setuptools
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/document_processor_requirements.txt
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/brochure_pipeline_requirements.txt
