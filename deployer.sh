#!/bin/bash

# Path to your project
AUTOBOT_AGENT_PATH="/mnta/autobot_agents"

# Go to the project directory
cd "$AUTOBOT_AGENT_PATH" || exit 1

# Activate virtual environment
source .env/bin/activate

# Gryd File Uploader Creds: 
export AUTH_HOST_USER_ID=
export AUTH_HOST=
export AUTH_HOST_API=
export AUTH_HOST_ENTERPRISE_ID=

# Comparision Agent Creds:
export CARDB_USER_ID=
export CARDB_API_KEY=
export CARDB_ENTERPRISE_ID=

# Dealer Creds:
export DEALER_ENTERPRISE_ID=
export DEALER_API_KEY=
export DEALER_USER_ID=

# AWS Credentials:
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export AWS_DEFAULT_REGION=

# RDS Postgres Credentials:
export POSTGRES_URL=
export RDS_SECRET=
export CLOUD_DATABASE=

# Gryd Worker Env: (This environment should be set in Gryd worker as well)
export ENVIRONMENT="test"

kill_worker() {
    echo "---- Checking GRYD Worker ----"
    WORKER_PID=$(ps -eaf | grep '[t]asks' | awk '{print $2}')
    if [ -n "$WORKER_PID" ]; then
        echo "Found GRYD worker (PID: $WORKER_PID). Killing..."
        kill -9 "$WORKER_PID"
    else
        echo "No GRYD worker running."
    fi
}

start_worker() {
    echo "---- Starting GRYD Worker ----"
    touch out.log
    nohup worker -m tasks.py -n 8 >> out.log 2>&1 &
    echo "GRYD worker started."
}

kill_streamlit() {
    echo "---- Checking Streamlit ----"
    APP_PID=$(ps -eaf | grep '[s]treamlit' | awk '{print $2}')
    if [ -n "$APP_PID" ]; then
        echo "Found Streamlit (PID: $APP_PID). Killing..."
        kill -9 "$APP_PID"
    else
        echo "No Streamlit app running."
    fi
}

start_streamlit() {
    echo "---- Starting Streamlit Dashboard ----"
    touch dashboard.log
    nohup streamlit run dashboard.py \
        --server.enableCORS false \
        --server.enableXsrfProtection false \
        --server.port 8501 \
        --server.address 0.0.0.0 >> dashboard.log 2>&1 &
    echo "Streamlit dashboard started."
}


if [[ "$1" == "only_kill" ]]; then
    echo "======================================="
    echo "       ONLY KILLING PROCESSES"
    echo "======================================="

    kill_worker
    kill_streamlit

    echo "======================================="
    echo "   Processes killed. No restart done."
    echo "======================================="
    exit 0
fi

echo "======================================="
echo "   Restarting GRYD Worker & Streamlit"
echo "======================================="

kill_worker
start_worker

kill_streamlit
start_streamlit

echo "======================================="
echo "        All services restarted"
echo "======================================="

# echo "======================================="
# echo "      Restarting GRYD Worker"
# echo "======================================="

# # Find running GRYD worker (tasks.py)
# WORKER_PID=$(ps -eaf | grep '[t]asks' | awk '{print $2}')

# if [ -n "$WORKER_PID" ]; then
#     echo "Found existing gryd worker (PID: $WORKER_PID). Killing..."
#     kill -9 "$WORKER_PID"
# else
#     echo "No existing worker found."
# fi

# # Start new GRYD worker
# echo "Starting new gryd worker..."
# touch out.log
# nohup worker -m tasks.py -n 8 >> out.log 2>&1 &
# echo "GRYD worker started."

# echo

# echo "======================================="
# echo "     Restarting Streamlit Dashboard"
# echo "======================================="

# # Find running Streamlit process
# APP_PID=$(ps -eaf | grep '[s]treamlit' | awk '{print $2}')

# if [ -n "$APP_PID" ]; then
#     echo "Found existing Streamlit app (PID: $APP_PID). Killing..."
#     kill -9 "$APP_PID"
# else
#     echo "No existing Streamlit app found."
# fi

# # Start Streamlit dashboard
# echo "Starting new Streamlit dashboard..."
# touch dashboard.log
# nohup streamlit run dashboard.py \
#     --server.enableCORS false \
#     --server.enableXsrfProtection false \
#     --server.port 8501 \
#     --server.address 0.0.0.0 >> dashboard.log 2>&1 &
# echo "Streamlit dashboard started."

# echo
# echo "======================================="
# echo "          All services started"
# echo "======================================="
