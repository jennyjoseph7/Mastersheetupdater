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


export LOG_RETENTION_DIR=${LOG_RETENTION_DIR:-./log_retention}
if [ ! -d $LOG_RETENTION_DIR ];then
	mkdir -p $LOG_RETENTION_DIR
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

export log_append_text="$HOSTNAME"_$(date +%s) 

export LOG_FILE=${LOGDIR}/${SERVICE_NAME}_${log_append_text}.log
export STDOUT_LOG_FILE=${LOGDIR}/${SERVICE_NAME}_stdout_${log_append_text}.log
export STDERR_LOG_FILE=${LOGDIR}/${SERVICE_NAME}_stderr_${log_append_text}.log 

export logio_agent_check_start_time=0
export LOGIO_AGENT_RESTART_TIME_SECS_THRESHOLD=${LOGIO_AGENT_RESTART_TIME_SECS_THRESHOLD:-300}

export tnow='date +"%Y-%m-%d %H:%M:%S"'
export worker_pid=0
export kill_signal=0

function stop_logio_agent() {
        #kill -0 $(ps -eaf | grep log.io- | head -n -1 | awk '{print $2}')
        pgrep -f "node /usr/local/bin/log.io-file-input" > /dev/null
        status=$?
        if [ $status == 0 ];then
                kill -9 $(ps -eaf | grep log.io- | head -n -1 | awk '{print $2}')
        else
                echo "Nothing to kill."
		status=0
        fi

}

function setup_logio_agent() {
    track_files=""
    if [ -f ./logio_track_files.logfile ];then
        track_files=$(cat ./logio_track_files.logfile)
    else
        # echo "$LOG_FILE,$STDOUT_LOG_FILE,$STDERR_LOG_FILE" > ./logio_track_files.logfile
        echo "$LOG_FILE" > ./logio_track_files.logfile
        track_files=$(cat ./logio_track_files.logfile)

    fi
    python3 /root/generate_logio_conf.py $track_files
    export LOGIO_FILE_INPUT_CONFIG_PATH=$APP_DIR/logio_conf.json
    status=$?
	if [ $status != 0 ];then
		echo "Generating log config failed. Exitting."
		exit
	fi	
	
	stop_logio_agent

	if [ $status == 0 ];then
		echo "Start input server"
		nohup log.io-file-input &
		echo $! > $BASE_PATH/$APP_NAME/logio.pid
                logio_agent_check_start_time=$(eval $tnow)
	else
		echo "Starting logger failed."
	fi
}

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
    	nohup $worker_path -m $ENTRYPOINT_PREFIX/$WORKER_ENTRYPOINT -n $PARALLEL_THREADS --shutdown-time=$SHUTDOWN_TIME &
        worker_pid=$!
	else
	    nohup $worker_path -m $ENTRYPOINT_PREFIX/$WORKER_ENTRYPOINT -n $PARALLEL_THREADS --shutdown-time=$SHUTDOWN_TIME --primary &
        worker_pid=$!
	fi

    echo $worker_pid > ./worker.pid
    if [ $SETUP_LOGIO_AGENT == "True" ];then
        sleep 5
        setup_logio_agent
    fi
    while [[ -n `jobs -rl | grep $worker_pid` ]]; do sleep 1; docheckup; echo `jobs -rl`; done
    echo "Exitting.."
    exit
}

function restart_logio_agent() {
    echo "Checking logio agent to restart. Last started time $logio_agent_check_start_time."

    if [ "$logio_agent_check_start_time" == 0 ];then
	echo "updating check start time."
        logio_agent_check_start_time=$(eval $tnow)
    fi

    logio_agent_check_start_time_seconds=$(date -d "$logio_agent_check_start_time" +%s)
    tnow_secs=$(date -d "$(eval $tnow)" +%s)
    tdiff=$((tnow_secs - logio_agent_check_start_time_seconds))

    if (( $tdiff > $LOGIO_AGENT_RESTART_TIME_SECS_THRESHOLD ));then
        echo "Restarting logio agent. tdiff is $tdiff, which is higher than set threshold $LOGIO_AGENT_RESTART_TIME_SECS_THRESHOLD."
        setup_logio_agent
        return
    fi

    echo "Not restarting logio agent as threshold - $LOGIO_AGENT_RESTART_TIME_SECS_THRESHOLD seconds not elapsed yet.\n"
}

function docheckup() {
    if [ $kill_signal == 0 ];then
	    echo "Running Checks."
	    restart_logio_agent
    else
	    echo "Kill received, skipping checks."
	    return 
    fi
}

function is_process_running() {
    ssw_pid=$1
    if ! kill -0 $ssw_pid > /dev/null 2>&1; then
        echo "Process $ssw_pid is not running." 1>&2
        return 1
    fi
    return 0
}

function kill_process() {
    # Kill the process with the given PID and a timeout of TERMINATION_GRACE_PERIOD or 130 seconds
    ssw_pid=$(cat ./worker.pid)
    shutdown_time=${2:-${TERMINATION_GRACE_PERIOD}}
    echo "Killing process $ssw_pid with a timeout of $shutdown_time seconds" 1>&2
    if ! is_process_running $ssw_pid; then
        return 0
    fi
    kill -15 $ssw_pid > /dev/null 2>&1 # Send SIGTERM to the process
    echo "Waiting for process $ssw_pid to terminate, with a timeout of $shutdown_time seconds..." 1>&2
    for i in $(seq 1 $shutdown_time); do
        if ! is_process_running $ssw_pid; then
            echo "Process $ssw_pid terminated successfully." 1>&2
            return 0
        fi
        sleep 1
        echo "Process $ssw_pid is still running. Waiting since $i seconds..." 1>&2
    done
    kill -9 $ssw_pid > /dev/null 2>&1 # Send SIGKILL to the process
    sleep 2
    if ! is_process_running $ssw_pid; then
        echo "Process $ssw_pid forcefully terminated." 1>&2
        return 0
    fi
    echo "Failed to terminate process $ssw_pid."
    return 1
}

function stop_single_workers() {
    export kill_signal=1
    stop_logio_agent
    shutdown_time=${1:-${TERMINATION_GRACE_PERIOD}}
    pids=()
    is_success=0
    echo "Stopping workers $ENTRYPOINT_PREFIX worker with a timeout of $shutdown_time seconds" 1>&2
    kill_process 

    
}

function main() {
    trap "echo 'Received kill signal'; stop_single_workers" SIGTERM SIGINT SIGHUP
    echo "Trap is set."
    echo "Starting ${SERVICE_NAME} in BG. Logs are written to stdout > $STDOUT_LOG_FILE err > $STDERR_LOG_FILE app > $LOG_FILE"
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

		nohup $WAITRESS_PATH --ident="" --port=${WEBAPP_PORT} --url-scheme=${WEBAPP_URL_SCHEME} --threads=${WEBAPP_API_THREADS} ${WEBAPP_APP_NAME}:app 1>> $STDOUT_LOG_FILE 2>> $STDERR_LOG_FILE &

	    app_pid=$!
		echo $app_pid > app.pid
        echo $app_pid > worker.pid
        if [ $SETUP_LOGIO_AGENT == "True" ];then
            sleep 5
            setup_logio_agent
        fi
        while [[ -n `jobs -rl | grep $app_pid` ]]; do sleep 1; docheckup; echo `jobs -rl`; done
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

			nohup $CRON_SCHEDULER_PATH &
			w_pid=$!
			echo "PID is $w_pid"
			echo $w_pid > $a.pid
            echo $w_pid > worker.pid
            if [ $SETUP_LOGIO_AGENT == "True" ];then
                sleep 5
                setup_logio_agent
            fi
            while [[ -n `jobs -rl | grep $w_pid` ]]; do sleep 1; docheckup; echo `jobs -rl`; done
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

			if [ $PRIMARY == 0 ];then
				nohup $CRON_WORKER_PATH -n $PARALLEL_THREADS &
			else
				nohup $CRON_WORKER_PATH -n $PARALLEL_THREADS --primary &
			fi
			w_pid=$!
			echo "PID is $w_pid"
			echo $w_pid > $a.pid
            echo $w_pid > worker.pid
            if [ $SETUP_LOGIO_AGENT == "True" ];then
                sleep 5
                setup_logio_agent
            fi
            while [[ -n `jobs -rl | grep $w_pid` ]]; do sleep 1; docheckup; echo `jobs -rl`; done
            echo "Exitting..."
            exit
		else
			echo "Process cron_worker is running."
		fi
    fi
}
