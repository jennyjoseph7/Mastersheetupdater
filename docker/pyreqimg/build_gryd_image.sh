#!/bin/bash

set -euo pipefail

BRANCH=$1
SERVICE=$2

CONF_DIR="/mnta/autobot_agents/docker/pyreqimg/Conf"
CONFIG_FILE="${CONF_DIR}/${SERVICE}.conf"

if [ -z "$BRANCH" ] || [ -z "$SERVICE" ]; then
    echo "Usage: bash build_gryd_image.sh <branch> <service>"
    exit 1
fi

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

prepare_dockerfile() {

    BASE_IMAGE="asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:${BRANCH}"

    sed \
        -e "s|__BASEIMAGE_TAG__|${BRANCH}|g" \
        -e "s|__REQUIREMENTS_FILE__|${REQUIREMENTS_FILE}|g" \
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
}

main() {
    update_repo
    load_config
    prepare_dockerfile
    build_image
    cleanup
}

main
