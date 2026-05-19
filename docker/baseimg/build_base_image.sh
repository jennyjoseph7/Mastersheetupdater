#!/bin/bash

function main() {
	docker build -t autobot_baseimage:$1 .	
	docker tag autobot_baseimage:$1 asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:$1
	docker push asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:$1
}

export TAG=${1:-latest}

main $TAG
