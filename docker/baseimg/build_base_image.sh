#!/bin/bash

function update_repo() {
	sha=$1
	git reset --hard HEAD^
	git pull origin scaling-up-twenty-threads
	git checkout $1

}

function main() {
	update_repo "scaling-up-twenty-threads"
	cp ../../requirements.txt ./
      	cp ../../spark/requirements.txt ./spark_requirements.txt
	docker build -t autobot_prod_baseimage:latest .	
	docker tag autobot_prod_baseimage:latest asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:latest
	docker push asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:latest
}

main

