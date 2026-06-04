#!/bin/bash

set -euo pipefail

BRANCH=${1:-master}
SERVICE=${2:-autobot_agents}

update_repo() {
    git fetch origin "$BRANCH"
    git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
    git reset --hard "origin/$BRANCH"
}

prepare_service() {

    if [ "$SERVICE" = "autobot_agents" ]; then

        cp ../../requirements.txt .

        REPO="asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage"

        REQS='COPY requirements.txt /tmp/
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/requirements.txt'

    elif [ "$SERVICE" = "spark" ]; then

        cp ../../spark/requirements.txt spark_requirements.txt

        REPO="asia-south1-docker.pkg.dev/dave-70c8e/spark-pyreq-image/autobot-pyreq-baseimage"

        REQS='COPY spark_requirements.txt /tmp/
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/spark_requirements.txt'

    elif [ "$SERVICE" = "document_processor" ]; then

        cp ../../document_processor/requirment_document_processor.txt document_processor_requirements.txt
        cp ../../brochure_pipeline/requirements.txt brochure_pipeline_requirements.txt

        REPO="asia-south1-docker.pkg.dev/dave-70c8e/document-processor-pyreq-image/autobot-pyreq-baseimage"

        REQS='COPY document_processor_requirements.txt /tmp/
COPY brochure_pipeline_requirements.txt /tmp/
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/document_processor_requirements.txt
RUN /root/pyenv/bin/pip install --ignore-installed -r /tmp/brochure_pipeline_requirements.txt'

    else
        echo "Invalid service: $SERVICE"
        exit 1
    fi
}

generate_dockerfile() {

    cat > Dockerfile.tmp <<EOF
FROM asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:${BRANCH}

WORKDIR /root/

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN /root/pyenv/bin/pip install -U pip setuptools

${REQS}
EOF
}

build_image() {

    docker build \
        -f Dockerfile.tmp \
        -t autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        .

    docker tag \
        autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        ${REPO}:${BRANCH}

    docker push ${REPO}:${BRANCH}
}

main() {
    update_repo
    prepare_service
    generate_dockerfile
    build_image
}

main
