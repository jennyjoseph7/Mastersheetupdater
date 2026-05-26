#!/bin/bash

export pull_success=0

export BRANCH=${1:-"master"}
export APP_NAME=${2:-"spark"}

export BASE_IMAGE_TAG=$BRANCH

export TAG1=$APP_NAME
export TAG2=$BRANCH

function update_repo() {

        branch=$1

        git fetch origin $branch
        git checkout $branch || git checkout -b $branch origin/$branch

        git reset --hard origin/$branch

        if [ $? != 0 ]; then
                echo "Pull branch $branch failed."
                pull_success=0
                return
        fi

        pull_success=1
}

function main() {

        update_repo $BRANCH

        if [ $pull_success == 0 ]; then
                return
        fi

        cp ../../../spark/requirements.txt ./spark_requirements.txt

        cp Dockerfile Dockerfile.tmp
        sed -i "s/<baseimage_tag>/$BASE_IMAGE_TAG/g" Dockerfile.tmp

        docker build -t autobot_pyreq_baseimage:$APP_NAME -f Dockerfile.tmp .

        docker tag autobot_pyreq_baseimage:$APP_NAME \
        asia-south1-docker.pkg.dev/dave-70c8e/splitting-pyreq-base-image/autobot-pyreq-baseimage:$TAG1

        docker push \
        asia-south1-docker.pkg.dev/dave-70c8e/splitting-pyreq-base-image/autobot-pyreq-baseimage:$TAG1

        docker tag autobot_pyreq_baseimage:$APP_NAME \
        asia-south1-docker.pkg.dev/dave-70c8e/splitting-pyreq-base-image/autobot-pyreq-baseimage:$TAG2

        docker push \
        asia-south1-docker.pkg.dev/dave-70c8e/splitting-pyreq-base-image/autobot-pyreq-baseimage:$TAG2

        rm -f Dockerfile.tmp
}

main
