#!/bin/bash
BUILD_CONF_FILE=${BUILD_CONF_FILE:-"./build.conf"}

if [ -z $BUILD_CONF_FILE ];then
    echo "No build conf file given. Assuming parameters are set in environment variables."
else
    echo "Sourcing $BUILD_CONF_FILE"
    source $BUILD_CONF_FILE
    # printenv
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
create_sha_status=-1
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
	    sha_status=$?

	    if [ $sha_status -ne 0 ];then
	    	echo "Unable to get SHA assuming latest"
	    	sha="latest"
	    fi

	    echo $sha > $(basename $dir_path).sha
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
        echo "Invalid zip filenmae given. Aborting."
        exit 1
    fi

    validate_directory $dir_path

    if [ $dir_status -eq 0 ];then
        echo "$dir_path exists."
    else
        echo "$dir_path does not exists."
    fi

    echo "Zipping the repo."
    
    if [ $zip_name == 0 ];then
        zip_name="$(basename $dir_path).zip"
    fi
    
    create_sha_file $dir_path

    pushd $dir_path

        if [ -f $zip_name ];then
	        rm -rf $zip_name  
        fi

	    zip -r --exclude=*frontend* --exclude=*creds* --exclude=*recordings* --exclude=*config.sh* --exclude=*local* --exclude=*results* --exclude=*.pid* --exclude=*stats* --exclude=*.whl* --exclude=*.zip* --exclude=*.log* --exclude=*.git* --exclude=*docker* --exclude=*venv* --exclude=*pyenv* --exclude=*logs* --exclude=*keys* --exclude=*__pycache__* --exclude=*py.swp* $zip_name ./
    
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
    image_build_status=$?

    if [ "$image_build_status" != 0 ];then
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

function checkout_sha() {
    dir_path=$1
    sha=$2

    echo "Checking out $dir_path to SHA $sha"
    pushd $dir_path
        git fetch --all
        git checkout $sha
        if [ $? -ne 0 ]; then
            echo "Failed to checkout $sha in $dir_path. Aborting."
            exit 1
        fi
    popd
}

function push_image_to_registry() {

    if [ $REGISTRY_LINK_PREFIX == 0 ];then
        echo "Invalid registry link prefix."
        exit 1
    fi

	rname=$REGISTRY_LINK_PREFIX"/"$WORKER_NAME
	imagePushTag=$rname:$WORKER_DOCKER_IMAGE_TAG
	echo "Pushing the docker image $imagePushTag, to $DOCKER_REGISTRY"

    do_registry_authentication $DOCKER_REGISTRY

    echo "Tagging $WORKER_DOCKER_IMAGE_NAME as $imagePushTag."
	docker tag $WORKER_DOCKER_IMAGE_NAME $imagePushTag
	docker push $imagePushTag

    if [ $PUSH_AS_LATEST == 1 ];then
        echo "Adding latest tag to this image and pushing."
	    docker tag $imagePushTag $rname:latest
	    docker push $rname:latest
    fi

}

function main() {
    echo "Creting working dockerfile."
    cat Dockerfile.og > Dockerfile.wk

    if [ $BUILD_ENVIRONMENT == 0 ];then
        echo "Build environment is not set."
        exit 1
    fi

    if [ $GCP_CREDS_DIR == 0 ];then
	    echo "GCP Creds dir not set."
    else
    	export GCP_CREDS_PATH="$GCP_CREDS_DIR/$BUILD_ENVIRONMENT/credentials.json"
    	if [[ ! -f $GCP_CREDS_PATH ]];then
    	    echo "GCP Creds Not Found in $GCP_CREDS_PATH."
    	fi
    fi

    if [ $WORKER_NAME == 0 ];then
        echo "Invalid worker name."
        exit 1
    elif [ -z $WORKER_NAME ];then
        echo "Worker name is empty."
        exit 1
    fi
	
    if [ $ONLY_PUSH == 0 ];then
	echo "Patching zipname."
    	sed "s/<zipname>/$WORKER_NAME/g" Dockerfile.wk > Dockerfile
        zip_repo $WORKER_DIR $WORKER_NAME.zip
        build_docker_image
    fi

    if [ $PUSH_TO_REGISTRY == 1 ];then

        if [ $DOCKER_REGISTRY == 0 ];then
            echo "Docker registry not given. Aborting."
            exit 1
        fi

        push_image_to_registry
    fi
}

main
