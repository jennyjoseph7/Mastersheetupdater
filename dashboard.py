import streamlit as st
import json
from gryd_worker import gryd
from utils import *
import plotly.io as pio

logger = get_logger(__name__)
gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config=GRYD_CONFIG)

st.set_page_config(page_title="AutoBot Agents", layout="wide")
st.title("AutoBot Agents")
st.header("Gryd Dashboard")

uploaded_file = st.sidebar.file_uploader("📁 Upload JSON file", type=["json"])
run_agent = st.sidebar.button("Run Agents 🚀")
if not uploaded_file:
    st.warning("⚠️ Please upload a valid JSON file.")

tab1, tab2, tab3 = st.tabs(["Propensity Agent", "Comparison Analysis Agent", "Personalization Agent"])

propensity_result = None
competitor_result = None
personalization_result = None

if run_agent:
    try:
        input_data = json.load(uploaded_file)
        autobot_agents_trigger = [{
            "task": "autobot_agents_trigger",
            "service": GRYD_SERVICE,
            "kwargs": {
                "source": input_data,
                "execution_mode": "async"
            },
            "args": (None)
        }]

        sync_result = gryd.await_results(autobot_agents_trigger)
        sync_result = list(sync_result[0])
        logger.info(json.dumps(sync_result, indent=4, default=str))
        # assert False
        for job in sync_result:
            
            task_name = job.get("task")

            if task_name == "propensity_agent":
                propensity_result = job
            elif task_name == "competitor_analysis_agent":
                competitor_result = job
            elif task_name == "personalization_agent":
                personalization_result = job

            # task_name, status, result_data = job[1], job[3], job[4]

            # if status == "result":
            #     logger.info(f"Result found at Index: {idx}")
            #     agent_results_list = result_data

            #     for agent_result in agent_results_list:
            #         task = agent_result.get("task")
            #         if task == "propensity_agent":
            #             propensity_result = agent_result
            #         elif task == "competitor_analysis_agent":
            #             competitor_result = agent_result
            #         elif task == "personalization_agent":
            #             personalization_result = agent_result
    except Exception as e:
        traceback.print_exc()
        st.error(f"❌ Agent failed: {str(e)}")

# Propensity Agent tab
with tab1:
    st.subheader("🧠 Propensity Agent")
    if propensity_result:
        scores = propensity_result.get("scores")
        propensity_img_url = propensity_result.get("propensity_chart_url")
        propensity_chart_json = propensity_result.get("propensity_chart_json")
        fig = pio.from_json(propensity_chart_json)
        st.success("✅ Propensity Scores Computed Successfully")
        st.markdown("### 📊 Propensity Scores")
        st.json(scores)
        if fig:
            st.markdown("### 📷 Propensity Chart")
            st.plotly_chart(fig, use_container_width=True)
            # st.image(propensity_img_url, width=1000,) # caption=" ### 📷 Propensity Score Radar Plot"
    else:
        st.info("ℹ️ Run the agent to see results.")

# Competitor Analysis tab
with tab2:
    st.subheader("📈 Competitor Analysis Agent")
    if competitor_result:
        st.success("✅ Competitor Analysis Computed Successfully")
        st.markdown("### 🧾 Competitor Analysis Results")
        if isinstance(competitor_result, dict):
            st.json(competitor_result)
        else:
            st.write(competitor_result)
    else:
        st.info("ℹ️ No competitor data yet.")

with tab3:
    st.subheader("🧠 Personalization Agent")
    if personalization_result:
        st.success("✅ Personalization Computed Successfully")
        st.markdown("### 🧾 Personalization Results")
        if isinstance(personalization_result, dict):
            st.json(personalization_result)
        else:
            st.write(personalization_result)
    else:
        st.info("ℹ️ No personalization data yet.")

