#!/bin/bash

if [ -e config.sh ];then
	echo "Found config file. Sourcing it."
	source config.sh 
fi

function gen_aws_creds_file() {
        mkdir /root/.aws
        echo "[default]" > /root/.aws/credentials
        echo "aws_access_key_id = $AWS_ACCESS_KEY_ID" >> /root/.aws/credentials
        echo "aws_secret_access_key = $AWS_SECRET_ACCESS_KEY" >> /root/.aws/credentials

        echo "[default]" > /root/.aws/config
        echo "region = $AWS_REGION_NAME" >> /root/.aws/config
        echo "output = json" >> /root/.aws/config
}

function main() {
	if [ "$CONTAINER" == "True" ];then
		gen_aws_creds_file
	fi
	source ./start_worker.sh
	start_workers
}

main

