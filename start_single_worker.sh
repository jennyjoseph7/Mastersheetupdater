export BASE_PATH=${BASE_PATH:-$(dirname `pwd`)}
export APP_NAME=${APP_NAME:-$(basename `pwd`)}
export ENVIRONMENT=${ENVIRONMENT:-production}
export POSTGRES_URL=${POSTGRES_URL}
export PYTHON_VENV=${PYTHON_VENV:-"./pyenv"}
export PARALLEL_THREADS=${PARALLEL_THREADS:-2}
export SHUTDOWN_TIME=${SHUTDOWN_TIME:-86000}
export LOGDIR=${LOGDIR:-./logs}
if [ ! -d $LOGDIR ];then
	mkdir -p $LOGDIR
fi

export SETUP_WEBAPP=${SETUP_WEBAPP:-False}
export START_WORKERS=${START_WORKERS:-False}
export SETUP_CRON_SCHEDULER=${SETUP_CRON_SCHEDULER:-False}
export SETUP_CRON_EXECUTER=${SETUP_CRON_EXECUTER:-False}
# export RUN_IN_BG=True
# export KEEPALIVE_CONTAINER=${KEEPALIVE_CONTAINER:-True}

export ENTRYPOINT_PREFIX=${ENTRYPOINT_PREFIX:-0}
export WORKER_ENTRYPOINT=${WORKER_ENTRYPOINT:-0}
export PROCESS_SEARCH_STRING=${PROCESS_SEARCH_STRING:-$WORKER_ENTRYPOINT}

export SERVER_PORT=${SERVER_PORT:-0}
export PRIMARY=${PRIMARY:-0}

export WAITRESS_PATH=waitress-serve
export CRON_SCHEDULER_PATH=execute-cron-continuous
export CRON_WORKER_PATH=cron_worker
export APP_DIR=${APP_DIR:-"/root/app/"}


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

function start_workers() {
	stop_workers
	echo "Executing $WORKER_ENTRYPOINT as GRYD service."

    if [ $ENTRYPOINT_PREFIX == 0 ];then
        echo "Invalid entrypoint path."
        exit
    fi

    if [ $WORKER_ENTRYPOINT == 0 ];then
        echo "Invalid worker entrypoint."
        exist
    fi

	export worker_path=$WORKER_PATH
	echo "Container is set to true."
	echo "Creating pid file."
	echo FG > ./worker.pid
	WORKER_FNAME=${WORKER_ENTRYPOINT%.*}
    if [ $PRIMARY == 0 ];then
    	nohup $worker_path -m $ENTRYPOINT_PREFIX/$WORKER_ENTRYPOINT -n $PARALLEL_THREADS --shutdown-time=$SHUTDOWN_TIME 1>> ${LOGDIR}/${WORKER_FNAME}_stdout.log 2>> ${LOGDIR}/${WORKER_FNAME}_stderr.log &
        worker_pid=$!
	else
	    nohup $worker_path -m $ENTRYPOINT_PREFIX/$WORKER_ENTRYPOINT -n $PARALLEL_THREADS --shutdown-time=$SHUTDOWN_TIME --primary 1>> ${LOGDIR}/${WORKER_FNAME}_stdout.log 2>> ${LOGDIR}/${WORKER_FNAME}_stderr.log &
        worker_pid=$!
	fi

    echo $worker_pid > ./worker.pid
    if [ $SETUP_LOGIO_AGENT == "True" ];then
        sleep 60
        setup_logio_agent
    fi
    while [[ -n `jobs -rl | grep $worker_pid` ]]; do sleep 1; echo `jobs -rl`; done
    echo "Exitting.."
    exit
}

function stop_logio_server() {
	kill -9 $(ps -eaf | grep log.io- | head -n -1 | awk '{print $2}')
}


function setup_logio_agent() {
    python3 /root/generate_logio_conf.py
    export LOGIO_FILE_INPUT_CONFIG_PATH=$APP_DIR/logio_conf.json
    status=$?
	if [ $status != 0 ];then
		echo "Generating log config failed. Exitting."
		exit
	fi	
	
	stop_logio_server

	if [ $status == 0 ];then
		echo "Start input server"
		nohup log.io-file-input &
	else
		echo "Starting logger failed."
	fi
}

function main() {
    if [ $PYTHON_VENV != 0 ];then
    	export WAITRESS_PATH=$PYTHON_VENV/bin/waitress-serve
    	export WORKER_PATH=$PYTHON_VENV/bin/worker
    	export CRON_SCHEDULER_PATH=$PYTHON_VENV/bin/execute-cron-continuous
    	export CRON_WORKER_PATH=$PYTHON_VENV/bin/cron_worker
    fi

    if [ $SETUP_WEBAPP == "True" ];then
        echo "Setting up webapp."
		WEBAPP_PORT=$SERVER_PORT
		WEBAPP_URL_SCHEME=${URL_SCHEME:-https}
		WEBAPP_API_THREADS=$PARALLEL_THREADS
		WEBAPP_APP_NAME=${APP_NAME:-app}
	
		nohup $WAITRESS_PATH --ident="" --port=${WEBAPP_PORT} --url-scheme=${WEBAPP_URL_SCHEME} --threads=${WEBAPP_API_THREADS} ${WEBAPP_APP_NAME}:app 1>> ${LOGDIR}/webapp_stdout.log 2>> ${LOGDIR}/webapp_stderr.log &

	    app_pid=$!
		echo $app_pid > app.pid
        if [ $SETUP_LOGIO_AGENT == "True" ];then
            sleep 60
            setup_logio_agent
        fi
        while [[ -n `jobs -rl | grep $app_pid` ]]; do sleep 300; echo `jobs -rl`; done
        echo "Exitting..."
        exit
    elif [ $SETUP_CRON_SCHEDULER == "True" ];then
        a=cron_scheduler
    	echo "Starting default workers - $a"
		pid_filename=$a.pid
		w_pid=$(cat $pid_filename | echo 0)
		stat=100
    	if [ $w_pid != 0 ];then
			ps -eaf | grep $w_pid | grep execute-cron-continuous
			stat=$?
		fi

		if [ $stat != 0 ];then
			echo "Process exited or not started. Starting."
			echo "Starting Cron Continuous in BG. Logs are written to ${LOGDIR}/${a}_stderr.log and ${LOGDIR}/${a}_stdout.log"
			nohup $CRON_SCHEDULER_PATH 1>> ${LOGDIR}/${a}_stdout.log 2>> ${LOGDIR}/${a}_stderr.log &
			w_pid=$!
			echo "PID is $w_pid"
			echo $w_pid > $a.pid
            if [ $SETUP_LOGIO_AGENT == "True" ];then
                sleep 60
                setup_logio_agent
            fi
            while [[ -n `jobs -rl | grep $w_pid` ]]; do sleep 1; echo `jobs -rl`; done
            echo "Exitting..."
            exit
		else
			echo "Process execute-cron-continuous is running."
		fi
    elif [ $START_WORKERS == "True" ];then
        echo "Starting workers."
        start_workers
    fi

    if [ $SETUP_CRON_EXECUTER == "True" ];then
        a=cron_worker
    	echo "Starting default workers - $a"
		pid_filename=$a.pid
		w_pid=$(cat $pid_filename | echo 0)
		stat=100
		if [ $w_pid != 0 ];then
			ps -eaf | grep $w_pid | grep cron_worker
			stat=$?
		fi

		if [ $stat != 0 ];then
			echo "Process exited or not started. Starting."
			echo "Starting Cron Worker in BG. Logs are written to ${LOGDIR}/${a}_stderr.log and ${LOGDIR}/${a}_stdout.log"
			if [ $PRIMARY == 0 ];then
				nohup $CRON_WORKER_PATH -n $PARALLEL_THREADS 1>> ${LOGDIR}/${a}_stdout.log 2>> ${LOGDIR}/${a}_stderr.log &
			else
				nohup $CRON_WORKER_PATH -n $PARALLEL_THREADS --primary 1>> ${LOGDIR}/${a}_stdout.log 2>> ${LOGDIR}/${a}_stderr.log &
			fi
			w_pid=$!
			echo "PID is $w_pid"
			echo $w_pid > $a.pid
            if [ $SETUP_LOGIO_AGENT == "True" ];then
                sleep 60
                setup_logio_agent
            fi
            while [[ -n `jobs -rl | grep $w_pid` ]]; do sleep 1; echo `jobs -rl`; done
            echo "Exitting..."
            exit
		else
			echo "Process cron_worker is running."
		fi
    fi
}
