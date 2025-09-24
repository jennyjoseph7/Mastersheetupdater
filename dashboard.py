import streamlit as st
import json
from gryd_worker import gryd
from utils import *
import plotly.io as pio
import pandas as pd
import os, sys, traceback
import pydeck as pdk

logger = get_logger(__name__)
gryd.SERVICE = GRYD_SERVICE
gryd.set_queue_manager(config=GRYD_CONFIG)
environment = os.getenv("ENVIRONMENT", "-local")
if not environment.startswith("-"):
    environment = f"-{environment}"
gryd.ENVIRONMENT = environment
st.set_page_config(page_title="AutoBot Agents", layout="wide")
st.markdown("## 🤖 **AutoBot Agents**")

uploaded_file = st.sidebar.file_uploader("📁 Upload JSON file", type=["json"])
if uploaded_file:
    try:
        input_data = json.load(uploaded_file)
        st.sidebar.success("✅ Customer data parsed successfully!")
        run_agent = st.sidebar.button("Run Agents 🚀")
        st.sidebar.json(input_data)
    except Exception as e:
        st.sidebar.error(f"❌ Failed to parse JSON: {e}")
        run_agent = False
else:
    st.sidebar.warning("⚠️ Please upload a valid JSON file.")
    run_agent = False

if st.button("Go to Orchestrator"):
    st.switch_page("pages/orchestrator_dashboard.py")

tabs = [
    "Customer Data Platform (CDP)", 
    "Propensity Agent", 
    "Comparison Analysis Agent", 
    "Dealer Locator Agent", 
    "Prioritization Agent", 
    "Sentiment Analysis Agent", 
    "Personalization Agent",
    "Communication Agent"
]

tab1, tab2, tab3, dealer_locator_agent, tab4, tab5, tab6, tab7 = st.tabs(tabs)

propensity_result = None
competitor_result = None
personalization_result = None
aem_result = None
sentiment_result = None
prioritization_result = None
communication_result = None

dealer_locator_result = None

def response_generator(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.05)

def run_autobot_agents_trigger(input_data):
    global propensity_result, competitor_result, personalization_result, aem_result, sentiment_result, prioritization_result, communication_result
    autobot_agents_trigger = [{
        "task": "autobot_agents_trigger",
        "service": GRYD_SERVICE,
        "kwargs": {
            "source": input_data,
            "execution_mode": "async"
        },
        "args": (None)
    }]
    sync_result = gryd.await_results(autobot_agents_trigger)[0]
    logger.info(json.dumps(sync_result, indent=4, default=str))
    for job in sync_result:
        if job is None:
            continue
        task_name = job.get("task")
        if task_name == "propensity_agent":
            propensity_result = job
        elif task_name == "competitor_analysis_agent":
            competitor_result = job
        elif task_name == "personalization_agent":
            personalization_result = job
        elif task_name == "aem_integration_agent":
            aem_result = job
        elif task_name == "sentiment_analysis_agent":
            sentiment_result = job
        elif task_name == "prioritization_agent":
            prioritization_result = job
        elif task_name == "communication_agent":
            communication_result = job
    return propensity_result, competitor_result, personalization_result, aem_result, sentiment_result, prioritization_result, communication_result

if run_agent:
    with st.spinner("Running agents..."):
        try:   
            # autobot_agents_trigger_async = [{
            #     "task": "autobot_agents_trigger_generator",
            #     "service": GRYD_SERVICE,
            #     "kwargs": {
            #         "source": input_data,
            #         "execution_mode": "async"
            #     },
            #     "args": (None)
            # }]
            # for job in gryd.yield_results(autobot_agents_trigger_async):
            #     task_name, status, result_data = job[1], job[3], job[4]
            #     if status != "result":
            #         logger.warning(f"⚠️ Task '{task_name}' failed or is still pending.")
            #         continue
            #     logger.info(f"✅ Task '{task_name}' completed with result:\n{json.dumps(result_data, indent=4, default=str)}")

            #     if task_name == "propensity_agent":
            #         propensity_result = result_data
            #     elif task_name == "competitor_analysis_agent":
            #         competitor_result = result_data
            #     elif task_name == "personalization_agent":
            #         personalization_result = result_data
            #     elif task_name == "aem_integration_agent":
            #         aem_result = result_data
            #     elif task_name == "sentiment_analysis_agent":
            #         sentiment_result = result_data
            #     elif task_name == "prioritization_agent":
            #         prioritization_result = result_data

            propensity_result, competitor_result, personalization_result, aem_result, sentiment_result, prioritization_result, communication_result = run_autobot_agents_trigger(input_data)

            # dealer locator agent seperate call
            dealer_locator_agent_call = [{
                    "task": "dealer_locator_agent",
                    "service": GRYD_SERVICE,
                    "kwargs": {
                        "source": input_data,
                        "execution_mode": "async"
                    },
                    "args": (None)
            }]

            dealer_locator_result = gryd.await_results(dealer_locator_agent_call)[0]
            logger.info(f"dealer_locator_result: {dealer_locator_result}")
        except Exception as e:
            traceback.print_exc()
            st.error(f"❌ Agent failed: {str(e)}")
with tab1:
    st.subheader("🧠 Customer Data Platform (CDP) ")
    if aem_result:
        st.success("✅ Customer Interaction Fetched Successfully from AEM.")
        if isinstance(aem_result, dict):
            interaction = aem_result.get("updated_source")
            st.json(interaction)
    else:
        st.info("ℹ️ Run the agent to see results.")

# Propensity Agent tab
with tab2:
    st.subheader("🧠 Propensity Agent")
    if propensity_result:
        scores = propensity_result.get("scores")
        propensity_img_url = propensity_result.get("propensity_chart_url")
        reasoning = propensity_result.get("reasoning")
        if reasoning:
            st.markdown("#### <Agent Reasoning>")
            response = st.write_stream(response_generator(response = reasoning))
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

with tab3:
    st.subheader("📈 Competitor Analysis Agent")

    if competitor_result:
        st.success("✅ Competitor Analysis Computed Successfully")
        # full data
        with st.expander("Full Data"):
            st.json(competitor_result)
        
        st.markdown("#### 🚗 Competitor Car Variants")

        # Showing car variant details in tabular format
        car_variants = []
        car_groups = competitor_result.get("compared_cars_data", [])
        for car_group in car_groups:
            for variant in car_group:
                car_variants.append({
                    "Brand": variant.get("brand", variant.get("brand_name")),
                    "Product Name": variant.get("product_name"),
                    "Variant": variant.get("variant", variant.get("variant_name", "N/A")),
                    "Fuel Type": variant.get("fuel_type", "N/A"),
                    "Vehicle Type" : variant.get("vehicle_type", "N/A"),
                    "Price (₹)": float(variant.get("price", 0)),
                    "Technology & Performance" : variant.get("technology_and_performance", []),
                    "General Info" : variant.get("general", []),
                    
                    # "Engine": variant.get("technology_and_performance", [])[0] if variant.get("technology_and_performance") else "N/A",
                    # "Transmission": variant.get("general", [])[3] if variant.get("general") and len(variant.get("general")) > 3 else "N/A",
                    "Safety & Environment" : variant.get("safety_and_environment", []),
                    "Infotainment & Connectivity": variant.get("infotainment_and_connectivity", []), # "infotainment_connectivity"
                    "Comfort & Convenience": variant.get("comfort_and_convenience", []),
                    "Branding & Looks": variant.get("branding_and_looks", [])
                })

        if car_variants:
            car_df = pd.DataFrame(car_variants)
            st.dataframe(car_df, use_container_width=True)

        # Show Key Comparisons
        st.markdown("#### 🔍 Key Comparisons")
        comparisons = competitor_result.get("comparisons", {})
        if isinstance(comparisons, dict):
            for comparison_title, metrics in comparisons.items():
                st.markdown(f"#### {comparison_title}")
                comparison_df = pd.DataFrame(metrics).T.reset_index()
                comparison_df.columns = ['Feature'] + list(comparison_df.columns[1:])
                st.dataframe(comparison_df, use_container_width=True)
        else:
            st.warning("No Key Comparisons found.")

        # Show Common Points
        st.markdown("#### 🔗 Common Points")
        common_points = competitor_result.get("common_points", [])
        if common_points:
            common_df = pd.DataFrame(common_points, columns=["Common Features"])
            st.dataframe(common_df, use_container_width=True)

        # Show Key Differences
        st.markdown("####  ⚖️ Key Differences")
        key_diff = competitor_result.get("key_differences", {})
        if isinstance(key_diff, dict):
            for key, val in key_diff.items():
                st.markdown(f"#### 🔸 {key.replace('_', ' ').title()}")
                diff_df = pd.DataFrame(val.items(), columns=["Model", key.replace('_', ' ').title()])
                st.dataframe(diff_df, use_container_width=True)
        else:
            st.warning("No Key Differences found.")

        # User Choice Justification
        st.markdown("#### ✅ User Choice Justification")
        user_just = competitor_result.get("user_choice_justification", {})
        if isinstance(user_just, dict):
            for model, reason in user_just.items():
                st.markdown(f"**{model}**")
                st.info(reason)
        else:
            st.warning("No User Choice Justification found.")
    else:
        st.info("ℹ️ Run the agent to see results.")

with dealer_locator_agent:
    def show_dealer_locations(dealer_locator_result):
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

    show_dealer_locations(dealer_locator_result)

with tab4:
    st.subheader("🧠 Prioritization Agent")
    if prioritization_result:
        st.success("✅ Prioritization Computed Successfully")
        st.write("🧾 Prioritization Results")
        with st.expander("📦 Raw Data"):
            st.json(prioritization_result)
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
    else:
        st.info("ℹ️ No prioritization data yet.")


with tab5:
    st.subheader("🧠 Sentiment Analysis Agent")
    if sentiment_result:
        st.success("✅ Sentiment Computed Successfully")
        st.write("🧾 Sentiment Results")
        if isinstance(sentiment_result, dict):
            st.info(f"**User Input:** {sentiment_result.get('user_input')}\n\n**Justification:** {sentiment_result.get('justification')} \n\n**Emotions:** {sentiment_result.get('emotions')}\n\n**Sentiment Score:** {sentiment_result.get('sentiment_score')}")
    else:
        st.info("ℹ️ No sentiment data yet.")

with tab6:
    st.subheader("🧠 Personalization Agent")
    if personalization_result:
        st.success("✅ Personalization Computed Successfully")
        st.write("🧾 Personalization Results")
        reasoning = personalization_result.get("reasoning")
        if reasoning:
            st.markdown("#### <Agent Reasoning>")
            response = st.write_stream(response_generator(response = reasoning))
        if isinstance(personalization_result, dict):
            message = personalization_result.get("personalization_agent_response")
            st.text_area("Personalization Message : ", message, height=600)
    else:
        st.info("ℹ️ No personalization data yet.")

with tab7:
    st.subheader("📧 Communication Agent")
    if communication_result:
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
                        st.markdown(f"**📌 Subject:** {subject}")# Subject
                        st.divider()# Divider
                        st.markdown("**Body:**")# Body
                        st.markdown(f"> {message}")
                    else:
                        st.write(email_draft)

        elif status == "error":
            st.error("❌ Email Sending Failed!")
        elif status == "failed" or "not sent" in result_message.lower():
            st.warning("⚠️ Email Not Sent")
        else:
            st.info("ℹ️ Communication Agent Completed")
        with st.expander("🔧 Debug Information"):
            st.json(communication_result)



