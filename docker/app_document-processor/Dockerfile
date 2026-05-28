FROM asia-south1-docker.pkg.dev/dave-70c8e/document-processor-pyreq-image/autobot-pyreq-baseimage:master

WORKDIR /root/
COPY autobot-agents.zip /root/
COPY generate_logio_conf.py /root/
RUN unzip autobot-agents.zip -d app/
WORKDIR /root/app/

CMD [ "bash" , "./start_process_container.sh" ]

