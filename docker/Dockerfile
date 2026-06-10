FROM <PYREQ_IMAGE>:<DOCKER_BASE_IMG_TAG>

WORKDIR /root/

COPY <zipname>.zip /root/

COPY generate_logio_conf.py /root/

RUN unzip <zipname>.zip -d app/

WORKDIR /root/app/

CMD [ "bash" , "./start_process_container.sh" ]

