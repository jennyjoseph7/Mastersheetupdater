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

update_repo() {
    git fetch origin "$BRANCH"
    git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
    git pull origin "$BRANCH"
}

generate_dockerfile() {
    cp Dockerfile Dockerfile.tmp
    sed -i "s|__BASEIMAGE_TAG__|${BRANCH}|g" Dockerfile.tmp

    IFS=, read -ra items <<< "$REQUIREMENTS_SOURCE"

    for item in "${items[@]}"; do
        item=$(echo "$item" | xargs)

        item=${item#../../}

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
}

main() {
    update_repo
    generate_dockerfile
    build_image
    cleanup
}

main
