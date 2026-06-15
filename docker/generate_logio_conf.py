import json, os, glob, sys

def generate_conf(host, port, log_files, service_name):
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


if __name__ == '__main__':
    SERVICE_NAME=f'{os.environ.get("SERVICE_NAME", "UNKNOWN_SERVICE")}-{os.environ.get("ENVIRONMENT", "UNKNOWN_ENVIRONMENT")}'
    HOST=os.environ.get("LOGIO_SERVER_TCP_URL", None)
    PORT=os.environ.get("LOGIO_SERVER_TCP_PORT", 6689)
    APP_DIR=os.environ.get("BASE_DIR", "/root/app")
    log_files_csv= sys.argv[1]

    if not log_files_csv:
        print("No log files given")
        sys.exit()
    
    log_files = log_files_csv.split(",")
    print(f"Given log files - {log_files}.")
    with open(f"{APP_DIR}/logio_conf.json","w") as fp:
        print("Writing log config.")
        fp.write(json.dumps(generate_conf(HOST, PORT, log_files, SERVICE_NAME), indent=4))  