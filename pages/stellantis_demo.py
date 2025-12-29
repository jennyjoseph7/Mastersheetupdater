import streamlit as st
import json
from gryd_worker import gryd
from utils import *
import plotly.io as pio
import pandas as pd
import os, sys, traceback
import pydeck as pdk
from streamlit_chat import message

from agents.cohort_generation_agent import CohortGenerationAgent
from agents.cohort_classification_agent import CohortClassificationAgent
from agents.campaign_idea_generator_agent import CampaignIdeaGeneratorAgent
from agents.affinity_agent import AffinityEngineAgent
from agents.propensity_agent import PropensityAgent
from collections import defaultdict

logger = get_logger(__name__)

def setup_gryd():
    gryd.SERVICE = GRYD_SERVICE
    gryd.set_queue_manager(config=GRYD_CONFIG)
    environment = os.getenv("ENVIRONMENT", "-local")
    if not environment.startswith("-"):
        environment = f"-{environment}"
    gryd.ENVIRONMENT = environment

setup_gryd()

def setup_header():
    st.set_page_config(page_title="Agentic CX: Campaign Funnel & Lead Nurturing", layout="wide")
    st.subheader("Agentic CX: Campaign Funnel & Lead Nurturing")
    st.write("Product Knowledge → Cohorts → User Affinity → Campaign")

setup_header()

# st.sidebar.image(
#     "pages/campaign_funnel.drawio.png",
#     width=280
# )

st.divider()

DEFAULT_KEYS = ["interaction", "affinity", "cohorts", "classified_cohort", "campaign", "clusters"]

for key in DEFAULT_KEYS:
    if key not in st.session_state:
        st.session_state[key] = None

st.sidebar.header("⚙️ Controls")

if "pipeline_ran" not in st.session_state:
    st.session_state.pipeline_ran = False

if "pipeline_data" not in st.session_state:
    st.session_state.pipeline_data = {}

if "show_chatbot" not in st.session_state:
    st.session_state.show_chatbot = False

if st.sidebar.button("🔄 Reset Pipeline"):
    for key in DEFAULT_KEYS:
        st.session_state[key] = None
    # st.experimental_rerun()
    st.session_state.pipeline_ran = False
    st.session_state.pipeline_user_id = None
    st.rerun()


st.subheader("1️⃣ Product Knowledge → Cohorts")

st.markdown("(Either provide Product URL or Brochure PDF)")
col1, col2 = st.columns(2)

with col1:
    product_link = st.text_input(
        "Product Website URL",
        placeholder="https://auto.mahindra.com/suv/xuv3xo/X3XO.html"
    )

with col2:
    brochure_url = st.text_input(
        "Brochure PDF URL",
        placeholder="https://auto.mahindra.com/on/demandware.static/-/Sites-amc-Library/default/dw48c7c87f/brochures/X3XO/X3XO_brochure.pdf"
    )

if st.button("Generate Cohorts"):
    if not product_link and not brochure_url:
        st.error("Provide either Product URL or Brochure PDF")
    else:
        with st.spinner("Generating cohorts... (this may take a few minutes)"):
                cga = CohortGenerationAgent(product_website_url = product_link, brochure_url = brochure_url)
                cohorts = cga.run()['cohorts']
                st.session_state.cohorts = cohorts

if st.session_state.cohorts:
    st.success("✅️ Cohorts Generated. Total Cohorts: {}".format(len(st.session_state.cohorts)))

    cohort_rows = []

    for cohort in st.session_state.cohorts:
        # ---- Flatten eligibility rules
        eligibility_events = cohort.get("eligibility_rules", {}).get("events", [])
        eligibility_str = " | ".join([
            f"{e.get('type')}:{e.get('page')} (min {e.get('min_count')})"
            for e in eligibility_events
        ])

        cohort_rows.append({
            "idx": cohort.get("idx"),
            "Cohort ID": cohort.get("cohort_id"),
            "Cohort Name": cohort.get("cohort_name"),
            "Intent Level": cohort.get("intent_level"),
            "Priority": cohort.get("priority"),
            "Description": cohort.get("description"),
            "Behavioral Signals": cohort.get("behavioral_signals", []),     # "| ".join(cohort.get("behavioral_signals", [])),
            "Eligibility Rules": eligibility_str,
            "Exclusion Rules":  cohort.get("exclusion_rules", []),          # " | ".join(cohort.get("exclusion_rules", [])),
            "Recommended Channels": cohort.get("recommended_channels", []),  #  " | ".join(cohort.get("recommended_channels", [])),
            "Message Style Tags": cohort.get("message_style_tags", []),     # " | ".join(cohort.get("message_style_tags", [])" 
            "Cooldown Days": cohort.get("cooldown_days")
        })

    cohorts_df = pd.DataFrame(cohort_rows)

    # ---- Use idx as index
    cohorts_df = cohorts_df.set_index("idx")
    st.dataframe(cohorts_df, use_container_width=True)

else:
    st.warning("⚠️️ Cohorts Registry is empty.")
    st.stop()

st.divider()

def build_clusters(classified_users):
    clusters = defaultdict(list)
    # Format of clusters:
    # {
    #     "cohort_id": [
    #         {
    #             "user_id_1" : "user_id (type: str)",
    #             "interaction": "interaction (type: dict)",
    #             "classified_cohort_data": "classified_cohort_data (type: dict)" 
    #         },
    #         {
    #             "user_id_2" : "user_id (type: str)",
    #             "interaction": "interaction (type: dict)",
    #             "classified_cohort_data": "classified_cohort_data (type: dict)" 
    #         }
    #     ]
    # }
    for u in classified_users:
        cohort_id = u["classified_cohort_data"]["cohort_id"]
        clusters[cohort_id].append(u)
    return clusters

def classify_users(users, cohorts : list[dict]):
    progress = st.progress(0)
    status = st.empty()
    total = len(users)

    results = []

    for idx, interaction in enumerate(users):
        user_id = interaction.get("user_id", f"user_{idx}")
        status.markdown(f"**Classifying User {user_id}, Record {idx+1}/{total}**")
        cc = CohortClassificationAgent(
            source=interaction,
            cohorts=cohorts,
            brochure_url=None,
            product_website_url=None
        )
        classified = cc.run()

        classified_cohort_data = None 
        for cohort in cohorts:
            if cohort["cohort_id"] == classified["cohort_id"]:
                classified_cohort_data = cohort

        results.append({
            "user_id": interaction.get("user_id", f"user_{idx}"),
            "interaction": interaction,
            "classified_cohort_data": classified_cohort_data
        })
        progress.progress((idx + 1) / total)
    return results



def read_csv_detect(uploaded_file):
    import chardet
    raw = uploaded_file.read()
    encoding = chardet.detect(raw)["encoding"]
    uploaded_file.seek(0)
    return pd.read_csv(uploaded_file, encoding=encoding)

def upload_data():
    st.subheader("2️⃣ User Interaction")
    st.markdown("(Either Upload single user JSON or bulk CSV/JSON)")

    col1, col2, col3 = st.columns(3)

    with col1:
        single_json = st.file_uploader(
            "Single User Interaction (JSON)",
            type=["json"],
            disabled=st.session_state.cohorts is None
        )

    with col2:
        bulk_csv = st.file_uploader(
            "Bulk User Interactions (CSV)",
            type=["csv"],
            disabled=st.session_state.cohorts is None
        )

    with col3:
        bulk_json = st.file_uploader(
            "Bulk User Interactions (JSON)",
            type=["json"],
            disabled=st.session_state.cohorts is None
        )

    # ------------------------- Bulk CSV -------------------------
    if bulk_csv:
        df = read_csv_detect(bulk_csv)
        df = df.sample(n = min(10, len(df)), random_state=42)
        users = df.to_dict(orient="records")
        return {
            "mode": "bulk",
            "users": users
        }

    # ------------------------- Bulk JSON -------------------------
    if bulk_json:
        users = json.load(bulk_json)
        if not isinstance(users, list):
            st.error("Bulk JSON must be a list of user objects")
            return None
        return {
            "mode": "bulk",
            "users": users
        }

    # ------------------------- Single JSON -------------------------
    if single_json:
        user = json.load(single_json)
        return {
            "mode": "single",
            "users": [user]
        }

    return None

data = upload_data()

if data is None:
    st.error("Please upload user data")
    st.stop()

clusters = None

mode = data["mode"]
users = data["users"]
st.success(f"Loaded {len(users)} user(s) [{mode}]")

st.divider()

st.subheader("3️⃣ Cohort Clusters")
st.markdown("(Create cohort clusters of users based on their interactions)")

generate_clusters = st.button("🚀 Generate Cohort Clusters")

if generate_clusters:
    with st.spinner("Classifying users and building clusters..."):
        classified_users : list[dict] = classify_users(users, st.session_state.cohorts)
        clusters: dict[str, list] = build_clusters(classified_users)
        st.success(f"✅️ Classified {len(classified_users)} user(s)")
        st.session_state.clusters = clusters

if st.session_state.clusters is None:
    st.warning("Please generate cohort clusters first")
    st.stop()

cluster_rows = []
for cohort_id, users in st.session_state.clusters.items():
    cohort_meta = None
    for c in st.session_state.cohorts:
        if c["cohort_id"] == cohort_id:
            cohort_meta = c
            break

    # cohort_meta = st.session_state.cohorts[cohort_id]
    cluster_rows.append({
        "Cohort Name": cohort_meta["cohort_name"],
        "Cohort ID": cohort_id,
        "Users Count": len(users),
        "Intent Level": cohort_meta["intent_level"],
        "Priority": cohort_meta["priority"]
    })
cluster_df = pd.DataFrame(cluster_rows)

import plotly.express as px
fig = px.pie(
    cluster_df,
    names="Cohort Name",
    values="Users Count",
    hole=0.45,
    title="Cohort Share"
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("4️⃣ Select User")
st.markdown("(Select a user from the cohort cluster)")

def select_user(clusters : dict):
    col1, col2 = st.columns(2)
    with col1:
        selected_cohort = st.selectbox("Select Cohort", options=list(clusters.keys()))
        users_in_cluster = clusters[selected_cohort]
    with col2:
        selected_user_id = st.selectbox("Select User", options=[u["user_id"] for u in users_in_cluster])
    selected_user_data = None
    for u in users_in_cluster:
        if u["user_id"] == selected_user_id:
            selected_user_data = u
            break
    return selected_user_data

if st.session_state.clusters is not None:
    selected_user_data = select_user(clusters=st.session_state.clusters)
    current_user_id = selected_user_data["user_id"]

    if "pipeline_user_id" not in st.session_state:
        st.session_state.pipeline_user_id = None
    
    if st.session_state.pipeline_user_id != current_user_id:
        st.session_state.pipeline_ran = False
        st.session_state.pipeline_user_id = current_user_id

        # Clear previous pipeline results
        st.session_state.classified = None
        st.session_state.affinity = None
        st.session_state.campaign = None
    
    st.session_state.selected_user_data = selected_user_data

interaction = st.session_state.selected_user_data["interaction"]

st.info("Interaction Loaded")

with st.expander("📝 View Interaction"):
    st.json(interaction)

run_pipeline = st.button("🚀 Run Pipeline")

if run_pipeline:
    st.session_state.pipeline_ran = True

# Display results if pipeline has been run
if st.session_state.get("pipeline_ran", False):
    classified = st.session_state.classified
    
    # ----------------------------- Display Cohort Classification -----------------------------
    st.divider()
    st.subheader("5️⃣ 👥 Cohort Classification")

    if run_pipeline or st.session_state.classified is None:
        with st.spinner("Classifying user..."):
            logger.info(f" selected_user_data: {st.session_state.selected_user_data}")
            classified = st.session_state.selected_user_data["classified_cohort_data"]
            st.session_state.classified = classified
    
    summary_df = pd.DataFrame([{
        "Cohort Name": st.session_state.selected_user_data["classified_cohort_data"]["cohort_name"],
        "Cohort ID": st.session_state.selected_user_data["classified_cohort_data"]["cohort_id"],
        "Intent Level": st.session_state.selected_user_data["classified_cohort_data"]["intent_level"],
        "Priority": st.session_state.selected_user_data["classified_cohort_data"]["priority"]
    }])
    st.markdown("**Identified Cohort**")
    st.dataframe(summary_df, hide_index=True, use_container_width=True)

    desc_df = pd.DataFrame([{"Description": classified["description"]}])
    st.markdown("**Cohort Description**")
    st.dataframe(desc_df, hide_index=True, use_container_width=True)

    signals_df = pd.DataFrame({"Behavioral Signal": classified["behavioral_signals"]})
    st.markdown("**Cohort Signals**")
    st.dataframe(signals_df, hide_index=True, use_container_width=True)
    
    rules_df = pd.DataFrame(classified["eligibility_rules"]["events"])
    st.markdown("**Cohort Rules**")
    st.dataframe(rules_df, hide_index=True, use_container_width=True)

    tags_df = pd.DataFrame({"Message Style Tag": classified["message_style_tags"]})
    st.markdown("**Cohort Tags**")
    st.dataframe(tags_df, hide_index=True, use_container_width=True)

    # ----------------------------- Display Affinity Engine -----------------------------
    st.divider()
    st.subheader("6️⃣ 🔗 Affinity Engine")

    if run_pipeline or st.session_state.affinity is None:
        with st.spinner("Calculating affinity..."):
            affinity = AffinityEngineAgent().run(interaction)
            st.session_state.affinity = affinity

    st.markdown("**Why these affinities?**")
    st.info(st.session_state.affinity["llm_reasoning"])
    scores_df = pd.DataFrame(st.session_state.affinity["affinity_scores"].items(), columns=["Dimension", "Score"]).sort_values("Score")

    st.markdown("**Affinity Scores**")
    st.dataframe(scores_df, use_container_width=True, hide_index=True)

    if "affinity_fig_json" in st.session_state.affinity:
        fig = pio.from_json(json.dumps(st.session_state.affinity["affinity_fig_json"]))
        st.plotly_chart(fig, use_container_width=True)
    
    # ----------------------------- Display Campaign Generation -----------------------------
    st.divider()
    st.subheader("7️⃣ 🎯 Campaign Ideas")

    if run_pipeline or st.session_state.campaign is None:
        with st.spinner("Generating campaign ideas..."):
            campaign = CampaignIdeaGeneratorAgent(
                source=interaction,
                classified_cohort=selected_user_data["classified_cohort_data"],
                brochure_url=brochure_url,
                product_website_url=product_link
            )
            campaign_output = campaign.run()
            st.session_state.campaign = campaign_output
    
    campaign_df = pd.DataFrame({"Campaign Idea": st.session_state.campaign["campaign_ideas"]})
    st.markdown("**Campaign Ideas**")
    st.dataframe(campaign_df, hide_index=True, use_container_width=True)

    nudges_df = pd.DataFrame({"Nudge": st.session_state.campaign["nudges"]})
    st.markdown("**User Nudges**")
    st.dataframe(nudges_df, hide_index=True, use_container_width=True)

    hooks_df = pd.DataFrame({"Hook Copy": st.session_state.campaign["hooks"]})
    st.markdown("**Hooks**")
    st.dataframe(hooks_df, hide_index=True, use_container_width=True)

    wa_df = pd.DataFrame({"WhatsApp Message": st.session_state.campaign["whatsapp_msgs"]})
    st.markdown("**💬 Website Bot Messages**")
    st.dataframe(wa_df, hide_index=True, use_container_width=True)

    value_df = pd.DataFrame({"Value Proposition": st.session_state.campaign["value_props"]})
    st.markdown("**💰 Value Propositions**")
    st.dataframe(value_df, hide_index=True, use_container_width=True)

    variant_df = pd.DataFrame({"Variant Recommendation": st.session_state.campaign["variant_recos"]})
    st.markdown("**Variant Recommendations**")
    st.dataframe(variant_df, hide_index=True, use_container_width=True)

    st.divider()

    st.subheader("8️⃣ Next Steps")
    whatsapp_button = st.button("💬 Send WhatsApp Message")
    redirect_button = st.button("👉 Redirect to Product Page")
    add_to_cdp = st.button("💾 Add to CDP")

    if whatsapp_button:
        st.session_state.show_chatbot = True

    if redirect_button:
        st.markdown("**👉 Redirect to Product Page**")
        if product_link:
            st.write(f"Redirecting to {product_link}")
            st.components.v1.html(
        f"""
        <script>
            window.open("{product_link}", "_blank");
        </script>
        """,
        height=0
    )

    if add_to_cdp:
        st.markdown("**💾 Add to CDP**")
        st.error("Feature coming soon...")
    
    if st.session_state.get("show_chatbot", False) is True:
        # from agents.media_extraction_agent import MediaExtractionAgent
        # media_agent = MediaExtractionAgent(url=product_link)
        # media_extraction_agent_result = media_agent.run()
        # all_images = media_extraction_agent_result["images"]
        # all_videos = media_extraction_agent_result["videos"]
        # image = all_images[0] if len(all_images) > 0 else None
        # video = all_videos[0] if len(all_videos) > 0 else None

        import random
        if st.session_state.campaign is not None:
            wa_msgs = st.session_state.campaign["whatsapp_msgs"]
            random_wa_msg = random.choice(wa_msgs)
            logger.info(f"random_wa_msg: {random_wa_msg}")
            st.markdown("""
                <style>
                .chatbot-container {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    width: 350px;
                    height: 450px;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 5px 40px rgba(0,0,0,0.3);
                    z-index: 9999;
                    display: flex;
                    flex-direction: column;
                    animation: slideUp 0.3s ease-out;
                }
                
                @keyframes slideUp {
                    from {
                        transform: translateY(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateY(0);
                        opacity: 1;
                    }
                }
                
                .chatbot-header {
                    background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                    color: white;
                    padding: 15px;
                    border-radius: 15px 15px 0 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .chatbot-body {
                    flex: 1;
                    padding: 20px;
                    overflow-y: auto;
                    background: #ece5dd;
                }
                
                .message-bubble {
                    background: #DCF8C6;
                    padding: 12px 15px;
                    border-radius: 10px;
                    margin: 10px 0;
                    max-width: 85%;
                    float: right;
                    clear: both;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    font-size: 14px;
                    line-height: 1.4;
                }
                
                .message-time {
                    font-size: 11px;
                    color: #667781;
                    text-align: right;
                    margin-top: 5px;
                }
                
                .close-btn {
                    background: rgba(255,255,255,0.2);
                    border: none;
                    color: white;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    cursor: pointer;
                    font-size: 18px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                </style>
                
                <div class="chatbot-container">
                    <div class="chatbot-header">
                        <div>
                            <div style="font-weight: bold; font-size: 16px;">💬 WhatsApp Bot</div>
                            <div style="font-size: 12px; opacity: 0.9;">Online</div>
                        </div>
                    </div>
                    <div class="chatbot-body">
                        <div class="message-bubble">
                            """ + random_wa_msg + """
                            <div class="message-time">Just now ✓✓</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            
            close = st.button("❌ Close WhatsApp", key="close_chatbot")
            if close:
                st.session_state.show_chatbot = False
                st.rerun()