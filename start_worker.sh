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
#export RDS_SECRET=${RDS_SECRET:-0}
export TAIL_LOGS=${TAIL_LOGS:-True}
if [ ! -d $LOGDIR ];then
	mkdir -p $LOGDIR
fi

export SETUP_WEBAPP=${SETUP_WEBAPP:-True}
export SETUP_WORKERS=${SETUP_WORKERS:-True}
export RUN_IN_BG=True
export KEEPALIVE_CONTAINER=${KEEPALIVE_CONTAINER:-True}
export START_AGENTS=${START_AGENTS:-0}
export START_WORKERS=${START_WORKERS:-0}
export DEFAULT_WORKERS=${DEFAULT_WORKERS:-0}
export SERVER_PORT=${SERVER_PORT:-0}
export PRIMARY=${PRIMARY:-0}

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

function start_default_workers() {
	for a in ${DEFAULT_WORKERS//,/ };do
		echo "Starting default workers - $a"
		pid_filename=${a}.pid
		w_pid=$(cat $pid_filename | echo 0)
		stat=100

		if [ "$a" == "cron-scheduler" ];then
			if [ $w_pid != 0 ];then
				ps -eaf | grep $w_pid | grep execute-cron-continuous
				stat=$?
			fi

			if [ $stat != 0 ];then
				echo "Process exited or not started. Starting."
				echo "Starting Cron Continuous in BG. Logs are written to ${LOGDIR}/${a}_stderr.log and ${LOGDIR}/${a}_stdout.log"
				nohup execute-cron-continuous 1>> ${LOGDIR}/${a}_stdout.log 2>> ${LOGDIR}/${a}_stderr.log &
				w_pid=$!
				echo "PID is $w_pid"
				echo $w_pid > $a.pid
			else
				echo "Process execute-cron-continuous is running."
			fi


		fi

		if [ "$a" == "cron_worker" ];then
			if [ $w_pid != 0 ];then
				ps -eaf | grep $w_pid | grep cron_worker
				stat=$?
			fi

			if [ $stat != 0 ];then
				echo "Process exited or not started. Starting."
				echo "Starting Cron Worker in BG. Logs are written to ${LOGDIR}/${a}_stderr.log and ${LOGDIR}/${a}_stdout.log"
				if [ $PRIMARY == 0 ];then
					nohup cron_worker 1>> ${LOGDIR}/${a}_stdout.log 2>> ${LOGDIR}/${a}_stderr.log &
				else
					nohup cron_worker --primary 1>> ${LOGDIR}/${a}_stdout.log 2>> ${LOGDIR}/${a}_stderr.log &
				fi
				w_pid=$!
				echo "PID is $w_pid"
				echo $w_pid > $a.pid
			else
				echo "Process cron_worker is running."
			fi
		fi

	done
}

function start_worker_in_bg() {
	worker_path=worker
	
	echo "Agents to start : $START_AGENTS, Workers to start : $START_WORKERS"
	if [ $START_AGENTS != 0 ];then
		for a in ${START_AGENTS//,/ };do
			echo "Starting up Agent - $a."
			jq -c '.agents[]' start_worker_config.json | while IFS= read -r wmap;do
				echo "$wmap"
				WORKER_NAME=$(jq -r '.name' <<< "$wmap")
				WORKER_ENTRYPOINT=$(jq -r '.entry_point' <<< "$wmap")
				WORKER_PARALLEL_THREADS=$(jq -r '.parallel_threads' <<< "$wmap")
				WORKER_SHUTDOWN_TIME=$(jq -r '.shutdown_time' <<< "$wmap")
				WORKER_FNAME=${WORKER_ENTRYPOINT%.*}


				if [ "$WORKER_NAME" == "$a" ];then
					pid_filename=${WORKER_NAME}_${WORKER_FNAME}.pid
					w_pid=$(cat $pid_filename | echo 0)
					stat=100
	
					if [ $w_pid != 0 ];then
						ps -eaf | grep $w_pid | grep $WORKER_ENTRYPOINT
						stat=$?
					fi
	
					if [ $stat != 0 ];then
						echo "Process exited or not started. Starting."
						echo "Setting up $WORKER_NAME in BG. Logs are written to ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stderr.log and ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stdout.log"
						if [ $PRIMARY == 0 ];then
							nohup $worker_path -m agents/$WORKER_ENTRYPOINT -n $WORKER_PARALLEL_THREADS --shutdown-time=$WORKER_SHUTDOWN_TIME 1>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stdout.log 2>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stderr.log &
						else
							nohup $worker_path -m agents/$WORKER_ENTRYPOINT -n $WORKER_PARALLEL_THREADS --shutdown-time=$WORKER_SHUTDOWN_TIME --primary 1>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stdout.log 2>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stderr.log &
						fi
						w_pid=$!
						echo $w_pid > ${WORKER_NAME}_${WORKER_FNAME}.pid
					else
						echo "Process $WORKER_ENTRYPOINT is running."
					fi
				fi
			done
		done
	else
		echo "No start agents set."
	fi

	if  [ $START_WORKERS != 0 ];then
		for w in ${START_WORKERS//,/ };do
			echo "Starting up worker - $w."
			jq -c '.workers[]' start_worker_config.json | while IFS= read -r wmap;do
				echo "$wmap"
				WORKER_NAME=$(jq -r '.name' <<< "$wmap")
				WORKER_ENTRYPOINT=$(jq -r '.entry_point' <<< "$wmap")
				WORKER_PARALLEL_THREADS=$(jq -r '.parallel_threads' <<< "$wmap")
				WORKER_SHUTDOWN_TIME=$(jq -r '.shutdown_time' <<< "$wmap")
				WORKER_FNAME=${WORKER_ENTRYPOINT%.*}
	
				if [ "$WORKER_NAME" == "$w" ];then
					pid_filename=${WORKER_NAME}_${WORKER_FNAME}.pid
					w_pid=$(cat $pid_filename | echo 0)
					stat=100
	
					if [ $w_pid != 0 ];then
						ps -eaf | grep $w_pid | grep $WORKER_ENTRYPOINT
						stat=$?
					fi
	
					if [ $stat != 0 ];then
						echo "Setting up $WORKER_NAME - '$WORKER_ENTRYPOINT' in BG. Logs are written to ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stderr.log and ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stdout.log"
						if [ $PRIMARY == 0 ];then
							nohup $worker_path -m $WORKER_NAME/$WORKER_ENTRYPOINT -n $WORKER_PARALLEL_THREADS --shutdown-time=$WORKER_SHUTDOWN_TIME 1>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stdout.log 2>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stderr.log &
						else
							nohup $worker_path -m $WORKER_NAME/$WORKER_ENTRYPOINT -n $WORKER_PARALLEL_THREADS --shutdown-time=$WORKER_SHUTDOWN_TIME --primary 1>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stdout.log 2>> ${LOGDIR}/${WORKER_NAME}_${WORKER_FNAME}_stderr.log &
						fi
						w_pid=$!
						echo $w_pid > ${WORKER_NAME}_${WORKER_FNAME}.pid
					else
						echo "Process $WORKER_ENTRYPOINT is running."
					fi
				fi
			done
		done
	else
		echo "No start agents set."
	fi
}

function start_daemon_process() {
	app_pid=$(cat app.pid || echo 0)
	if [ $app_pid == 0 ];then
		echo "Webapp is not running."
	else
		echo "Webapp is running."
	fi

	if [ $START_WORKERS != 0 ];then
	
		for w in ${START_WORKERS//,/ };do
			echo "Daemon checking health of Workers."
			jq -c '.workers[]' start_worker_config.json | while IFS= read -r wmap;do

				WORKER_NAME=$(jq -r '.name' <<< "$wmap")
				if [ $WORKER_NAME == $w ];then
					WORKER_NAME=$(jq -r '.name' <<< "$wmap")
					WORKER_ENTRYPOINT=$(jq -r '.entry_point' <<< "$wmap")
					WORKER_FNAME=${WORKER_ENTRYPOINT%.*}
					pid_filename=${WORKER_NAME}_${WORKER_FNAME}.pid
					
					w_pid=$(cat $pid_filename || echo 0)
					stat=100
			
					x_pid=$(ps -eaf | grep $w_pid | grep $WORKER_FNAME | head -1 | awk '{print $2}')
					echo "PID for $WORKER_NAME is $w_pid"
					if [ -n $x_pid ];then
						echo "Service $WORKER_NAME is running."
					else
						echo "Service $WORKER_NAME is not running."
 					fi
				fi
			done
		done
	else
		echo "No start workers set."
	fi

	if [ $START_AGENTS != 0 ];then
		for w in ${START_AGENTS//,/ };do
			echo "Daemon checking health of Agents."
			jq -c '.agents[]' start_worker_config.json | while IFS= read -r wmap;do

				WORKER_NAME=$(jq -r '.name' <<< "$wmap")
				if [ $WORKER_NAME == $w ];then
					WORKER_ENTRYPOINT=$(jq -r '.entry_point' <<< "$wmap")
					WORKER_FNAME=${WORKER_ENTRYPOINT%.*}
					pid_filename=${WORKER_NAME}_${WORKER_FNAME}.pid
					
					w_pid=$(cat $pid_filename || echo 0)
					stat=100
					
					x_pid=$(ps -eaf | grep $w_pid | grep $WORKER_FNAME | head -1 | awk '{print $2}')

					if [ -n $x_pid ];then
						echo "Agent $WORKER_NAME is running."
					else
						echo "Agent $WORKER_NAME is not running."
 					fi
				fi
			done
		done
	else
		echo "No start agents set."
	fi
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
			
			if [ $SERVER_PORT != 0 ];then
				WEBAPP_PORT=$SERVER_PORT
			fi

			nohup waitress-serve --ident="" --port=${WEBAPP_PORT} --url-scheme=${WEBAPP_URL_SCHEME} --threads=${WEBAPP_API_THREADS} ${WEBAPP_APP_NAME}:app 1>> ${LOGDIR}/webapp_stdout.log 2>> ${LOGDIR}/webapp_stderr.log &

			#export RDS_SECRET=${RDS_SECRET} && nohup python app.py 1>> ${LOGDIR}/webapp_stdout.log 2>> ${LOGDIR}/webapp_stderr.log & 
	    	app_pid=$!
			echo $app_pid > app.pid
		fi

		if [ "$SETUP_WORKERS" == "True" ];then
			echo "Statring workers."
			start_worker_in_bg
		fi
		
		if [ "$KEEPALIVE_CONTAINER" == "True" ];then
			echo "Running dev container."
			echo "Done with deploy" >&2

			while true; do
				#if [ "$TAIL_LOGS" == "True" ];then
				#	tail -f --follow=name --retry ./logs/*.log 
				#else
			       	#	sleep 600
				#fi
				
				start_daemon_process
				sleep 5
			done
		fi
	fi
}

function main() {
	start_default_workers
	start_workers
}

#main
