#!/bin/bash

BRANCH=${1:-master}
SERVICE=${2:-document_processor}

DOCKERFILE=${DOCKERFILE:-Dockerfile}
pull_success=0

declare -A REPOS
REPOS["document_processor"]="asia-south1-docker.pkg.dev/dave-70c8e/document-processor-pyreq-image/autobot-pyreq-baseimage"
REPOS["spark"]="asia-south1-docker.pkg.dev/dave-70c8e/spark-pyreq-image/autobot-pyreq-baseimage"
REPOS["autobot_agents"]="asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage"

update_repo() {

    branch=$1

    git fetch origin "$branch"
    git checkout "$branch" || git checkout -b "$branch" origin/"$branch"
    git reset --hard origin/"$branch"

    if [ $? != 0 ]; then
        echo "Pull branch $branch failed."
        pull_success=0
        return
    fi

    pull_success=1
}

build_image() {

    DOCKERFILE_LOCAL=$1

    echo "Using Dockerfile: $DOCKERFILE_LOCAL"

    docker build \
        -t autobot-pyreq-baseimage:$SERVICE-$BRANCH \
        -f "$DOCKERFILE_LOCAL" \
        .

    docker tag \
        autobot-pyreq-baseimage:$SERVICE-$BRANCH \
        ${REPOS[$SERVICE]}:$BRANCH

    docker push ${REPOS[$SERVICE]}:$BRANCH
}

main() {

    if [ -z "${REPOS[$SERVICE]}" ]; then
        echo "Invalid service: $SERVICE"
        exit 1
    fi

    update_repo "$BRANCH"

    if [ $pull_success == 0 ]; then
        exit 1
    fi

    echo "Branch: $BRANCH"
    echo "Service: $SERVICE"

    if [ "$SERVICE" == "document_processor" ]; then

        cp ../../brochure_pipeline/requirements.txt ./brochure_pipeline_requirements.txt
        cp ../../document_processor/requirment_document_processor.txt ./document_processor_requirements.txt

        cp Document_BrochureDockerfile Document_BrochureDockerfile.tmp
        sed -i "s/<baseimage_tag>/$BRANCH/g" Document_BrochureDockerfile.tmp

        build_image Document_BrochureDockerfile.tmp

        rm -f Document_BrochureDockerfile.tmp

    elif [ "$SERVICE" == "spark" ]; then

        cp ../../spark/requirements.txt ./spark_requirements.txt

        cp SparkDockerfile SparkDockerfile.tmp
        sed -i "s/<baseimage_tag>/$BRANCH/g" SparkDockerfile.tmp

        build_image SparkDockerfile.tmp

        rm -f SparkDockerfile.tmp

    elif [ "$SERVICE" == "autobot_agents" ]; then

        cp ../../requirements.txt ./

        cp AutobotDockerfile AutobotDockerfile.tmp
        sed -i "s/<baseimage_tag>/$BRANCH/g" AutobotDockerfile.tmp

        build_image AutobotDockerfile.tmp

        rm -f AutobotDockerfile.tmp
    fi
}

main
