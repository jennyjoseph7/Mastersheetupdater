#!/bin/bash
set -euo pipefail

BRANCH=$1
SERVICE=$2

BASE_DIR="/mnta/autobot_agents/docker/pyreqimg"
CONF_DIR="$BASE_DIR/Conf"
CONFIG_FILE="${CONF_DIR}/${SERVICE}.conf"

cd "$BASE_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config not found: $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

if [ -z "${REQUIREMENTS_SOURCE:-}" ]; then
    echo "REQUIREMENTS_SOURCE is not set"
    exit 1
fi

update_repo() {
    git fetch origin "$BRANCH"
    git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
    git pull origin "$BRANCH"
}

generate_dockerfile_and_context() {
    cp Dockerfile Dockerfile.tmp
    sed -i "s|__BASEIMAGE_TAG__|${BRANCH}|g" Dockerfile.tmp

    IFS=, read -ra items <<< "$REQUIREMENTS_SOURCE"

    for item in "${items[@]}"; do
        item=$(echo "$item" | xargs)

        # HOST PATH (works on your machine)
        if [ ! -f "$item" ]; then
            echo "Missing file on host: $item"
            exit 1
        fi

        filename=$(basename "$item")

        # COPY INTO BUILD CONTEXT
        cp "$item" "$BASE_DIR/$filename"

        # USE RELATIVE PATH INSIDE DOCKER
	echo "RUN /root/pyenv/bin/pip install --upgrade --force-reinstall --no-cache-dir -r $filename" >> Dockerfile.tmp
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

    # remove copied requirement files only
    IFS=, read -ra items <<< "$REQUIREMENTS_SOURCE"
    for item in "${items[@]}"; do
        filename=$(basename "$item")
        rm -f "$BASE_DIR/$filename"
    done
}

main() {
    update_repo
    generate_dockerfile_and_context
    build_image
    cleanup
}

main
