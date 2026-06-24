import json, os, glob, sys, yaml

def generate_logio_conf(host, port, log_files, service_name):
    logio_conf = {}
    logio_conf["messageServer"] = {}
    logio_conf["messageServer"] = {"host": host, "port": port}

    finputs = []

    for logf in log_files:

        if not os.path.isfile(logf):
            print("Not valid log file.")
            continue

        spl = os.path.basename(logf).split(".")

        try:
            streamName = spl[0].split("_")[0]
            if not streamName:
                streamName = spl[0]
        except Exception as e:
            print(e)
            print("log file name formating issue, error in parsing log stream name, using fullname.")
            streamName = spl[0]

        logf = os.path.abspath(logf)
        bp, _ = os.path.splitext(logf)
        logf = f"{bp}*"

        j = {}
        j["source"] = service_name
        j["stream"] = streamName
        j["config"] = {
            "path" : logf
        }
        finputs.append(j)

    logio_conf["inputs"] = finputs
    return logio_conf

def generate_fluentbit_conf(host, port, log_files, service_name):
    final_config = {}
    final_config["pipeline"] = {}
    inputs = []
    outputs = []
    for log_file in log_files:
        logf = os.path.abspath(log_file)
        input_config = {
            "name" : "tail",
            "path" : logf,
            "tag" : service_name,
            "db" : f"/tmp/{service_name}.db"
        }
        inputs.append(input_config)
        output_config = {
            "name" : "loki",
            "match" : service_name,
            "host" : host,
            "port" : port,
            "tls" : "on",
            "tls.verify" : "on",
            "uri" : "/loki/api/v1/push",
            "labels" : f"service_name={service_name}"
        }
        outputs.append(output_config)
    final_config["pipeline"]["inputs"] = inputs
    final_config["pipeline"]["outputs"] = outputs
    
    return final_config

if __name__ == '__main__':
    SERVICE_NAME=f'{os.environ.get("SERVICE_NAME", "UNKNOWN_SERVICE")}-{os.environ.get("ENVIRONMENT", "UNKNOWN_ENVIRONMENT")}'
    HOST=os.environ.get("LOG_SERVER_URL", None)
    PORT=os.environ.get("LOG_SERVER_PORT", 6689)
    LOG_AGENT_TYPE=os.environ.get("LOG_AGENT_TYPE", None)
    APP_DIR=os.environ.get("BASE_DIR", "/root/app")
    log_files_csv= sys.argv[1]

    if not LOG_AGENT_TYPE:
        print("No log agent type given.")
        sys.exit()

    if not log_files_csv:
        print("No log files given")
        sys.exit()
    
    log_files = log_files_csv.split(",")
    print(f"Given log files - {log_files}.")
    print("Writing log config.")
    if LOG_AGENT_TYPE == "logio":
        with open(f"{APP_DIR}/logio_conf.json","w") as fp:
            fp.write(json.dumps(generate_logio_conf(HOST, PORT, log_files, SERVICE_NAME), indent=4))  
    elif LOG_AGENT_TYPE == "fluentbit":
        with open(f"{APP_DIR}/fluentbit_conf.yaml","w") as fp:
            yaml.dump(generate_fluentbit_conf(HOST, PORT, log_files, SERVICE_NAME), fp, default_flow_style=False, sort_keys=False)