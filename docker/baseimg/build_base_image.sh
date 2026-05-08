#!/bin/bash

function main() {
	docker build -t autobot_baseimage:latest .	
	docker tag autobot_baseimage:latest asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:latest
	docker push asia-south1-docker.pkg.dev/dave-70c8e/autobot-base-image/base_image:latest
}

main
