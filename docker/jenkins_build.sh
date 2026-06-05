#!/bin/bash

BUILD_CONF_FILE="${BUILD_CONF_FILE:-./build.conf}"

if [ -n "$BUILD_CONF_FILE" ] && [ -f "$BUILD_CONF_FILE" ]; then
    echo "Sourcing $BUILD_CONF_FILE"
    source "$BUILD_CONF_FILE"
fi

DOCKER_BASE_IMG_TAG="${1:-latest}"

# 2nd argument (must match WORKER_NAME)
REPO_NAME="${2:?Repository name is required}"

# =========================
# VALIDATION
# =========================

if [ -z "$WORKER_NAME" ] || [ "$WORKER_NAME" = "0" ]; then
    echo "ERROR: WORKER_NAME not set in build.conf"
    exit 1
fi

if [ "$WORKER_NAME" != "$REPO_NAME" ]; then
    echo "ERROR: WORKER_NAME mismatch"
    echo "build.conf WORKER_NAME = $WORKER_NAME"
    echo "CLI argument (2nd arg) = $REPO_NAME"
    exit 1
fi

# =========================
# CONFIG VARIABLES
# =========================

WORKER_DOCKER_IMAGE_TAG="${WORKER_DOCKER_IMAGE_TAG:-0}"
WORKER_DOCKER_IMAGE_NAME="${WORKER_NAME}:${WORKER_DOCKER_IMAGE_TAG}"

DOCKER_REGISTRY="${DOCKER_REGISTRY:-0}"
PUSH_AS_LATEST="${PUSH_AS_LATEST:-0}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-0}"
GCP_ACCOUNT_ID="${GCP_ACCOUNT_ID:-0}"
REGISTRY_LINK_PREFIX="${REGISTRY_LINK_PREFIX:-0}"
ONLY_PUSH="${ONLY_PUSH:-0}"
PUSH_TO_REGISTRY="${PUSH_TO_REGISTRY:-0}"
BUILD_ENVIRONMENT="${BUILD_ENVIRONMENT:-0}"
GCP_CREDS_DIR="${GCP_CREDS_DIR:-0}"

export GCP_CREDS_PATH=0

WORKING_DIR="$(pwd)"
WORKER_DIR="$(realpath ../)"

dir_status=-1
SHA=0

# =========================
# FUNCTIONS
# =========================

function print_worker_git_info() {

    printf "%-20s %-10s %-18s %-12s %s\n" "WORKER" "SHA" "AUTHOR" "DATE" "MESSAGE"
    echo "-----------------------------------------------------------------------------------------------"

    grep '"name"' start_worker_config.json \
    | sed 's/.*"\(.*\)".*/\1/' \
    | sort -u \
    | while read -r worker; do

        commit=$(git log -1 --date=short --pretty=format:"%H|%an|%ad|%s" -- "$worker")

        [ -z "$commit" ] && continue

        IFS="|" read -r sha author date message <<< "$commit"

        echo "$(git log -1 --pretty=format:"%H - %an, %ad : %s" -- "$worker")" > "$worker/version.sha"

        echo "$date|$worker|$sha|$author|$message"

    done | sort -r | while IFS="|" read -r date worker sha author message; do
        printf "%-20s %-10s %-18s %-12s %s\n" "$worker" "$sha" "$author" "$date" "$message"
    done
}

function validate_directory() {
    local dir_name="$1"
    echo "Validating directory $dir_name"

    dir_status=1
    if [ -d "$dir_name" ]; then
        dir_status=0
    fi
}

function create_sha_file() {
    local dir_name="$1"

    pushd "$dir_name" >/dev/null || exit 1

    sha=$(git log -1 --pretty=format:%h)
    sha_status=$?

    if [ "$sha_status" -ne 0 ]; then
        sha="latest"
    fi

    echo "$sha" > "$(basename "$dir_name").sha"

    gbsha=$(git log -1 --pretty=format:"%H:%aI")
    echo "$gbsha" > version.sha

    SHA="$sha"

    print_worker_git_info

    popd >/dev/null || exit 1
}

function zip_repo() {

    local dir_path="$1"
    local zip_name="$2"

    if [[ ! "$zip_name" =~ \.zip$ ]]; then
        echo "Invalid zip filename"
        exit 1
    fi

    validate_directory "$dir_path"

    if [ "$dir_status" -ne 0 ]; then
        echo "Directory does not exist"
        exit 1
    fi

    if [ "$zip_name" = "0" ]; then
        zip_name="$(basename "$dir_path").zip"
    fi

    create_sha_file "$dir_path"

    pushd "$dir_path" >/dev/null || exit 1

    rm -f "$zip_name"

    zip -r "$zip_name" ./ \
        --exclude='*frontend*' \
        --exclude='*creds*' \
        --exclude='*recordings*' \
        --exclude='*config.sh*' \
        --exclude='*local*' \
        --exclude='*results*' \
        --exclude='*.pid*' \
        --exclude='*stats*' \
        --exclude='*.whl*' \
        --exclude='*.zip*' \
        --exclude='*.log*' \
        --exclude='*.git*' \
        --exclude='*docker*' \
        --exclude='*venv*' \
        --exclude='*pyenv*' \
        --exclude='*logs*' \
        --exclude='*keys*' \
        --exclude='*__pycache__*' \
        --exclude='*.swp'

    cp "$zip_name" "$WORKING_DIR"

    popd >/dev/null || exit 1
}

function build_docker_image() {

    if [ "$WORKER_DOCKER_IMAGE_TAG" = "0" ]; then
        WORKER_DOCKER_IMAGE_TAG="$SHA"
    fi

    WORKER_DOCKER_IMAGE_NAME="${WORKER_NAME}:${WORKER_DOCKER_IMAGE_TAG}"

    if [ "$GCP_CREDS_PATH" != "0" ]; then
        cp -v "$GCP_CREDS_PATH" ./
    fi

    docker build -f Dockerfile.build -t "$WORKER_DOCKER_IMAGE_NAME" .

    if [ $? -ne 0 ]; then
        echo "Build Failed"
        exit 1
    fi
}

function do_registry_authentication() {
    gcloud auth activate-service-account --key-file=/home/ubuntu/firebase.json
}

function push_image_to_registry() {

    if [ "$REGISTRY_LINK_PREFIX" = "0" ]; then
        echo "Invalid registry link prefix"
        exit 1
    fi

    rname="${REGISTRY_LINK_PREFIX}/${WORKER_NAME}"
    imagePushTag="${rname}:${WORKER_DOCKER_IMAGE_TAG}"

    do_registry_authentication

    docker tag "$WORKER_DOCKER_IMAGE_NAME" "$imagePushTag"
    docker push "$imagePushTag"

    build_env_tag="${rname}:${BUILD_ENVIRONMENT}"

    docker tag "$WORKER_DOCKER_IMAGE_NAME" "$build_env_tag"
    docker push "$build_env_tag"

    if [ "$PUSH_AS_LATEST" = "1" ]; then
        docker tag "$imagePushTag" "${rname}:latest"
        docker push "${rname}:latest"
    fi
}

# =========================
# MAIN
# =========================

function main() {

    echo "Creating working Dockerfile..."

    # FIX: support both Dockerfile names
    if [ -f "Dockerfile" ]; then
        cp Dockerfile Dockerfile.wk
    elif [ -f "Dockefile" ]; then
        cp Dockefile Dockerfile.wk
    else
        echo "ERROR: Dockerfile not found"
        exit 1
    fi

    # -------------------------
    # VALIDATION
    # -------------------------

    if [ -z "$BUILD_ENVIRONMENT" ] || [ "$BUILD_ENVIRONMENT" = "0" ]; then
        echo "ERROR: Build environment not set."
        exit 1
    fi

    if [ -z "$WORKER_NAME" ] || [ "$WORKER_NAME" = "0" ]; then
        echo "ERROR: Invalid worker name."
        exit 1
    fi

    # -------------------------
    # GCP CREDS HANDLING
    # -------------------------

    if [ -z "$GCP_CREDS_DIR" ] || [ "$GCP_CREDS_DIR" = "0" ]; then
        echo "WARNING: GCP Creds dir not set."
        export GCP_CREDS_PATH=0
    else
        export GCP_CREDS_PATH="$GCP_CREDS_DIR/$BUILD_ENVIRONMENT/credentials.json"

        if [[ ! -f "$GCP_CREDS_PATH" ]]; then
            echo "WARNING: GCP Creds Not Found at $GCP_CREDS_PATH"
            export GCP_CREDS_PATH=0
        else
            echo "Using GCP creds: $GCP_CREDS_PATH"
        fi
    fi

    # -------------------------
    # PATCH DOCKERFILE
    # -------------------------

    sed -i "s#<PYREQ_IMAGE>#$PYREQ_IMAGE#g" Dockerfile.wk
    sed -i "s#<DOCKER_BASE_IMG_TAG>#$DOCKER_BASE_IMG_TAG#g" Dockerfile.wk

    # -------------------------
    # BUILD
    # -------------------------

    if [ "$ONLY_PUSH" = "0" ]; then

        sed "s#<zipname>#$WORKER_NAME#g" Dockerfile.wk > Dockerfile.build

        zip_repo "$WORKER_DIR" "$WORKER_NAME.zip"

        build_docker_image
    fi

    # -------------------------
    # PUSH
    # -------------------------

    if [ "$PUSH_TO_REGISTRY" = "1" ]; then

        if [ "$DOCKER_REGISTRY" = "0" ]; then
            echo "ERROR: Docker registry not given. Aborting."
            exit 1
        fi

        push_image_to_registry
    fi

    # -------------------------
    # SAVE IMAGE TAG
    # -------------------------

    echo "Saving current image full path..."

    if [ -z "$WORKER_DOCKER_IMAGE_TAG" ] || [ "$WORKER_DOCKER_IMAGE_TAG" = "0" ]; then
        WORKER_DOCKER_IMAGE_TAG="$SHA"
    fi

    FULL_IMAGE_NAME="$REGISTRY_LINK_PREFIX/$WORKER_NAME:$WORKER_DOCKER_IMAGE_TAG"

    echo "$FULL_IMAGE_NAME" > /home/dave/autobot/current_image_tag.txt

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to save image name"
        exit 1
    fi

    echo "Image saved: $FULL_IMAGE_NAME"
}

main
