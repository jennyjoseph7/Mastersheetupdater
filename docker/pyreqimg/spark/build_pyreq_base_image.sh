#!/bin/bash

export pull_success=0
export BRANCH=${1:-"spark"}
export TAG="spark"

function update_repo() {
        branch=$1

        git fetch origin
        git checkout $branch

        if [ $? != 0 ]; then
                git checkout -b $branch origin/$branch
        fi

        git pull origin $branch

        status=$?

        if [ $status != 0 ]; then
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

        cp ../../spark/requirements.txt ./spark_requirements.txt

        sed -i "s/<baseimage_tag>/$TAG/g" Dockerfile

        docker build -t autobot_pyreq_baseimage:$TAG .

        docker tag autobot_pyreq_baseimage:$TAG \
        asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage:$TAG

        docker push \
        asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage:$TAG
}

main
