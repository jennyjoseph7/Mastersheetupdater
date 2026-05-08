#!/bin/bash

export pull_success=0

function update_repo() {
	sha=$1
	git reset --hard HEAD^
	git checkout $1
	git pull origin $1
	status=$?
	pull_success=1
	if [ $status != 0 ];then
		echo "Pull branch $1 failed."
		pull_success=0
	fi
}

function main() {
	update_repo $1
	if [ $pull_success == 0 ];then
		return
	fi
	cp ../../requirements.txt ./
    cp ../../spark/requirements.txt ./spark_requirements.txt
	docker build -t autobot_pyreq_baseimage:$TAG .	
	docker tag autobot_pyreq_baseimage:$TAG asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage:$TAG
	docker push asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage:$TAG
}

export BRANCH=${1:-"master"}

if [ "$BRANCH" == "master" ];then
	export TAG="latest"
else
	export TAG=$BRANCH
fi

main 