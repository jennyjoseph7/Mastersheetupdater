#!/bin/bash

pull_success=0

BRANCH=${1:-master}

IMAGE_NAME="autobot-pyreq-baseimage"
APP_NAME="document_processor"

REPO="asia-south1-docker.pkg.dev/dave-70c8e/document-processor-pyreq-image/$IMAGE_NAME"

update_repo() {

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

main() {

    update_repo $BRANCH

    if [ $pull_success == 0 ]; then
        return
    fi

    cp ../../../brochure_pipeline/requirements.txt ./brochure_pipeline_requirements.txt
    cp ../../../document_processor/requirment_document_processor.txt ./document_processor_requirements.txt

    cp Dockerfile Dockerfile.tmp
    sed -i "s/<baseimage_tag>/$BRANCH/g" Dockerfile.tmp

    docker build -t $IMAGE_NAME:$APP_NAME -f Dockerfile.tmp .

    docker tag $IMAGE_NAME:$APP_NAME $REPO:$BRANCH

    docker push $REPO:$BRANCH

    rm -f Dockerfile.tmp
}

main
