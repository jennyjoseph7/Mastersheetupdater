import streamlit as st
import time
import json
from gryd_worker import gryd
from utils import *
import plotly.io as pio
import pandas as pd
import os, sys, traceback

logger = get_logger(__name__)
gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config=GRYD_CONFIG)

st.set_page_config(page_title="Agent Orchestrator Streaming", layout="wide")
st.markdown("## 🕵🏻 **Agent Orchestrator Streaming**")

uploaded_file = st.sidebar.file_uploader("📁 Upload JSON file", type=["json"])
if uploaded_file:
    try:
        input_data = json.load(uploaded_file)
        st.sidebar.success("✅ Customer data parsed successfully!")
        st.sidebar.json(input_data)
    except Exception as e:
        st.sidebar.error(f"❌ Failed to parse JSON: {e}")
else:
    st.sidebar.warning("⚠️ Please upload a valid JSON file.")

def run_orchestrator(query: str):
    job = {
        "task": "query_orchestrator",
        "service": GRYD_SERVICE,
        "kwargs": {
            "source" : input_data,
            "user_query" : query
        },
            "args": (None)
        }

    async_job = [job]
    for job in gryd.yield_results(async_job):
        task_name, status, result_data = job[1], job[3], job[4]
        if status == "result":
            logger.info(f"Task '{task_name}' yielded result: {json.dumps(result_data, indent = 4, default = str)} \n")
            yield result_data

def orchestrator(query: str):
    yield {"agent": "AEM", "status": "running"}
    time.sleep(1)
    yield {"agent": "AEM", "status": "done"}
    time.sleep(1)
    yield {"agent": "Propensity", "status": "done"}
    time.sleep(1)
    yield {"agent": "Personalization", "result": "Email generated"}

def response_generator(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

user_query = st.text_input("Enter your query")

if st.button("Run Orchestrator") and user_query:
    for result in run_orchestrator(user_query):

        if "reasoning" in result:
            st.info(result["reasoning"])
            continue

        if result.get("task") == "aem_integration_agent":
            # st.json(result)
            continue
        
        if "propensity_agent_result" in result:
            propensity_result = result.get("propensity_agent_result")
            st.success("✅ Propensity Scores Computed Successfully")
            scores = propensity_result.get("scores")
            propensity_img_url = propensity_result.get("propensity_chart_url")
            reasoning = propensity_result.get("reasoning")
            if reasoning:
                st.markdown("#### <Agent Reasoning>")
                response = st.write_stream(response_generator(response = reasoning))
                st.write("Propensity Scores:")
                st.json(scores)
            if propensity_img_url:
                st.write("Propensity Chart:")
                st.image(propensity_img_url, width=1000,)
        
        st.json(result)


        # agent = step.get("agent", "")

        # if agent == "AEM":
        #     st.success(f"AEM → {step}")
        # elif agent == "Propensity":
        #     st.info(f"Propensity → {step}")
        # elif agent == "Personalization":
        #     st.warning(f"Personalization → {step}")
        # else:
        #     st.json(step)

        # time.sleep(0.1)
