#!/bin/bash

set -euo pipefail

BRANCH=$1
SERVICE=$2

if [ -z "$BRANCH" ] || [ -z "$SERVICE" ]; then
    echo "Usage: bash build_gryd_image.sh <branch> <service>"
    exit 1
fi

CONF_DIR="/mnta/autobot_agents/docker/pyreqimg/Conf"
CONFIG_FILE="${CONF_DIR}/${SERVICE}.conf"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config not found: $CONFIG_FILE"
    exit 1
fi

update_repo() {
    git fetch origin "$BRANCH"
    git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
    git pull origin "$BRANCH"
}

load_config() {
    source "$CONFIG_FILE"
}

prepare_requirements() {

    if [ "$SERVICE" == "spark" ]; then
        cp ../../spark/requirements.txt spark_requirements.txt

    elif [ "$SERVICE" == "autobot_agents" ]; then
        cp ../../requirements.txt requirements.txt

    elif [ "$SERVICE" == "document_processor" ]; then
        cp ../../document_processor/requirment_document_processor.txt document_processor_requirements.txt
        cp ../../brochure_pipeline/requirements.txt brochure_pipeline_requirements.txt
    fi
}

prepare_dockerfile() {

    sed \
        -e "s|__BASEIMAGE_TAG__|${BRANCH}|g" \
        -e "s|__REQ1__|${REQUIREMENTS_FILE_1}|g" \
        -e "s|__REQ2__|${REQUIREMENTS_FILE_2}|g" \
        Dockerfile > Dockerfile.tmp
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

cleanup() {
    rm -f Dockerfile.tmp
    rm -f spark_requirements.txt requirements.txt document_processor_requirements.txt brochure_pipeline_requirements.txt
}

main() {
    update_repo
    load_config
    prepare_requirements
    prepare_dockerfile
    build_image
    cleanup
}

main
