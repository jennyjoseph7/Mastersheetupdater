#!/bin/bash

BUILD_CONF_FILE="${BUILD_CONF_FILE:-./build.conf}"

if [ -n "$BUILD_CONF_FILE" ] && [ -f "$BUILD_CONF_FILE" ]; then
    echo "Sourcing $BUILD_CONF_FILE"
    source "$BUILD_CONF_FILE"
fi

DOCKER_BASE_IMG_TAG="${1:-latest}"

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

create_previous_image_backup() {
    local file="/home/dave/autobot/current_image_tag.txt"
    if [ -f "$file" ]; then
        cp "$file" /home/dave/autobot/previous_image.txt
    fi
}

print_worker_git_info() {

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

validate_directory() {
    local dir_name="$1"
    echo "Validating directory $dir_name"

    dir_status=1
    if [ -d "$dir_name" ]; then
        dir_status=0
    fi
}

create_sha_file() {
    local dir_name="$1"

    pushd "$dir_name" >/dev/null || exit 1

    sha=$(git log -1 --pretty=format:%h || echo "latest")

    echo "$sha" > "$(basename "$dir_name").sha"

    gbsha=$(git log -1 --pretty=format:"%H:%aI" || echo "latest")
    echo "$gbsha" > version.sha

    SHA="$sha"

    popd >/dev/null || exit 1
}

zip_repo() {

    local dir_path="$1"
    local zip_name="$2"

    validate_directory "$dir_path"

    if [ "$dir_status" -ne 0 ]; then
        echo "Directory does not exist"
        exit 1
    fi

    create_sha_file "$dir_path"

    pushd "$dir_path" >/dev/null || exit 1

    rm -f "$zip_name"

    zip -r "$zip_name" ./ \
        --exclude='*frontend*' \
        --exclude='*creds*' \
        --exclude='*recordings*' \
        --exclude='*.zip*' \
        --exclude='*.git*' \
        --exclude='*venv*' \
        --exclude='*__pycache__*'

    cp "$zip_name" "$WORKING_DIR"

    popd >/dev/null || exit 1
}

build_docker_image() {

    if [ "$WORKER_DOCKER_IMAGE_TAG" = "0" ]; then
        WORKER_DOCKER_IMAGE_TAG="$SHA"
    fi

    WORKER_DOCKER_IMAGE_NAME="${WORKER_NAME}:${WORKER_DOCKER_IMAGE_TAG}"

    if [ "$GCP_CREDS_PATH" != "0" ]; then
        cp -v "$GCP_CREDS_PATH" ./ || true
    fi

    # =========================
    # FIX: SAFE Dockerfile generation
    # =========================

    if [ ! -f Dockerfile.wk ]; then
        echo "ERROR: Dockerfile.wk missing"
        exit 1
    fi

    if [ ! -s Dockerfile.wk ]; then
        echo "ERROR: Dockerfile.wk is empty"
        exit 1
    fi

    sed "s#<zipname>#${WORKER_NAME}#g" Dockerfile.wk > Dockerfile.build

    if [ ! -s Dockerfile.build ]; then
        echo "ERROR: Dockerfile.build is empty (sed failed)"
        exit 1
    fi

    docker build \
        --no-cache \
        -f Dockerfile.build \
        -t "$WORKER_DOCKER_IMAGE_NAME" .
}

do_registry_authentication() {
    gcloud auth activate-service-account --key-file=/home/ubuntu/firebase.json
}

push_image_to_registry() {

    rname="${REGISTRY_LINK_PREFIX}/${WORKER_NAME}"
    imagePushTag="${rname}:${WORKER_DOCKER_IMAGE_TAG}"

    do_registry_authentication

    docker tag "$WORKER_DOCKER_IMAGE_NAME" "$imagePushTag"
    docker push "$imagePushTag"

    docker tag "$WORKER_DOCKER_IMAGE_NAME" "${rname}:${BUILD_ENVIRONMENT}"
    docker push "${rname}:${BUILD_ENVIRONMENT}"

    if [ "$PUSH_AS_LATEST" = "1" ]; then
        docker tag "$imagePushTag" "${rname}:latest"
        docker push "${rname}:latest"
    fi
}

# =========================
# MAIN
# =========================

main() {

    cp -f Dockerfile Dockerfile.wk

    sed -i "s#<PYREQ_IMAGE>#$PYREQ_IMAGE#g" Dockerfile.wk
    sed -i "s#<DOCKER_BASE_IMG_TAG>#$DOCKER_BASE_IMG_TAG#g" Dockerfile.wk

    if [ "$BUILD_ENVIRONMENT" = "0" ]; then
        echo "Build environment not set"
        exit 1
    fi

    if [ "$ONLY_PUSH" = "0" ]; then
        zip_repo "$WORKER_DIR" "$WORKER_NAME.zip"
        build_docker_image
    fi

    if [ "$PUSH_TO_REGISTRY" = "1" ]; then
        push_image_to_registry
    fi

    # =========================
    # IMAGE TRACKING FIXED
    # =========================

    echo "Saving current image full path..."

    create_previous_image_backup

    if [ -z "$WORKER_DOCKER_IMAGE_TAG" ] || [ "$WORKER_DOCKER_IMAGE_TAG" = "0" ]; then
        WORKER_DOCKER_IMAGE_TAG="$SHA"
    fi

    FULL_IMAGE_NAME="${REGISTRY_LINK_PREFIX}/${WORKER_NAME}:${WORKER_DOCKER_IMAGE_TAG}"

    echo "$FULL_IMAGE_NAME" > /home/dave/autobot/current_image_tag.txt

    echo "Image saved: $FULL_IMAGE_NAME"
}

main
