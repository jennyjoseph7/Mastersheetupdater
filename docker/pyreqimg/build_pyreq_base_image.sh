#!/bin/bash

function update_repo() {
	sha=$1
	git reset --hard HEAD^
	git pull origin $1
	git checkout $1

}

function main() {
	update_repo "master"
	cp ../../requirements.txt ./
    cp ../../spark/requirements.txt ./spark_requirements.txt
	docker build -t autobot_pyreq_baseimage:latest .	
	docker tag autobot_pyreq_baseimage:latest asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage:latest
	docker push asia-south1-docker.pkg.dev/dave-70c8e/autobot-pyreq-baseimage/autobot-pyreq-baseimage:latest
}

main