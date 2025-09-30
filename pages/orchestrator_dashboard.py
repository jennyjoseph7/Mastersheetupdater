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

st.set_page_config(page_title="Multi-Agent Orchestrator Streaming", layout="wide")
st.markdown("## 🕵🏻 **Multi-Agent Orchestrator Streaming**")

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

user_query = st.text_input("Enter your query and press Enter to run")
if user_query:
    st.write(f"Running Orchestrator for: '{user_query}'")
    all_results = []
    for result in run_orchestrator(user_query):
        all_results.append(result)
        if "reasoning" in result:
            st.markdown("#### <Query Orchestrator Reasoning>")
            st.info(result["reasoning"])
            continue

        if result.get("task") == "aem_integration_agent":
            continue
        
        if "propensity_agent_results" in result:
            propensity_result = result.get("propensity_agent_results")
            st.success("✅ Propensity Scores Computed Successfully")
            scores = propensity_result.get("scores")
            propensity_img_url = propensity_result.get("propensity_chart_url")
            reasoning = propensity_result.get("reasoning")
            propensity_chart_json = propensity_result.get("propensity_chart_json")
            if reasoning:
                st.markdown("#### <Propensity Agent Reasoning>")
                response = st.write_stream(response_generator(response = reasoning))
                st.write("Propensity Scores:")
                st.json(scores)
            if propensity_chart_json:
                fig = pio.from_json(propensity_chart_json)
                st.plotly_chart(fig, use_container_width=True)
            elif propensity_img_url:
                st.write("Propensity Chart:")
                st.image(propensity_img_url, width=800,)

        def show_dealer_locations(dealer_locator_result):
            import pydeck as pdk
            st.subheader("🔎 Dealer Locator Agent")
            if not dealer_locator_result:
                st.info("ℹ️ Dealer locator agent yet to be written.")
                return
            
            location_data = dealer_locator_result["location"]
            for loc in location_data:
                if "error" in loc:
                    return {"error" : loc} 
            
            st.success("✅ Dealer Locator Computed Successfully")
            with st.expander("📦 Raw Data"):
                st.json(dealer_locator_result)

            locations_for_map = []
            for dealer in location_data:
                if "location" in dealer and dealer["location"]:
                    try:
                        lat, lon = map(float, dealer["location"].split(","))
                        locations_for_map.append({
                            "Dealer": dealer.get("dealer_name", "Unknown"),
                            "Address": dealer.get("dealer_address", "N/A"),
                            "Latitude": lat,
                            "Longitude": lon,
                        })
                    except:
                        pass

            if locations_for_map:
                df_map = pd.DataFrame(locations_for_map)
                #Center map around first dealer
                view_state = pdk.ViewState(
                    latitude=df_map["Latitude"].mean(),
                    longitude=df_map["Longitude"].mean(),
                    zoom=12,
                    pitch=0,
                )
                #dealer markers with tooltips
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_map,
                    get_position="[Longitude, Latitude]",
                    get_color="[200, 30, 0, 160]",
                    get_radius=100,
                    pickable=True,
                )

                tooltip = {
                    "html": "<b>{Dealer}</b><br/>{Address}",
                    "style": {"backgroundColor": "steelblue", "color": "white"},
                }

                st.pydeck_chart(pdk.Deck(
                    # map_style="mapbox://styles/mapbox/streets-v12",
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
                    initial_view_state=view_state,
                    layers=[layer],
                    tooltip=tooltip,
                ))
            for dealer in location_data:
                with st.container():
                    with st.expander(f"🏢 {dealer.get('dealer_name', 'Unknown')}"):
                        st.write(f"**Address:** {dealer.get('dealer_address', 'N/A')}")
                        st.write(f"**City:** {dealer.get('dealer_city', 'N/A')} ({dealer.get('dealer_state', 'N/A')})")
                        st.write(f"**Pincode:** {dealer.get('dealer_pincode', 'N/A')}")
                        st.write(f"**Channel:** {dealer.get('dealer_channel', 'N/A')}")
                        st.write(f"**Type:** {dealer.get('dealer_type_name', 'N/A')}")
                        st.write(f"**Open Hours:** {dealer.get('open_hours', 'N/A')}")
                        st.write(f"**Contact Group:** {dealer.get('parent_group', 'N/A')}")
                        st.write(f"**Active:** {'✅ Yes' if dealer.get('is_active') else '❌ No'}")
                        if "location" in dealer and dealer["location"]:
                            st.write(f"**Coordinates:** {dealer['location']}")
        
        if "dealer_locator_agent_results" in result:
            dealer_locator_result = result.get("dealer_locator_agent_results")
            show_dealer_locations(dealer_locator_result)
        
        if "competitor_analysis_agent_results" in result:
            competitor_result = result.get("competitor_analysis_agent_results")
            st.json(competitor_result)
        
        if "personalization_agent_results" in result:
            personalization_result = result.get("personalization_agent_results")
            st.success("✅ Personalization Computed Successfully")
            reasoning = personalization_result.get("reasoning")
            if reasoning:
                st.markdown("#### <Personalization Agent Reasoning>")
                response = st.write_stream(response_generator(response = reasoning))
            message = personalization_result.get("personalization_agent_response")
            # st.text_area("Personalization Message : ", message, height=600)
            st.write(message)
        
        if "sentiment_analysis_agent_results" in result:
            sentiment_result = result.get("sentiment_analysis_agent_results")
            st.success("✅ Sentiment Computed Successfully")
            reasoning = sentiment_result.get("reasoning")
            if reasoning:
                st.markdown("#### <Sentiment Agent Reasoning>")
                response = st.write_stream(response_generator(response = reasoning))
            if isinstance(sentiment_result, dict):
                st.info(f"**User Input:** {sentiment_result.get('user_input')}\n\n**Justification:** {sentiment_result.get('justification')} \n\n**Emotions:** {sentiment_result.get('emotions')}\n\n**Sentiment Score:** {sentiment_result.get('sentiment_score')}")
            # st.text_area("Sentiment Message : ", message, height=600)
        
        if "communication_agent_results" in result:
            communication_result = result.get("communication_agent_results")
            st.success("✅ Communication Computed Successfully")
            reasoning = communication_result.get("reasoning")
            if reasoning:
                st.markdown("#### <Communication Agent Reasoning>")
                response = st.write_stream(response_generator(response = reasoning))
            status = communication_result.get("status", "unknown")
            email_draft = communication_result.get("email_draft")
            result_message = communication_result.get("communication_agent_result", "")
            error = communication_result.get("error")
            if status == "success":
                st.success("✅ Email Sent Successfully!")
                if email_draft:
                    st.write("✉️ Email Content:")
                    with st.expander("View Email", expanded=True):
                        if isinstance(email_draft, dict):
                            subject = email_draft.get('subject', '(No Subject)')
                            message = email_draft.get('message', '')
                            st.markdown(f"**📌 Subject:** {subject}") # Subject
                            st.divider()# Divider
                            st.markdown("**Body:**")# Body
                            st.markdown(f"> {message}")
                        else:
                            st.write(email_draft)

            elif status == "error":
                st.error("❌ Email Sending Failed!")
            elif status == "failed" or "not sent" in result_message.lower():
                st.warning("⚠️ Email Not Sent")
        
        if "prioritization_agent_results" in result:
            prioritization_result = result.get("prioritization_agent_results")
            st.success("✅ Priority Computed Successfully")
            st.write("🧾 Prioritization Results")
            st.markdown("#### 🔍 Prioritization Summary")
            top_fields = ["priority_level", "prioritization_score", "risk_factors", "talking_points", "recommended_actions"]
            for field in top_fields:
                value = prioritization_result.get(field)
                if value:
                    st.markdown(f"**{field.replace('_', ' ').title()}:**")
                    if isinstance(value, list):
                        for item in value:
                            st.markdown(f"- {item}")
                    else:
                        st.markdown(f"`{value}`")
            st.markdown("### 👤 Customer Summary")

            customer_summary = prioritization_result.get("customer_summary", {})
            if customer_summary:
                for section_title, section_data in customer_summary.items():
                    st.markdown(f"#### 📂 {section_title.replace('_', ' ').title()}")
                    if isinstance(section_data, dict):
                        summary_df = pd.DataFrame(list(section_data.items()), columns=["Key", "Value"])
                        st.dataframe(summary_df, use_container_width=True)
                    elif isinstance(section_data, list):
                        list_df = pd.DataFrame({section_title: section_data})
                        st.dataframe(list_df, use_container_width=True)
                    else:
                        st.markdown(f"- `{section_data}`")
            else:
                st.warning("No customer summary found.")

        if "conclusive_reasoning" in result:
            conclusive_reasoning = result.get("conclusive_reasoning")
            st.write("🧾 Conclusive Reasoning")
            st.success(conclusive_reasoning)
           

    # Full Debug
    with st.expander("Full Debug"):
        st.json(all_results)


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
