#!/bin/bash

BUILD_CONF_FILE=${BUILD_CONF_FILE:-"./build.conf"}

if [ -z $BUILD_CONF_FILE ];then
    echo "No build conf file given. Assuming parameters are set in environment variables."
else
    echo "Sourcing $BUILD_CONF_FILE"
    source $BUILD_CONF_FILE
fi

WORKER_NAME=${WORKER_NAME:-0}
WORKER_DOCKER_IMAGE_TAG=${WORKER_DOCKER_IMAGE_TAG:-0}
WORKER_DOCKER_IMAGE_NAME=$WORKER_NAME:$WORKER_DOCKER_IMAGE_TAG
DOCKER_REGISTRY=${DOCKER_REGISTRY:-0}
PUSH_AS_LATEST=${PUSH_AS_LATEST:-0}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-0}
GCP_ACCOUNT_ID=${GCP_ACCOUNT_ID:-0}
REGISTRY_LINK_PREFIX=${REGISTRY_LINK_PREFIX:-0}
ONLY_PUSH=${ONLY_PUSH:-0}
PUSH_TO_REGISTRY=${PUSH_TO_REGISTRY:-0}
BUILD_ENVIRONMENT=${BUILD_ENVIRONMENT:-0}
GCP_CREDS_DIR=${GCP_CREDS_DIR:-0}
DOCKER_BASE_IMG_TAG=${DOCKER_BASE_IMG_TAG:-latest}

export GCP_CREDS_PATH=0

WORKING_DIR=$(pwd)

# repo root
WORKER_DIR=$(realpath ../..)

dir_status=-1
SHA=0


function print_worker_git_info() {

    if [ ! -f "$WORKER_DIR/start_worker_config.json" ]; then
        return
    fi

    printf "%-20s %-10s %-18s %-12s %s\n" \
    "WORKER" "SHA" "AUTHOR" "DATE" "MESSAGE"

    echo "---------------------------------------------------------"

    grep '"name"' "$WORKER_DIR/start_worker_config.json" \
    | sed 's/.*"\(.*\)".*/\1/' \
    | sort -u \
    | while read worker; do

        commit=$(git log -1 \
        --date=short \
        --pretty=format:"%H|%an|%ad|%s" \
        -- "$worker")

        [ -z "$commit" ] && continue

        IFS="|" read sha author date message <<< "$commit"

        printf "%-20s %-10s %-18s %-12s %s\n" \
        "$worker" "$sha" "$author" "$date" "$message"

    done
}


function validate_directory() {

    dir_name=$1

    export dir_status=1

    if [ -d "$dir_name" ];then
        export dir_status=0
    fi
}


function create_sha_file() {

    dir_name=$1

    pushd "$dir_name" >/dev/null

    sha=$(git log -1 --pretty=format:%h)

    if [ $? -ne 0 ];then
        sha="latest"
    fi

    echo $sha > version.sha

    export SHA=$sha

    popd >/dev/null
}


function zip_repo() {

    dir_path=$1

    zip_name=$2

    validate_directory "$dir_path"

    if [ $dir_status -ne 0 ];then
        echo "Invalid repo directory"
        exit 1
    fi

    create_sha_file "$dir_path"

    pushd "$dir_path" >/dev/null

    rm -f "$zip_name"

    zip -r \
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
    --exclude=*__pycache__* \
    --exclude=*py.swp* \
    "$zip_name" ./

    cp "$zip_name" "$WORKING_DIR"

    popd >/dev/null
}


function build_docker_image() {

    if [ "$WORKER_DOCKER_IMAGE_TAG" == 0 ];then
        WORKER_DOCKER_IMAGE_TAG=$SHA
    fi

    export WORKER_DOCKER_IMAGE_NAME=$WORKER_NAME:$WORKER_DOCKER_IMAGE_TAG

    if [ "$GCP_CREDS_PATH" != 0 ];then
        cp -v "$GCP_CREDS_PATH" ./
    fi

    # files that exist one level behind docker/app_spark
    cp ../generate_logio_conf.py . 2>/dev/null || true

    docker build \
    -t $WORKER_DOCKER_IMAGE_NAME \
    .

    if [ $? != 0 ];then
        echo "Build Failed"
        exit 1
    fi
}


function do_registry_authentication() {

    gcloud auth activate-service-account \
    --key-file=/home/ubuntu/firebase.json
}


function push_image_to_registry() {

    rname=$REGISTRY_LINK_PREFIX/$WORKER_NAME

    imagePushTag=$rname:$WORKER_DOCKER_IMAGE_TAG

    do_registry_authentication

    docker tag \
    $WORKER_DOCKER_IMAGE_NAME \
    $imagePushTag

    docker push \
    $imagePushTag

    build_env_tag=$rname:$BUILD_ENVIRONMENT

    docker tag \
    $WORKER_DOCKER_IMAGE_NAME \
    $build_env_tag

    docker push \
    $build_env_tag

    if [ $PUSH_AS_LATEST == 1 ];then

        docker tag \
        $WORKER_DOCKER_IMAGE_NAME \
        $rname:latest

        docker push \
        $rname:latest

    fi
}


function main() {

    cp Dockerfile Dockerfile.og

    cat Dockerfile.og > Dockerfile.wk

    sed -i \
    "s/<DOCKER_BASE_IMG_TAG>/$DOCKER_BASE_IMG_TAG/g" \
    Dockerfile.wk

    if [ $ONLY_PUSH == 0 ];then

        sed \
        "s/<zipname>/$WORKER_NAME/g" \
        Dockerfile.wk > Dockerfile

        zip_repo \
        "$WORKER_DIR" \
        "$WORKER_NAME.zip"

        build_docker_image

    fi

    if [ $PUSH_TO_REGISTRY == 1 ];then

        push_image_to_registry

    fi
}

main
