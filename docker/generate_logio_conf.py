import json, os, glob

def generate_conf(host, port, app_dir, service_name):
    logio_conf = {}
    logio_conf["messageServer"] = {}
    logio_conf["messageServer"] = {"host": host, "port": port}

    finputs = []

    for logf in glob.glob(f"{app_dir}/logs/*log"):
        spl = os.path.basename(logf).split(".")
        j = {}
        j["source"] = service_name
        j["stream"] = spl[0]
        j["config"] = {
            "path" : os.path.abspath(logf)
        }
        finputs.append(j)

    logio_conf["inputs"] = finputs
    return logio_conf


if __name__ == '__main__':
    SERVICE_NAME=os.environ.get("SERVICE_NAME", "UNKNOWN_SERVICE")
    HOST=os.environ.get("LOGIO_SERVER_TCP_URL", None)
    PORT=os.environ.get("LOGIO_SERVER_TCP_PORT", 6689)
    APP_DIR=os.environ.get("APP_DIR", "/root/app/")
    with open(f"{APP_DIR}/logio_conf.json","w") as fp:
        print("Writing log config.")
        fp.write(json.dumps(generate_conf(HOST, PORT, APP_DIR, SERVICE_NAME), indent=4))  