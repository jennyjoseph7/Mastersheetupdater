#   !/bin/bash -x

export BASE_PATH=${BASE_PATH:-$(dirname `pwd`)}
export APP_NAME=${APP_NAME:-$(basename `pwd`)}
export ENVIRONMENT=${ENVIRONMENT:-production}
export POSTGRES_URL=${POSTGRES_URL}
export PYTHON_VENV=${PYTHON_VENV:-"./pyenv"}
export PARALLEL_THREADS=${PARALLEL_THREADS:-10}
export SHUTDOWN_TIME=${SHUTDOWN_TIME:-55}
export PROCESS_SEARCH_STRING=${PROCESS_SEARCH_STRING:-$WORKER_ENTRYPOINT}
export LOGDIR=${LOGDIR:-./logs}

export SETUP_WEBAPP=${WEBAPP:-True}
export SETUP_WORKERS=${SETUP_WORKERS:-True}
export RUN_IN_BG=True
export DEV_CONTAINER=${DEV_CONTAINER:-False}

process_config=`cat start_worker_config.json`

echo "APP Config"
echo $process_config


function stop_workers() {

    pid_file_path=$BASE_PATH/$APP_NAME/worker.pid

    if [ ! -f $pid_file_path ];then
        echo "PID file doesn't exist."
        return
    fi

    ssw_pid=$(cat "$pid_file_path")  # Read the process ID from the file

    if [ "$ssw_pid" == "FG" ];then
        echo "Killing foreground process."
        echo $PROCESS_SEARCH_STRING
        if [ ! -n $PROCESS_SEARCH_STRING ];then
            echo "PROCESS_SEARCH_STRING is empty. Aborting."
            exit
        fi

        ssw_pid=`ps -eaf | grep $PROCESS_SEARCH_STRING | head -1 | awk '{print $2}'`
        echo "Got PIDs - $ssw_pid"
    fi

    if [ ! -n "$ssw_pid" ];then
        echo "PID file is empty or invalid pid"
        return
    fi

    #   kill $ssw_pid  # Send SIGTERM to the process

    # Wait for the process to terminate, with a timeout of 20 seconds
    for i in {1..20}; do
        if ! kill -0 $ssw_pid > /dev/null 2>&1; then
            echo "Process $ssw_pid terminated successfully."
            rm -f $BASE_PATH/$APP_NAME/worker.pid
            break
        fi
        sleep 1
    done

    # If the process is still running after 20 seconds, force kill it
    if kill -0 $ssw_pid > /dev/null 2>&1; then
        echo "Process $ssw_pid did not terminate in time. Sending SIGKILL..."
        kill -9 $ssw_pid
        sleep 2
        if ! kill -0 $ssw_pid > /dev/null 2>&1; then
            echo "Process $ssw_pid forcefully terminated."
            rm -f $BASE_PATH/$APP_NAME/worker.pid
        else
            echo "Failed to terminate process $ssw_pid."
        fi
    fi
}

function start_worker_in_bg() {
	worker_path=worker
	jq -c '.workers[]' start_worker_config.json | while IFS= read -r wmap;do
		echo "$wmap"
		WORKER_NAME=$(jq -r '.name' <<< "$wmap")
		WORKER_ENTRYPOINT=$(jq -r '.entry_point' <<< "$wmap")
		WORKER_PARALLEL_THREADS=$(jq -r '.parallel_threads' <<< "$wmap")
		WORKER_SHUTDOWN_TIME=$(jq -r '.shutdown_time' <<< "$wmap")

		echo "Setting up $WORKER_NAME in BG. Logs are written to ${LOGDIR}/${WORKER_NAME}_stderr.log and ${LOGDIR}/${WORKER_NAME}_stdout.log"
	
		nohup $worker_path -m agents/$WORKER_ENTRYPOINT -n $PARALLEL_THREADS --shutdown-time=$SHUTDOWN_TIME 1>> ${LOGDIR}/${WORKER_NAME}_stdout.log 2>> ${LOGDIR}/${WORKER_NAME}_stderr.log &
	done
	

}

function start_workers() {
	stop_workers
	#echo "Executing $WORKER_ENTRYPOINT as GRYD service."

	if [ "$CONTAINER" == "True" ];then
		export worker_path="worker"
		echo "Container is set to true."
		echo "Creating pid file."
	        echo FG > ./worker.pid	
		echo "Single container deloyment logic is not integrated yet."

	elif [ "$RUN_IN_BG" == "True" ];then
		if [ "$SETUP_WEBAPP" == "True" ];then
			webapp_config=`cat start_worker_config.json | jq '.webapp'`
			WEBAPP_PORT=$(jq -r '.port' <<< "$webapp_config")
			WEBAPP_URL_SCHEME=$(jq -r '.url_scheme' <<< "$webapp_config")
			WEBAPP_API_THREADS=$(jq -r '.api_threads' <<< "$webapp_config")
			WEBAPP_APP_NAME=$(jq -r '.name' <<< "$webapp_config")

			#nohup waitress-serve --ident="" --port=${WEBAPP_PORT} --url-scheme=${WEBAPP_URL_SCHEME} --threads=${WEBAPP_API_THREADS} ${WEBAPP_APP_NAME}:app 1>> ${LOGDIR}/webapp_stdout.log 2>> ${LOGDIR}/webapp_stderr.log &
	    		app_pid=$!
			echo $app_pid > app.pid
		fi

		if [ "$SETUP_WORKERS" == "True" ];then
			echo "Statring workers."
			start_worker_in_bg
		fi
		
		if [ "$DEV_CONTAINER" == "True" ];then
			echo "Running dev container."
			echo "Done with deploy" >&2
			while [[ -n `jobs -l | grep $app_pid` ]]; do sleep 600; done
		fi
	fi
}

function main() {
	start_workers
}

#main

