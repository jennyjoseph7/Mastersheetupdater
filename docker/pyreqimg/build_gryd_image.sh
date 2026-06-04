#!/bin/bash

set -euo pipefail

BRANCH=$1
SERVICE=$2

CONF_DIR="/mnta/autobot_agents/docker/pyreqimg/Conf"
CONFIG_FILE=${CONFIG:-${CONF_DIR}/${SERVICE}.conf}

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

build_image() {
    docker build \
        --build-arg BASEIMAGE_TAG="${BRANCH}" \
        --build-arg REQUIREMENTS_FILE="${REQUIREMENTS_FILE}" \
        -f Dockerfile \
        -t autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        .

    docker tag \
        autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        ${REPO}:${BRANCH}

    docker push ${REPO}:${BRANCH}
}

main() {
    update_repo
    load_config
    build_image
}

main
