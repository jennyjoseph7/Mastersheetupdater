#!/bin/bash -x
export BASE_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
pushd $BASE_DIR > /dev/null
export APP_NAME=${APP_NAME:-$(basename $BASE_DIR)}
export ENVIRONMENT=${ENVIRONMENT:-production}
export POSTGRES_URL=${POSTGRES_URL}
export PYTHON_VENV=${PYTHON_VENV:-0}
export PARALLEL_THREADS=${PARALLEL_THREADS:-0}
export API_THREADS=${API_THREADS:-0}
export SHUTDOWN_TIME=${SHUTDOWN_TIME:-0}
export LOGDIR=${LOGDIR:-./logs}
#export RDS_SECRET=${RDS_SECRET:-0}
export TAIL_LOGS=${TAIL_LOGS:-True}
if [ ! -d $LOGDIR ];then
    mkdir -p $LOGDIR
fi
export LOG_APPEND_TEXT="$HOSTNAME"_$(date +%s) 
export SETUP_WEBAPP=${SETUP_WEBAPP:-True}
export SETUP_WORKERS=${SETUP_WORKERS:-True}
# Start webapps is a comma-separated list of <app-name>,<app-name1>
export START_WEBAPP=${START_WEBAPP:-1}
# Start agents is a comma-separated list of <agent_name>/<entrypoint>.py,<agent_name1>/<entrypoint1.py>
export START_AGENTS=${START_AGENTS:-1}
# Start workers is a comma-separated list of <name>/<entrypoint>.py,<name1>/<entrypoint1.py>
export START_WORKERS=${START_WORKERS:-1}
# DEFAULT_WORKERS can be a comma-separated list of default workers, currently including "cron_worker,cron-scheduler"
export DEFAULT_WORKERS=${DEFAULT_WORKERS:-1}
export SERVER_PORT=${SERVER_PORT:-5000}
export PRIMARY=${PRIMARY:-1}
export WORKER_PATH=worker
export WAITRESS_PATH=waitress-serve
export CRON_SCHEDULER_PATH=execute-cron-continuous
export CRON_WORKER_PATH=cron_worker
DEFAULT_WORKER_EXECUTABLES=""

if [ $PYTHON_VENV != 0 ];then
        export WAITRESS_PATH=$PYTHON_VENV/bin/waitress-serve
        export WORKER_PATH=$PYTHON_VENV/bin/worker
        export CRON_SCHEDULER_PATH=$PYTHON_VENV/bin/execute-cron-continuous
        export CRON_WORKER_PATH=$PYTHON_VENV/bin/cron_worker
fi

if [[ $DEFAULT_WORKERS != 0 ]];then
    if [[ $DEFAULT_WORKERS == 1 ]];then
        DEFAULT_WORKERS="cron-scheduler,cron-worker"
    fi
    for default_worker in ${DEFAULT_WORKERS//,/ }; do
        if [ "$default_worker" == "cron-scheduler" ];then
            DEFAULT_WORKER_EXECUTABLES+="${CRON_SCHEDULER_PATH},"
        elif [ "$default_worker" == "cron_scheduler" ];then
            DEFAULT_WORKER_EXECUTABLES+="${CRON_SCHEDULER_PATH},"
        elif [ "$default_worker" == "cron_worker" ];then
            DEFAULT_WORKER_EXECUTABLES+="${CRON_WORKER_PATH},"
        elif [ "$default_worker" == "cron-worker" ];then
            DEFAULT_WORKER_EXECUTABLES+="${CRON_WORKER_PATH},"
        fi
    done
fi


process_config=`cat start_worker_config.json`

echo "APP Config"
echo $process_config

function stop_logio_agent() {
	kill -9 $(ps -eaf | grep log.io- | head -n -1 | awk '{print $2}')
}

function setup_logio_agent() {
    log_files=${1:-$LOG_FILE}
    track_files=""
    if [ -f ./logio_track_files.logfile ];then
        track_files=$(cat ./logio_track_files.logfile)
    else
        # echo "$LOG_FILE,$STDOUT_LOG_FILE,$STDERR_LOG_FILE" > ./logio_track_files.logfile
        echo "$log_files" > ./logio_track_files.logfile
        track_files=$(cat ./logio_track_files.logfile)

    fi
    python3 /root/generate_logio_conf.py $track_files
    export LOGIO_FILE_INPUT_CONFIG_PATH=$BASE_DIR/logio_conf.json
    status=$?
	if [ $status != 0 ];then
		echo "Generating log config failed. Exitting."
		exit
	fi	
	
	stop_logio_agent

	if [ $status == 0 ];then
		echo "Start input server"
		nohup log.io-file-input &
	else
		echo "Starting logger failed."
	fi
}


function get_process_pids() {
    # Get the list of pid of the process matching the search string
    # e.g. get_pid "python.*app.py" will return the pid of the first process matching the regex "python.*app.py"
    echo "Getting process pids for search-string $@" 1>&2
    ssw_pid=`ps -eaf | grep "$@" | grep -v grep | grep -v "ps -eaf" | awk '{print $2}' | sort`
    if [[ -n $ssw_pid ]];then
        echo $ssw_pid
        return 0
    else
        echo "No active process found for search string $@." 1>&2
        return 1
    fi
}

function get_worker_pids() {
    # Get the pids of the worker matching the search string
    # e.g. get_worker_pids "python app.py" will return the pids of the processes matching the regex "python.*app.py"
    worker_name=$1
    worker_fname=${2%.*}
    # Get the pid of the process matching the search string
    echo "Getting worker pids for $worker_name $worker_fname" 1>&2
    pid_filename=`ls -1 $BASE_DIR/${worker_name}_${worker_fname}*.pid 2>/dev/null | sort`
    echo "PID filename: $pid_filename" 1>&2
    for pid_file in $pid_filename; do
        pid=$(cat $pid_file)
        if [[ -n $pid ]];then
            echo $pid
            return 0
        fi
    done
    echo "No pid found for ${worker_name}_${worker_fname}" 1>&2
    return 1
}

function remove_pid_file() {
    pid_filename=$1
    echo "Trying to remove pid file $pid_filename" 1>&2
    if [ ! -f $pid_filename ];then
        echo "Pid file $pid_filename does not exist." 1>&2
        return 0
    fi
    ssw_pid=$(cat $pid_filename)
    echo "Checking if process $ssw_pid is running from pid file $pid_filename" 1>&2
    if ! is_process_running $ssw_pid; then
        echo "Removing pid file $pid_filename. Since no process is running with pid $ssw_pid" 1>&2
        rm -f $pid_filename
        return 0
    fi
    echo "Not removing pid file $pid_filename." 1>&2
    return 1
}

function remove_worker_pid_file() {
    worker_name=$1
    worker_fname=${2%.*}
    echo "Removing worker pid file for $worker_name_$worker_fname" 1>&2
    pid_filename=`ls -1 $BASE_DIR/${worker_name}_${worker_fname}*.pid 2>/dev/null | sort`
    is_success=0
    for pid_file in $pid_filename; do
        remove_pid_file $pid_file
        if [ $? -ne 0 ];then
            is_success=1
        fi
    done
    return $is_success
}

function get_webapp_pids() {
    webapp_name=$1
    echo "Getting webapp pids for $webapp_name" 1>&2
    pid_filename=`ls -1 $BASE_DIR/${webapp_name}*.pid 2>/dev/null | sort`
    for pid_file in $pid_filename; do
        pid=$(cat $pid_file)
        if [[ -n $pid ]];then
            echo $pid
        fi
    done
    echo "No pid found for $webapp_name" 1>&2
    return 1
}


function remove_webapp_pid_file() {
    webapp_name=$1
    echo "Removing webapp pid file for $webapp_name" 1>&2
    pid_filename=`ls -1 $BASE_DIR/${webapp_name}*.pid 2>/dev/null | sort`
    is_success=0
    for pid_file in $pid_filename; do
        remove_pid_file $pid_file
        if [ $? -ne 0 ];then
            is_success=1
        fi
    done
    return $is_success
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
    # Kill the process with the given PID and a timeout of 130 seconds
    ssw_pid=$1
    shutdown_time=${2:-130}
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

function kill_process_by_search_string() {
    # GET pids by search string and then kill all the PIDs by that string e.g. kill_process_by_search_string "my.*search.*string"
    ssw_pids=`get_process_pids "${1}"`
    shutdown_time=${2:-130}
    echo "SSW PIDs for search-string ${1}: $ssw_pids" 1>&2
    for ssw_pid in $ssw_pids; do
        echo "Killing process $ssw_pid with a timeout of $shutdown_time seconds" 1>&2
        kill_process $ssw_pid $shutdown_time
        if [ $? -ne 0 ];then
            echo "Failed to kill process $ssw_pid within $shutdown_time seconds" 1>&2
            is_success=1
        fi
    done
    return is_success
}


function stop_worker() {
    # Stop the worker by killing the process and waiting for it to terminate
    # e.g. stop_worker 130 will stop the worker named "workers" with a timeout of 130 seconds
    worker_name=$1
    shutdown_time=${2:-130}
    worker_type=${3:-workers}
    echo "Stopping $worker_type $worker_name with a timeout of $shutdown_time seconds" 1>&2
    names=( `jq -r ".${worker_type}[] | select(.name == \"${worker_name}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.name'` )
    s_entry_points=( `jq -r ".${worker_type}[] | select(.name == \"${worker_name}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.entry_point'` )
    echo "Names: $names" 1>&2
    echo "Entry points: $s_entry_points" 1>&2
    is_success=0
    for i in $(seq 0 $((${#names[@]} - 1))); do
        name=${names[$i]}
        s_entry_point=${s_entry_points[$i]}
        worker_fname=${s_entry_point%.*}
        echo "Stopping worker $i $name $s_entry_point" 1>&2
        for ssw_pid in `get_worker_pids ${name} ${s_entry_point}`; do
            kill_process $ssw_pid $shutdown_time
            if [ $? -ne 0 ];then
                echo "Failed to kill process $ssw_pid within $shutdown_time seconds" 1>&2
                is_success=1
            fi
        done
        ssw_pids=`get_process_pids "${name}.*${s_entry_point}"`
        echo "SSW PIDs for ${name}/${s_entry_point}: $ssw_pids" 1>&2
        for ssw_pid in $ssw_pids; do
            echo "Killing process $ssw_pid with a timeout of $shutdown_time seconds" 1>&2
            kill_process $ssw_pid $shutdown_time
            if [ $? -ne 0 ];then
                echo "Failed to kill process $ssw_pid within $shutdown_time seconds" 1>&2
                is_success=1
            fi
        done
        if [ $is_success -eq 0 ];then
            remove_worker_pid_file $name $s_entry_point
        fi
    done
    return $is_success
}

function stop_agent() {
    # Stop the agent by killing the process and waiting for it to terminate
    # e.g. stop_agent "agents" 130 will stop the agent named "agents" with a timeout of 130 seconds
    agent_name=$1
    shutdown_time=${2:-130}
    echo "Stopping agent $agent_name with a timeout of $shutdown_time seconds" 1>&2
    stop_worker $agent_name $shutdown_time agents
    return $?
}

function stop_webapp() {
    # Stop the webapp by killing the process and waiting for it to terminate
    # e.g. stop_webapp "app" 130 will stop the webapp named "app" with a timeout of 130 seconds
    webapp_name=$1
    shutdown_time=${2:-130}
    echo "Stopping webapp $webapp_name with a timeout of $shutdown_time seconds" 1>&2
    is_success=0
    for ssw_pid in `get_webapp_pids $webapp_name`; do
        kill_process $ssw_pid $shutdown_time
        if [ $? -ne 0 ];then
            is_success=1
        fi
    done
    for ssw_pid in `get_process_pids "waitress-serve.*$webapp_name"`; do
        kill_process $ssw_pid $shutdown_time
        if [ $? -ne 0 ];then
            is_success=1
        fi
    done
    if [ $is_success -eq 0 ];then
        remove_webapp_pid_file $webapp_name
    fi
    return $is_success
}

function stop_default_worker() {
    # Stop the default worker by killing the process and waiting for it to terminate
    # e.g. stop_default_worker "cron-scheduler" 130 will stop the default worker named "cron-scheduler" with a timeout of 130 seconds
    default_worker=$1
    shutdown_time=${2:-130}
    echo "Stopping default workers $default_worker with a timeout of $shutdown_time seconds" 1>&2
    is_success=0
    for ssw_pid in `ls -1 $BASE_DIR/${default_worker}*.pid 2>/dev/null | sort`; do
        kill_process $ssw_pid $shutdown_time
        if [ $? != 0 ];then
            is_success=1
        fi
    done
    for ssw_pid in `get_process_pids "worker.*$default_worker"`; do
        kill_process $ssw_pid $shutdown_time
        if [ $? != 0 ];then
            is_success=1
        fi
    done
    if [ $is_success -eq 0 ];then
        remove_webapp_pid_file $default_worker
    fi
    return $is_success
}

function stop_all_workers() {
    echo "Stopping all workers with a timeout of $shutdown_time seconds" 1>&2
    shutdown_time=${1:-130}
    pids=()
    is_success=0
    echo "Stopping default workers with a timeout of $shutdown_time seconds" 1>&2
    for default_worker in ${DEFAULT_WORKER_EXECUTABLES//,/ }; do
        stop_default_worker $default_worker $shutdown_time &
        pids+=($!)
    done
    worker_names=`jq -r '.workers[].name' ${BASE_DIR}/start_worker_config.json | sort -u 2>/dev/null`
    echo "Stopping workers $worker_names with a timeout of $shutdown_time seconds" 1>&2
    for worker_name in $worker_names; do
        stop_worker $worker_name $shutdown_time &
        pids+=($!)
    done
    agent_names=`jq -r '.agents[].name' ${BASE_DIR}/start_worker_config.json | sort -u 2>/dev/null`
    echo "Stopping agents $agent_names with a timeout of $shutdown_time seconds" 1>&2
    for agent_name in $agent_names; do
        stop_agent $agent_name $shutdown_time &
        pids+=($!)
    done
    webapp_names=`jq -r '.webapps[].name' ${BASE_DIR}/start_worker_config.json | sort -u 2>/dev/null`
    echo "Stopping webapps $webapp_names with a timeout of $shutdown_time seconds" 1>&2
    for webapp_name in $webapp_names; do
        stop_webapp $webapp_name $shutdown_time &
        pids+=($!)
    done
    for pid in ${pids[@]}; do
        wait $pid || is_success=1
    done
    kill_process_by_search_string "node.*log"
    return $is_success
}

function start_default_workers() {
    echo "Starting default workers $DEFAULT_WORKER_EXECUTABLES" 1>&2
    for executable in ${DEFAULT_WORKER_EXECUTABLES//,/ };do
        stop_default_worker $executable
        echo "Starting default workers - $executable"
        pid_filename=$BASE_DIR/${executable}.pid
        export LOG_FILE=${LOGDIR}/${executable##*/}_${LOG_APPEND_TEXT}_stderr.log
        STDOUT_FILE=${LOGDIR}/${executable##*/}_${LOG_APPEND_TEXT}_stdout.log
        STDERR_FILE=${LOGDIR}/${executable##*/}.log
        nohup $executable 1>> ${STDOUT_FILE} 2>> ${STDERR_FILE} &
        w_pid=$!
        echo $w_pid > $pid_filename
        echo "Default worker $executable started with PID $w_pid" 1>&2
    done
}


function start_worker() {
    worker_name=$1
    entry_point=$( echo $worker_name | awk -F"/" '{print $2}' )
    if [[ -n $entry_point ]]; then
        worker_name=$( echo $worker_name | awk -F"/" '{print $1}' )
    fi
    is_foreground=${2:-0}
    shutdown_time=${3:-130}
    worker_type=${4:-workers}
    echo "Checking for $worker_type $worker_name/$entry_point with a timeout of $shutdown_time seconds" 1>&2
    stop_worker $worker_name $shutdown_time $worker_type
    if [ $? -ne 0 ];then
        echo "Failed to stop worker $worker_name" 1>&2
        echo "Not starting worker $worker_name" 1>&2
        return 1
    fi
    echo "Starting $worker_type $worker_name"
    is_success=0
    if [ -z $entry_point ];then
        entry_points=( `jq -r ".${worker_type}[] | select(.name == \"${worker_name}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.entry_point'` )
    else
        entry_points=( $entry_point )
    fi
    for entry_point in ${entry_points[@]}; do
        if [[ $PRIMARY == 0 ]];then
            primary=""
        else
            primary="--primary "
        fi
        if [[ $PARALLEL_THREADS != 0 ]];then
            parallel_threads=${PARALLEL_THREADS}
        else
            parallel_threads=`jq -r ".${worker_type}[] | select(.name == \"${worker_name}\" and .entry_point == \"${entry_point}\")" ${BASE_DIR}/start_worker_config.json | jq '.parallel_threads'`
        fi
        if [[ $SHUTDOWN_TIME != 0 ]];then
            shutdown_time=${SHUTDOWN_TIME}
        else
            shutdown_time=`jq -r ".${worker_type}[] | select(.name == \"${worker_name}\" and .entry_point == \"${entry_point}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.shutdown_time'`
        fi
        worker_fname=${entry_point%.*}
        pid_filename=$BASE_DIR/${worker_name}_${worker_fname}.pid
        export LOG_FILE=${LOGDIR}/${worker_name}_${worker_fname##*/}_${LOG_APPEND_TEXT}.log
        STDOUT_FILE=${LOGDIR}/${worker_name}_${worker_fname##*/}_${LOG_APPEND_TEXT}_stdout.log
        STDERR_FILE=${LOGDIR}/${worker_name}_${worker_fname##*/}_${LOG_APPEND_TEXT}_stderr.log
        pushd $BASE_DIR > /dev/null
        if [ $worker_type == "workers" ];then
            entry_point=${worker_name}/${entry_point}
        elif [ $worker_type == "agents" ];then
            entry_point=agents/${entry_point}
        else
            echo "Invalid worker type $worker_type" 1>&2
            return 1
        fi
        echo "Running command: nohup $WORKER_PATH -m ${entry_point} -n $parallel_threads --shutdown-time=$shutdown_time $primary 1>> ${STDOUT_FILE} 2>> ${STDERR_FILE} &" 1>&2
        nohup $WORKER_PATH -m ${entry_point} -n $parallel_threads --shutdown-time=$shutdown_time $primary 1>> ${STDOUT_FILE} 2>> ${STDERR_FILE} &
        w_pid=$!
        echo $w_pid > ${pid_filename}
        echo "$worker_type $worker_name started with PID $w_pid" 1>&2
        popd > /dev/null
        if [[ $is_foreground != 0 ]];then
            tail -f --follow=name --retry ${LOG_FILE}
            stop_worker $worker_name $shutdown_time $worker_type
        fi
    done
    return $is_success
}

function start_agent() {
    agent_name=$1
    entry_point=$( echo $agent_name | awk -F"/" '{print $2}' )
    is_foreground=${2:-0}
    shutdown_time=${3:-130}
    echo "Starting agent $agent_name/$entry_point with a timeout of $shutdown_time seconds: foreground? $is_foreground" 1>&2
    start_worker $agent_name $is_foreground $shutdown_time agents
    return $?
}

function start_webapp() {
    webapp_name=$1
    is_foreground=${2:-0}
    shutdown_time=${3:-130}
    echo "Starting webapp $webapp_name with a timeout of $shutdown_time seconds: foreground? $is_foreground" 1>&2
    stop_webapp $webapp_name $shutdown_time
    if [ $? -ne 0 ];then
        echo "Failed to stop webapp $webapp_name" 1>&2
        echo "Not starting webapp $webapp_name" 1>&2
        return 1
    fi
    echo "Starting webapp $webapp_name"
    webapp_app_name=`jq -r ".webapps[] | select(.name == \"${webapp_name}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.name'`
    webapp_port=`jq -r ".webapps[] | select(.name == \"${webapp_name}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.port'`
    webapp_url_scheme=`jq -r ".webapps[] | select(.name == \"${webapp_name}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.url_scheme'`
    webapp_api_threads=`jq -r ".webapps[] | select(.name == \"${webapp_name}\")" ${BASE_DIR}/start_worker_config.json | jq -r '.api_threads'`
    if [[ $webapp_app_name == null ]];then
        webapp_app_name=`jq -r '.webapp.name' ${BASE_DIR}/start_worker_config.json`
        webapp_port=`jq -r '.webapp.port' ${BASE_DIR}/start_worker_config.json`
        webapp_url_scheme=`jq -r '.webapp.url_scheme' ${BASE_DIR}/start_worker_config.json`
        webapp_api_threads=`jq -r '.webapp.api_threads' ${BASE_DIR}/start_worker_config.json`
    fi
    webapp_port=${webapp_port:-${SERVER_PORT}}
    webapp_url_scheme=${webapp_url_scheme:-http}
    webapp_api_threads=${webapp_api_threads:-1}
    if [[ $API_THREADS != 0 ]];then
        webapp_api_threads=${API_THREADS}
    fi
    pids=()
    is_success=0
    if [[ $PRIMARY != 0 ]];then
        for i in $(seq $webapp_api_threads); do
            pid_filename=$BASE_DIR/${webapp_name}_${i}.pid
            port=$((webapp_port + i - 1))
            export LOG_FILE=${LOGDIR}/${webapp_name}_${i}_${LOG_APPEND_TEXT}_stderr.log
            STDOUT_FILE=${LOGDIR}/${webapp_name}_${i}_${LOG_APPEND_TEXT}_stdout.log
            STDERR_FILE=${LOGDIR}/${webapp_name}_${i}_${LOG_APPEND_TEXT}.log
            nohup $WAITRESS_PATH --ident="" --port=${port} --url-scheme=${webapp_url_scheme} --threads=1 ${webapp_app_name}:app 1>> ${STDOUT_FILE} 2>> ${STDERR_FILE} &
            w_pid=$!
            echo $w_pid >> ${pid_filename}
            echo "Webapp $webapp_name started with PID $w_pid" 1>&2
            pids+=($w_pid)
        done
    else
        export LOG_FILE=${LOGDIR}/${webapp_name}_stderr.log
        STDOUT_FILE=${LOGDIR}/${webapp_name}_${LOG_APPEND_TEXT}_stdout.log
        STDERR_FILE=${LOGDIR}/${webapp_name}_${LOG_APPEND_TEXT}.log
        nohup $WAITRESS_PATH --ident="" --port=${WEBAPP_PORT} --url-scheme=${WEBAPP_URL_SCHEME} --threads=${WEBAPP_API_THREADS} ${WEBAPP_APP_NAME}:app 1>> ${STDOUT_FILE} 2>> ${STDERR_FILE} &
        w_pid=$!
        echo $w_pid >> ${pid_filename}
        echo "Webapp $webapp_name started with PID $w_pid" 1>&2
        pids+=($w_pid)
    fi
    if [[ $is_foreground != 0 ]];then
        tail -f --follow=name --retry ${LOG_FILE}
        stop_webapp $webapp_name $shutdown_time
    fi
    return $is_success
}

function post_models() {
    # To post models, this is required in the beginning, first time only.
    # e.g. post_models "model1" "model2"
    pushd $BASE_DIR > /dev/null
    python config.py --post-models "$@"
    popd > /dev/null
}

function post_data() {
    # To post data, this is required in the beginning, first time only.
    # e.g. post_data "model1" "model2"
    pushd $BASE_DIR > /dev/null
    python config.py --post-data "$@"
    popd > /dev/null
}

function startup() {
    # To start up all the workers and webapps in GKE, this is required in the beginning
    # e.g. startup
    pushd $BASE_DIR > /dev/null
    python config.py --startup "$@"
    popd > /dev/null
}

function copy_ai_models() {
    # To start up all the workers and webapps in GKE, this is required in the beginning
    # e.g. copy_ai_models "autobot-staging-db-secret" "gcp" to copy from stable to current environment
    pushd $BASE_DIR > /dev/null
    python config.py --source-ai-secret-id "$1" --source-ai-cloud "$2"
    popd > /dev/null
}

function add_origin() {
    pushd $BASE_DIR > /dev/null
    python -c "import app; from gryd_worker import gryd_routes as rts; ca = rts.get_auth_connect(); ca.add_origin(app.AUTOCRM_APP_ENTERPRISE_ID, '$1'); ca.close()"
    popd > /dev/null
}


function setup() {
    # To setup the environment, this is required in the beginning, first time only.
    # e.g.
    # setup --new-db --new-environment --reseed
    # To reseed all the data
    # setup --reseed
    # To only setup models and data
    # setup --skip-cron --skip-sp --start-models-from "model1" --start-data-from "data1"
    # To only setup cron, and stored procedures
    # setup --skip-models --skip-data        
    pushd $BASE_DIR > /dev/null
    python app.py --setup "$@"
    popd > /dev/null
}

function wait_for_all_processes() {
    # Wait for all processes to terminate. 
    # If wait_for_all is 0, stop all workers and exit if any one process is killed. 
    # If wait_for_all is 1, wait for all processes to terminate and exit.
    pids=()
    process_files=()
    wait_for_all=${1:-0}
    for pid_filename in `ls -1 $BASE_DIR/*.pid 2> /dev/null | sort`; do
        pid=$(cat $pid_filename)
        if [[ -n $pid ]];then
            pids+=($pid)
            process_files+=( $pid_filename )
        fi
    done
    echo "Waiting for any one of the processes to be killed: $process_files" 1>&2
    while true; do
        for i in $(seq 0 $(( ${#pids[@]} - 1)) ); do
            pid=${pids[$i]}
            fpid=${process_files[$i]}
            if is_process_running $pid;then
                echo "Process $pid is still running. Waiting..." 1>&2
                sleep 10
            elif [[ $wait_for_all == 0 ]];then
                echo "WARNING!!!!: Process $pid in worker/app $fpid has terminated." 1>&2
                echo "Stopping all workers." 1>&2
                stop_all_workers
                echo "Exiting..." 1>&2
                return 0
            elif [[ $wait_for_all != 0 ]];then
                unset pids[$i]
                if [ ${#pids[@]} -eq 0 ];then # If all processes are terminated, exit.
                    echo "All processes terminated." 1>&2
                    echo "Exiting..." 1>&2
                    return 0
                fi
                break # Break the for loop if any process is terminated.
            fi
        done
    done
    return 0
}

function start_all() {
    echo "Starting all workers and webapps" 1>&2
    if [[ $SETUP_WEBAPP == "True" ]];then
        echo "Setting up webapp. Since SETUP_WEBAPP is True." 1>&2
        if [[ $START_WEBAPP == 1 ]];then
            echo "Getting webapp names from start_worker_config.json" 1>&2
            START_WEBAPP=`jq -r '.webapps[].name' ${BASE_DIR}/start_worker_config.json | sort -u | tr '\n' ',' | sed 's/,$//'`
            if [[ $START_WEBAPP == null ]];then
                echo "Getting webapp name from start_worker_config.json" 1>&2
                START_WEBAPP=`jq -r '.webapp.name' ${BASE_DIR}/start_worker_config.json`
            fi
        elif [[ $START_WEBAPP == 0 ]];then
            START_WEBAPP=""
        fi
        echo "Starting webapps $START_WEBAPP" 1>&2
        for webapp_name in ${START_WEBAPP//,/ }; do
            start_webapp $webapp_name
        done
    else
        echo "Not setting up webapp. Since SETUP_WEBAPP is not True." 1>&2
    fi
    if [[ $SETUP_WORKERS != "True" ]];then
        echo "Not setting up workers. Since SETUP_WORKERS is not True." 1>&2
        #return
    fi
    if [[ $DEFAULT_WORKERS == 0 || -z $DEFAULT_WORKERS ]] ;then
        echo "Not setting up default workers. Since DEFAULT_WORKERS is 0 or not set." 1>&2
        #return
    else
	    start_default_workers
    fi

    if [[ $START_AGENTS == 1 ]]; then
        START_AGENTS=`jq -r '.agents[].name' ${BASE_DIR}/start_worker_config.json | sort -u | tr '\n' ',' | sed 's/,$//'`
    elif [[ $START_AGENTS == 0 ]]; then
        START_AGENTS=""
    fi
    echo "Starting agents $START_AGENTS" 1>&2
    for agent_name in ${START_AGENTS//,/ }; do
        start_agent $agent_name
    done

    if [[ $START_WORKERS == 1 ]];then
        START_WORKERS=`jq -r '.workers[].name' ${BASE_DIR}/start_worker_config.json | sort -u | tr '\n' ',' | sed 's/,$//'`
    #elif [[ $START_WORKERS == 0 ]];then
    #    START_WORKERS=""
    fi
    echo "Starting workers $START_WORKERS" 1>&2
    for worker_name in ${START_WORKERS//,/ }; do
        start_worker $worker_name
    done

    sleep 5
    ls $LOG_FILE
    echo "Setting up logio agent."
    if [ $SETUP_LOGIO_AGENT == "True" ];then
        sleep 30
        setup_logio_agent
        echo "##########################"
        cat /root/app/logio_conf.json
        echo "##########################"
        cat $LOG_FILE
    fi
}
