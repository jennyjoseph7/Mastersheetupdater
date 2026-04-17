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

export GCP_CREDS_PATH=0
WORKING_DIR=$(pwd)
WORKER_DIR=$(realpath ../)

dir_status=-1
SHA=0

function validate_directory() {
    dir_name=$1
    echo "Validating directory $1"
    export dir_status=1

    if [ -d $dir_name ];then
        export dir_status=0
    fi
}

function create_sha_file() {
    dir_name=$1

    pushd $dir_name
        sha=`git log -1 --pretty=format:%h`
        if [ $? -ne 0 ];then
            echo "Unable to get SHA assuming latest"
            sha="latest"
        fi

        echo $sha > $(basename $dir_name).sha
        gbsha=`git log -1 --pretty=format:"%H:%aI"`
        echo $gbsha > version.sha
        export SHA=$sha
    popd
}

function zip_repo() {
    dir_path=$1
    zip_name=$2

    if [[ $zip_name =~ \.zip ]];then
        echo "Valid filename"
    else
        echo "Invalid zip filename. Aborting."
        exit 1
    fi

    validate_directory $dir_path

    echo "Zipping the repo."

    if [ $zip_name == 0 ];then
        zip_name="$(basename $dir_path).zip"
    fi

    create_sha_file $dir_path

    pushd $dir_path

        [ -f $zip_name ] && rm -rf $zip_name

        zip -r --exclude=*frontend* --exclude=*creds* --exclude=*recordings* \
        --exclude=*config.sh* --exclude=*local* --exclude=*results* \
        --exclude=*.pid* --exclude=*stats* --exclude=*.whl* \
        --exclude=*.zip* --exclude=*.log* --exclude=*.git* \
        --exclude=*docker* --exclude=*venv* --exclude=*pyenv* \
        --exclude=*logs* --exclude=*keys* --exclude=*__pycache__* \
        --exclude=*py.swp* $zip_name ./

        cp $zip_name $WORKING_DIR
    popd
}

function build_docker_image() {

    if [ $WORKER_DOCKER_IMAGE_TAG == 0 ];then
        WORKER_DOCKER_IMAGE_TAG=$SHA
    fi

    export WORKER_DOCKER_IMAGE_NAME=$WORKER_NAME:$WORKER_DOCKER_IMAGE_TAG

    if [ $GCP_CREDS_PATH != 0 ];then
        cp -v $GCP_CREDS_PATH ./
    fi

    docker build -t $WORKER_DOCKER_IMAGE_NAME .
    if [ $? -ne 0 ];then
        echo "Build Failed."
        exit 1
    else
        echo "Docker build completed."
    fi
}

function do_registry_authentication() {
    echo "Doing auth for $1"
    gcloud auth activate-service-account --key-file=/home/ubuntu/firebase.json
}

function push_image_to_registry() {

    if [ $REGISTRY_LINK_PREFIX == 0 ];then
        echo "Invalid registry link prefix."
        exit 1
    fi

    rname=$REGISTRY_LINK_PREFIX"/"$WORKER_NAME
    imagePushTag=$rname:$WORKER_DOCKER_IMAGE_TAG

    echo "Pushing docker image $imagePushTag"

    do_registry_authentication $DOCKER_REGISTRY

    docker tag $WORKER_DOCKER_IMAGE_NAME $imagePushTag
    docker push $imagePushTag

    build_env_tag=$rname:$BUILD_ENVIRONMENT
    docker tag $WORKER_DOCKER_IMAGE_NAME $build_env_tag
    docker push $build_env_tag

    if [ $PUSH_AS_LATEST == 1 ];then
        docker tag $imagePushTag $rname:latest
        docker push $rname:latest
    fi
}

function main() {

    echo "Creating working dockerfile."
    cat Dockerfile.og > Dockerfile.wk

    if [ $BUILD_ENVIRONMENT == 0 ];then
        echo "Build environment is not set."
        exit 1
    fi

    if [ $GCP_CREDS_DIR != 0 ];then
        export GCP_CREDS_PATH="$GCP_CREDS_DIR/$BUILD_ENVIRONMENT/credentials.json"
    fi

    if [ $WORKER_NAME == 0 ] || [ -z $WORKER_NAME ];then
        echo "Invalid worker name."
        exit 1
    fi

    if [ $ONLY_PUSH == 0 ];then
        sed "s/<zipname>/$WORKER_NAME/g" Dockerfile.wk > Dockerfile
        zip_repo $WORKER_DIR $WORKER_NAME.zip
        build_docker_image
    fi

    if [ $PUSH_TO_REGISTRY == 1 ];then
        push_image_to_registry
    fi

    #taking current image id
    echo "Saving current image full path..."

    if [ $WORKER_DOCKER_IMAGE_TAG == 0 ]; then
        WORKER_DOCKER_IMAGE_TAG=$SHA
    fi

    FULL_IMAGE_NAME="$REGISTRY_LINK_PREFIX/$WORKER_NAME:$WORKER_DOCKER_IMAGE_TAG"

    echo $FULL_IMAGE_NAME > /home/dave/autobot/current_image_tag.txt

    if [ $? -ne 0 ]; then
        echo "Failed to save image name"
        exit 1
    else
        echo "Image saved: $FULL_IMAGE_NAME"
    fi
}

main
