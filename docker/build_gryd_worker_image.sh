#!/bin/bash
set -euo pipefail

# -----------------------------
# CONFIG
# -----------------------------
BUILD_CONF_FILE=${BUILD_CONF_FILE:-"./build.conf"}
DOCKERFILE=${DOCKERFILE:-Dockerfile.og}
DOCKER_BASE_IMG_TAG=${DOCKER_BASE_IMG_TAG:-latest}

WORKING_DIR=$(pwd)
WORKER_DIR=$(realpath ../)

dir_status=-1
SHA=0

# -----------------------------
# LOAD CONFIG
# -----------------------------
if [ -n "$BUILD_CONF_FILE" ] && [ -f "$BUILD_CONF_FILE" ]; then
    echo "Sourcing $BUILD_CONF_FILE"
    source "$BUILD_CONF_FILE"
fi

# -----------------------------
# VARIABLES
# -----------------------------
WORKER_NAME=${WORKER_NAME:-0}
WORKER_DOCKER_IMAGE_TAG=${WORKER_DOCKER_IMAGE_TAG:-0}
DOCKER_REGISTRY=${DOCKER_REGISTRY:-0}
PUSH_AS_LATEST=${PUSH_AS_LATEST:-0}
REGISTRY_LINK_PREFIX=${REGISTRY_LINK_PREFIX:-0}
ONLY_PUSH=${ONLY_PUSH:-0}
PUSH_TO_REGISTRY=${PUSH_TO_REGISTRY:-0}
BUILD_ENVIRONMENT=${BUILD_ENVIRONMENT:-0}
GCP_CREDS_DIR=${GCP_CREDS_DIR:-0}

WORKER_DOCKER_IMAGE_NAME=$WORKER_NAME:$WORKER_DOCKER_IMAGE_TAG

# -----------------------------
# VALIDATE DIR
# -----------------------------
function validate_directory() {
    local dir_name=$1
    echo "Validating directory $dir_name"
    export dir_status=1

    if [ -d "$dir_name" ]; then
        export dir_status=0
    fi
}

# -----------------------------
# CREATE SHA
# -----------------------------
function create_sha_file() {
    local dir_name=$1

    pushd "$dir_name" >/dev/null

        sha=$(git log -1 --pretty=format:%h || echo "latest")
        echo "$sha" > "$(basename "$dir_name").sha"

        gbsha=$(git log -1 --pretty=format:"%H:%aI" || echo "latest")
        echo "$gbsha" > version.sha

        export SHA=$sha

    popd >/dev/null
}

# -----------------------------
# ZIP REPO
# -----------------------------
function zip_repo() {
    local dir_path=$1
    local zip_name=$2

    validate_directory "$dir_path"

    create_sha_file "$dir_path"

    pushd "$dir_path" >/dev/null

        rm -f "$zip_name"

        echo "Creating zip: $zip_name"

        zip -r "$zip_name" ./ \
        --exclude=*frontend* \
        --exclude=*creds* \
        --exclude=*recordings* \
        --exclude=*config.sh* \
        --exclude=*local* \
        --exclude=*results* \
        --exclude=*.pid* \
        --exclude=*stats* \
        --exclude=*.whl* \
        --exclude=*.zip* \
        --exclude=*.log* \
        --exclude=*.git* \
        --exclude=*docker* \
        --exclude=*venv* \
        --exclude=*pyenv* \
        --exclude=*logs* \
        --exclude=*keys* \
        --exclude=*__pycache__*

        cp "$zip_name" "$WORKING_DIR"

    popd >/dev/null
}

# -----------------------------
# BUILD DOCKER IMAGE
# -----------------------------
function build_docker_image() {

    if [ "$WORKER_DOCKER_IMAGE_TAG" == "0" ]; then
        WORKER_DOCKER_IMAGE_TAG=$SHA
    fi

    WORKER_DOCKER_IMAGE_NAME=$WORKER_NAME:$WORKER_DOCKER_IMAGE_TAG

    echo "Building Docker image: $WORKER_DOCKER_IMAGE_NAME"

    docker build -f Dockerfile.wk -t "$WORKER_DOCKER_IMAGE_NAME" .

    echo "Docker build completed."
}

# -----------------------------
# PUSH IMAGE
# -----------------------------
function push_image_to_registry() {

    local rname=$REGISTRY_LINK_PREFIX"/"$WORKER_NAME
    local imagePushTag=$rname:$WORKER_DOCKER_IMAGE_TAG

    echo "Pushing image: $imagePushTag"

    docker tag "$WORKER_DOCKER_IMAGE_NAME" "$imagePushTag"
    docker push "$imagePushTag"

    if [ "$PUSH_AS_LATEST" == "1" ]; then
        docker tag "$imagePushTag" "$rname:latest"
        docker push "$rname:latest"
    fi
}

# -----------------------------
# MAIN
# -----------------------------
function main() {

    echo "Using Dockerfile: $DOCKERFILE"

    cp "$DOCKERFILE" Dockerfile.wk

    echo "Patching base image tag..."
    sed -i "s/<DOCKER_BASE_IMG_TAG>/$DOCKER_BASE_IMG_TAG/g" Dockerfile.wk

    echo "Patching zip name..."
    sed -i "s/<zipname>/$WORKER_NAME/g" Dockerfile.wk

    if [ "$ONLY_PUSH" == "0" ]; then
        zip_repo "$WORKER_DIR" "$WORKER_NAME.zip"
        build_docker_image
    fi

    if [ "$PUSH_TO_REGISTRY" == "1" ]; then
        push_image_to_registry
    fi
}

main
