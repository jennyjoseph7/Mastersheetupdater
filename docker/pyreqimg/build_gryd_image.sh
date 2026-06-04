#!/bin/bash

set -euo pipefail

BRANCH=$1
SERVICE=$2

CONF_DIR="/mnta/autobot_agents/docker/pyreqimg/Conf"
CONFIG_FILE="${CONF_DIR}/${SERVICE}.conf"

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

generate_req_runs_file() {

    > req_runs.txt

    while read -r req; do
        if [ -n "$req" ]; then
            echo "RUN /root/pyenv/bin/pip install --ignore-installed -r $req" >> req_runs.txt
        fi
    done < .req_files.tmp
}

generate_dockerfile() {

    # replace simple variables only
    sed \
        -e "s|__BASEIMAGE_TAG__|${BRANCH}|g" \
        Dockerfile > Dockerfile.tmp

    # append REQ RUNS safely (NO sed)
    awk '
        /__REQ_RUNS__/ {
            while ((getline line < "req_runs.txt") > 0)
                print line
            next
        }
        { print }
    ' Dockerfile.tmp > Dockerfile.final
}

build_image() {

    docker build \
        -f Dockerfile.final \
        -t autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        .

    docker tag \
        autobot-pyreq-baseimage:${SERVICE}-${BRANCH} \
        ${REPO}:${BRANCH}

    docker push ${REPO}:${BRANCH}
}

cleanup() {
    rm -f Dockerfile.tmp Dockerfile.final .req_files.tmp req_runs.txt
    rm -f *_requirements.txt
}

main() {
    update_repo
    prepare_requirements
    generate_req_runs_file
    generate_dockerfile
    build_image
    cleanup
}

main
