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

prepare_requirements() {

    REQ_FILES=()

    for var in $(compgen -v | grep REQUIREMENTS_SOURCE_); do
        file="${!var}"

        if [ -n "$file" ] && [ -f "$file" ]; then
            cp "$file" .
            REQ_FILES+=("$(basename "$file")")
        fi
    done

    echo "${REQ_FILES[@]}" > .req_files.tmp
}

generate_dockerfile() {

    REQ_RUNS=""

    while read -r req; do
        if [ -n "$req" ]; then
            REQ_RUNS+="RUN /root/pyenv/bin/pip install --ignore-installed -r $req"$'\n'
        fi
    done < .req_files.tmp

    sed \
        -e "s|__BASEIMAGE_TAG__|${BRANCH}|g" \
        -e "s|__REQ_RUNS__|${REQ_RUNS}|g" \
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
    rm -f Dockerfile.tmp .req_files.tmp
    rm -f *_requirements.txt
}

main() {
    update_repo
    prepare_requirements
    generate_dockerfile
    build_image
    cleanup
}

main
