import streamlit as st
import json
from gryd_worker import gryd
from utils import *
import plotly.io as pio
import pandas as pd
import os, sys, traceback
import pydeck as pdk
from streamlit_chat import message

logger = get_logger(__name__)
def environment(environment: str = "-local"):
    gryd.SERVICE = GRYD_SERVICE
    gryd.set_queue_manager(config = GRYD_CONFIG)
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment
    message = {"message": f"Environment set to '{environment}'"}
    logger.info(message)
    return message
environment(environment = GRYD_ENVIRONMENT)
st.set_page_config(page_title="Tata Agentic CX Demo", layout="wide")
st.markdown("## 🤖 **Tata Agentic CX Demo**")
st.write("This demo shows how DaveAI's platform converts a cold visitor into a potential customer.")
st.sidebar.image("https://upload.wikimedia.org/wikipedia/hi/2/2a/Tata_logo.svg.png", width=200)
uploaded_file = st.sidebar.file_uploader("📁 Upload JSON file", type=["json"])

tabs = ["Interaction Data", "Propensity Calculation", "Segment Classification & Targeting", "AskBot"]
interaction_data, propensity, segment_classification, askbot = st.tabs(tabs)

if uploaded_file:
    try:
        input_data = json.load(uploaded_file)
        st.sidebar.success("✅ Customer data parsed successfully!")
        run_agent = st.sidebar.button("Run 🚀")
        with interaction_data:
            st.markdown("#### 📊 Interaction Data")
            st.json(input_data)
    except Exception as e:
        st.sidebar.error(f"❌ Failed to parse JSON: {e}")
        run_agent = False
else:
    st.sidebar.warning("⚠️ Please upload a valid JSON file.")
    run_agent = False

if "messages" not in st.session_state:
    st.session_state.messages = []
if "segment_classifier_agent_result" not in st.session_state:
    st.session_state.segment_classifier_agent_result = None
if "propensity_agent_result" not in st.session_state:
    st.session_state.propensity_agent_result = None
if "media_extraction_agent_result" not in st.session_state:
    st.session_state.media_extraction_agent_result = None
if "promo_added" not in st.session_state:
    st.session_state.promo_added = False

if st.sidebar.button("🔄 Reset Entire Demo"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]   # Clears EVERYTHING
    st.rerun()

if st.sidebar.button("🧹 Reset Chat Only"):
    st.session_state.messages = []
    st.session_state.promo_added = False
    st.rerun()


def response_generator(response):
    for word in response.split():
        yield word + " "
        time.sleep(0.03)

def history_sidebar():
    st.sidebar.subheader("Message History")
    for message in st.session_state.messages:
        if message['role'] == 'user':
            st.sidebar.markdown(f"🧑 **User:** {message['content']}")
        else:
            st.sidebar.markdown(f"🤖 **Bot:** {message['content']}")

if run_agent:
    segment_classifier_agent_call = [{
            "task": "segment_classifier_agent",
            "service": GRYD_SERVICE,
            "kwargs": {
                "source": input_data,
                # "brand_url" : "https://cars.tatamotors.com/sierra/ice.html"
            },
            "args": (None)
    }]

    # segment_classifier_agent_result = gryd.await_results(segment_classifier_agent_call)[0]
    st.session_state.segment_classifier_agent_result = gryd.await_results(segment_classifier_agent_call)[0]
    segment_classifier_agent_result = st.session_state.segment_classifier_agent_result
    logger.info(f"segment_classifier_agent_result: {segment_classifier_agent_result}")

    propensity_call = [{
            "task": "propensity_agent",
            "service": GRYD_SERVICE,
            "kwargs": {
                "source": input_data,
            },
            "args": (None)
    }]

    # propensity_result = gryd.await_results(propensity_call)[0]
    st.session_state.propensity_agent_result = gryd.await_results(propensity_call)[0]
    propensity_agent_result = st.session_state.propensity_agent_result
    logger.info(f"propensity_result: {propensity_agent_result}")

    media_extraction_agent_call = [
        {
            "task": "media_extraction_agent",
            "service": GRYD_SERVICE,
            "kwargs": {
                "url": "https://cars.tatamotors.com/sierra/ice.html",
            },
            "args": (None)
        }
    ]

    # media_extraction_agent_result = gryd.await_results(media_extraction_agent_call)[0]
    st.session_state.media_extraction_agent_result = gryd.await_results(media_extraction_agent_call)[0]
    media_extraction_agent_result = st.session_state.media_extraction_agent_result
    logger.info(f"media_extraction_agent_result: {media_extraction_agent_result}")

with propensity:
    st.markdown("#### 📊 Propensity Score")
    if st.session_state.propensity_agent_result:
        propensity_agent_result = st.session_state.propensity_agent_result
        scores = propensity_agent_result.get("scores")
        propensity_img_url = propensity_agent_result.get("propensity_chart_url")
        reasoning = propensity_agent_result.get("reasoning")
        propensity_chart_json = propensity_agent_result.get("propensity_chart_json")
        if reasoning:
            st.markdown("#### Propensity Agent Reasoning:")
            st.info(reasoning)
        
        st.write("Propensity Scores:")
        df = pd.DataFrame(scores.items(), columns=["Category", "Score"])
        st.dataframe(df)
        if propensity_chart_json:
            fig = pio.from_json(propensity_chart_json)
            st.plotly_chart(fig, use_container_width=True)
        elif propensity_img_url:
            st.write("Propensity Chart:")
            st.image(propensity_img_url, width=800,)
        st.markdown("---")

with segment_classification:
    st.markdown("#### 🧠 Detected Segment")
    if st.session_state.segment_classifier_agent_result:
        segment_classifier_agent_result = st.session_state.segment_classifier_agent_result
        detected_segment = segment_classifier_agent_result.get("detected_segment")
        reasoning = segment_classifier_agent_result.get("reasoning")
        if reasoning:
            st.markdown("#### Segment Classifier Agent Reasoning:")
            st.info(reasoning)

        st.warning(f"The customer is in the **'{detected_segment}'** segment.") 

        st.markdown("#### 🎯 Promotional Message")
        segment_classifier_agent_result = st.session_state.segment_classifier_agent_result
        promotional_message = segment_classifier_agent_result.get("promotional_message")

        if st.session_state.media_extraction_agent_result:
            media_extraction_agent_result = st.session_state.media_extraction_agent_result
            all_images = media_extraction_agent_result["images"]
            all_videos = media_extraction_agent_result["videos"]
            image = all_images[0] if len(all_images) > 0 else None
            video = all_videos[0] if len(all_videos) > 0 else None

            if image:
                promotional_message += f"\n\n![]({image})"
            elif video:
                promotional_message += f"\n\n📹 *Video Preview Below*"
                
        if not st.session_state.promo_added:
            st.session_state.messages.append({"role": "assistant", "content": promotional_message})
            st.session_state.promo_added = True
        st.write(promotional_message)
            # media_links : dict = segment_classifier_agent_result.get("media_links")
            # selected_images : list = media_links.get("selected_images")
            # selected_videos : list = media_links.get("selected_videos")
            # image = selected_images[0] if len(selected_images) > 0 else None
            # video = selected_videos[0] if len(selected_videos) > 0 else None
            # if image:
            #     promotional_message += f"\n\n![]({image})"
            # elif video:
            #     promotional_message += f"\n\n📹 *Video Preview Below*"
                
            # if not st.session_state.promo_added:
            #     st.session_state.messages.append({"role": "assistant", "content": promotional_message})
            #     st.session_state.promo_added = True
            # st.write(promotional_message)



initial_prompt = """
You are an AI assistant for the Newly launched Tata Sierra. 
Your job is to help potential buyers understand the car, explore variants, features, pricing, and guide them conversationally. 
Always be friendly, easy to talk to, and helpful. 
### Key Highlights to Know:
- Bold, boxy SUV design with upright stance, LED headlamp + full-width LED DRL bar, modern squared-off profile and dual-tone alloy wheels  
- Triple-screen dashboard setup: digital driver display + large central infotainment screen + passenger-side display  
- Premium interior touches: dual-tone cabin, ambient lighting, ventilated & powered front seats, panoramic sunroof, wireless phone charging, connected-car tech  
- Engine & powertrain options: 1.5-litre turbo-petrol (~170 PS / ~280 Nm) and 2.0-litre diesel (~170 PS / ~350 Nm), with 6-speed manual or automatic transmission options  
- Modern convenience & comfort: dual-zone climate control, premium audio, advanced connectivity, good cabin space & practicality  
- Safety & assistance: multiple airbags, ABS + ESC, hill-hold assist, driver-assist features, and availability of Level-2 ADAS (adaptive cruise, lane-keep assist, 360° camera etc. in higher variants)  
- Value-for-money positioning — blending rugged SUV looks, modern features and multiple engine/variant choices for different buyer needs  
"""


with askbot:
    st.subheader("🤖 AskBot")

    if not st.session_state.segment_classifier_agent_result:
        st.info("Run the agent first to enable conversation.")
        st.stop()

    # Create a dedicated container for chat messages
    chat_container = st.container()

    # (Optional) Sidebar history stays separate
    history_sidebar()

# ----------------------------
# Render chat history (dynamic)
# ----------------------------
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# ----------------------------
# FIXED chat_input (inside askbot)
# ----------------------------
with askbot:
    user_input = st.chat_input("Ask something…")


# ----------------------------
# Process user message
# ----------------------------
if user_input:
    with chat_container:
        st.chat_message("user").markdown(user_input)

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Processing..."):
        conversation_agent = [{
            "task": "conversation_agent",
            "service": GRYD_SERVICE,
            "kwargs": {
                "source": input_data,
                "segment_classifier_result": segment_classifier_agent_result,
                "propensity_result": propensity_agent_result,
                "history": st.session_state.messages,
                "user_message": user_input,
                "initial_prompt": initial_prompt
            }
        }]

    bot_result = gryd.await_results(conversation_agent)[0]
    bot_response = bot_result["response"]

    with chat_container:
        with st.chat_message("assistant"):
            st.write_stream(response_generator(bot_response))

    st.session_state.messages.append({"role": "assistant", "content": bot_response})

    if bot_result.get("follow_up"):
        st.success(bot_result["follow_up"])

# - Suggestions/more followup options in the initial msg
# - dealer locator for mahindra -> have dict based (similar to aem)