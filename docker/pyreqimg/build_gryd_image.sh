#!/bin/bash
set -euo pipefail

BRANCH=$1
SERVICE=$2

CONF_DIR="/mnta/autobot_agents/docker/pyreqimg/Conf"
CONFIG_FILE="${CONF_DIR}/${SERVICE}.conf"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config not found: $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

if [ -z "${REQUIREMENTS_SOURCE:-}" ]; then
    echo "REQUIREMENTS_SOURCE is not set in config"
    exit 1
fi

update_repo() {
    git fetch origin "$BRANCH"
    git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
    git pull origin "$BRANCH"
}

generate_dockerfile() {
    IFS=, read -ra items <<< "$REQUIREMENTS_SOURCE"

    # Create clean dockerfile copy
    cp Dockerfile Dockerfile.tmp

    # Replace base image tag
    sed -i "s|__BASEIMAGE_TAG__|${BRANCH}|g" Dockerfile.tmp

    # Remove placeholder line if present
    sed -i "/__REQ_RUNS__/d" Dockerfile.tmp

    # Append pip install layers
    for item in "${items[@]}"; do
        item=$(echo "$item" | xargs)  # trim spaces
        echo "RUN /root/pyenv/bin/pip install -r $item" >> Dockerfile.tmp
    done
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
    rm -f *_requirements.txt || true
}

main() {
    update_repo
    generate_dockerfile
    build_image
    cleanup
}

main
