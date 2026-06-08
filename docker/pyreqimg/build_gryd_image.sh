#!/bin/bash
set -euo pipefail

BRANCH=$1
SERVICE=$2

BASE_DIR="/mnta/autobot_agents/docker/pyreqimg"
CONFIG_FILE="$BASE_DIR/Conf/${SERVICE}.conf"

cd "$BASE_DIR"
source "$CONFIG_FILE"

update_repo() {
    git reset --hard
    git fetch origin "$BRANCH"
    git checkout "$BRANCH" || git checkout -b "$BRANCH" "origin/$BRANCH"
    git pull origin "$BRANCH"
}

generate_dockerfile() {
    # Remove any existing txt files from previous builds
    rm -f "$BASE_DIR"/*.txt

    cp Dockerfile Dockerfile.tmp
    sed -i "s|__BASEIMAGE_TAG__|$BRANCH|g" Dockerfile.tmp

    IFS=',' read -ra files <<< "$REQUIREMENTS_SOURCE"

    for file in "${files[@]}"; do
        filename=$(basename "$file")

        cp "$file" .

        echo "RUN /root/pyenv/bin/pip install --upgrade --force-reinstall --no-cache-dir -r $filename" \
            >> Dockerfile.tmp
    done
}

build_and_push() {
    docker build \
        -f Dockerfile.tmp \
        -t autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        .

    docker tag \
        autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        ${REPO}:${BRANCH}

    docker push ${REPO}:${BRANCH}
}

update_repo
generate_dockerfile
build_and_push
