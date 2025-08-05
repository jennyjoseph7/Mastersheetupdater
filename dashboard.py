import streamlit as st
import json
from gryd_worker import gryd
from utils import *
import plotly.io as pio
import pandas as pd

logger = get_logger(__name__)
gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config=GRYD_CONFIG)

st.set_page_config(page_title="AutoBot Agents", layout="wide")
st.markdown("## 🤖 **AutoBot Agents**")

uploaded_file = st.sidebar.file_uploader("📁 Upload JSON file", type=["json"])
run_agent = st.sidebar.button("Run Agents 🚀")
if not uploaded_file:
    st.warning("⚠️ Please upload a valid JSON file.")

tab1, tab2, tab3 = st.tabs(["Propensity Agent", "Comparison Analysis Agent", "Personalization Agent"])

propensity_result = None
competitor_result = None
personalization_result = None

if run_agent:
    with st.spinner("Running agents..."):
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
    # st.success("Done!")


# Propensity Agent tab
with tab1:
    st.subheader("🧠 Propensity Agent")
    if propensity_result:
        scores = propensity_result.get("scores")
        propensity_img_url = propensity_result.get("propensity_chart_url")
        # propensity_chart_json = propensity_result.get("propensity_chart_json")
        # fig = pio.from_json(propensity_chart_json)
        st.success("✅ Propensity Scores Computed Successfully")
        st.write("Propensity Scores:")
        st.json(scores)
        # if fig:
        #     st.markdown("### 📷 Propensity Chart")
        #     st.plotly_chart(fig, use_container_width=True)
            # st.image(propensity_img_url, width=1000,) # caption=" ### 📷 Propensity Score Radar Plot"
        if propensity_img_url:
            st.write("Propensity Chart:")
            st.image(propensity_img_url, width=1000,)
    else:
        st.info("ℹ️ Run the agent to see results.")

# Competitor Analysis tab

with tab2:
    st.subheader("📈 Competitor Analysis Agent")

    if competitor_result:
        st.success("✅ Competitor Analysis Computed Successfully")
        st.markdown("#### 🚗 Car Variants")

        # Show car variant details in tabular format
        car_variants = []
        for car_group in competitor_result.get("compared_cars_data", []):
            for variant in car_group:
                car_variants.append({
                    "brand": variant.get("brand"),
                    "Product Name": variant.get("product_name"),
                    "Variant": variant.get("variant"),
                    "Fuel Type": variant.get("fuel_type"),
                    "Price (₹)": float(variant.get("price", 0)),
                    "Engine": variant.get("technology_and_performance", [])[0] if variant.get("technology_and_performance") else "N/A",
                    "Transmission": variant.get("general", [])[3] if variant.get("general") and len(variant.get("general")) > 3 else "N/A",
                    "Safety & Environment" : variant.get("safety_and_environment", [])
                })

        if car_variants:
            car_df = pd.DataFrame(car_variants)
            st.dataframe(car_df, use_container_width=True)

        # Show Key Comparisons
        st.markdown("#### 🔍 Key Comparisons")
        comparisons = competitor_result.get("comparisons", {})
        for comparison_title, metrics in comparisons.items():
            st.markdown(f"#### {comparison_title}")
            comparison_df = pd.DataFrame(metrics).T.reset_index()
            comparison_df.columns = ['Feature'] + list(comparison_df.columns[1:])
            st.dataframe(comparison_df, use_container_width=True)

        # Show Common Points
        st.markdown("#### 🔗 Common Points")
        common_points = competitor_result.get("common_points", [])
        if common_points:
            common_df = pd.DataFrame(common_points, columns=["Common Features"])
            st.dataframe(common_df, use_container_width=True)

        # Show Key Differences
        st.markdown("####  ⚖️ Key Differences")
        key_diff = competitor_result.get("key_differences", {})
        for key, val in key_diff.items():
            st.markdown(f"#### 🔸 {key.replace('_', ' ').title()}")
            diff_df = pd.DataFrame(val.items(), columns=["Model", key.replace('_', ' ').title()])
            st.dataframe(diff_df, use_container_width=True)

        # User Choice Justification
        st.markdown("#### ✅ User Choice Justification")
        user_just = competitor_result.get("user_choice_justification", {})
        for model, reason in user_just.items():
            st.markdown(f"**{model}**")
            st.info(reason)

    else:
        st.info("ℹ️ Run the agent to see results.")

with tab3:
    st.subheader("🧠 Personalization Agent")
    if personalization_result:
        st.success("✅ Personalization Computed Successfully")
        st.markdown("####  🧾 Personalization Results")
        if isinstance(personalization_result, dict):
            message = personalization_result.get("personalization_agent_response")
            st.text_area("Personalization Message : ", message, height=200)
    else:
        st.info("ℹ️ No personalization data yet.")

