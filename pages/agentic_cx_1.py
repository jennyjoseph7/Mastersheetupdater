import streamlit as st
import json
from gryd_worker import gryd
from utils import *
import plotly.io as pio
import pandas as pd
import os, sys, traceback
import pydeck as pdk
from streamlit_chat import message
import uuid
import plotly.express as px

from agents.cohort_generation_agent import CohortGenerationAgent, ProductCohortGenerationAgent
from agents.cohort_classification_agent import CohortClassificationAgent
from agents.campaign_idea_generator_agent import CampaignIdeaGeneratorAgent
from agents.affinity_agent import AffinityEngineAgent
from agents.propensity_agent import PropensityAgent
from collections import defaultdict

logger = get_logger(__name__)

# ------------------------------------------------------------------------------------------------------------------------- #
# Gryd and Streamlit Header Setup

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


def setup_header():
    st.set_page_config(page_title="Agentic CX: Campaign Funnel & Lead Nurturing", layout="wide")
    st.subheader("Agentic CX: Campaign Funnel & Lead Nurturing")
    st.write("Product Knowledge → Cohorts → User Affinity → Campaign")

setup_header()

# ------------------------------------------------------------------------------------------------------------------------- #

st.divider()

# ------------------------------------------------------------------------------------------------------------------------- #
# Session State & Controls

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
    st.session_state.pipeline_ran = False
    st.session_state.pipeline_identifier = None
    st.session_state.classified = None
    st.session_state.affinity = None
    st.session_state.campaign = None
    st.rerun()

# ------------------------------------------------------------------------------------------------------------------------- #
# Generate Cohorts and Display

st.subheader("1️⃣ Product Knowledge → Cohorts")
st.markdown("(Either provide Product URL or Brochure PDF)")
col1, col2 = st.columns(2)

with col1:
    product_link = st.text_input(
        label="Product Website URL", 
        placeholder="https://auto.mahindra.com/suv/xuv3xo/X3XO.html"
        )

with col2:
    brochure_url = st.text_input(
        label="Brochure PDF URL", 
        placeholder="https://auto.mahindra.com/on/demandware.static/-/Sites-amc-Library/default/dw48c7c87f/brochures/X3XO/X3XO_brochure.pdf"
        )

if st.button("Generate Cohorts"):
    if not product_link and not brochure_url:
        st.error("Provide either Product URL or Brochure PDF")
    else:
        with st.spinner("Generating cohorts... (this may take a few minutes)"):
                cohort_generation_agent:object = ProductCohortGenerationAgent(product_website_url = product_link, brochure_url = brochure_url)
                cohorts:list = cohort_generation_agent.run()['cohorts']
                st.session_state.cohorts = cohorts

if st.session_state.cohorts:
    st.success("✅️ {} Cohorts Generated.".format(len(st.session_state.cohorts)))
    cohort_rows = []
    for cohort in st.session_state.cohorts:
        cohort_rows.append({
            "idx": cohort.get("idx"),
            "Cohort ID": cohort.get("cohort_id"),
            "Cohort Name": cohort.get("cohort_name"),
            "Intent Level": cohort.get("intent_level"),
            "Priority": cohort.get("priority"),
            "Description": cohort.get("description"),
            "Behavioral Signals": cohort.get("behavioral_signals", []),
            "Eligibility Rules": cohort.get("eligibility_rules", []),
            "Exclusion Rules":  cohort.get("exclusion_rules", []),
            "Recommended Channels": cohort.get("recommended_channels", []),
            "Message Style Tags": cohort.get("message_style_tags", []),
            "Cooldown Days": cohort.get("cooldown_days")
        })
    cohorts_df = pd.DataFrame(cohort_rows)
    cohorts_df = cohorts_df.set_index("idx")
    st.dataframe(cohorts_df, use_container_width=True)
else:
    st.warning("⚠️️ Cohorts Registry is empty.")
    st.stop()


# ------------------------------------------------------------------------------------------------------------------------- #

st.divider()

# ------------------------------------------------------------------------------------------------------------------------- #
# Generate Campaign Ideas Based on Product Knowledge or User Data

# st.subheader("🎯 Campaign Idea Generation Mode")
# colA, colB = st.columns(2)
# with colA:
#     direct_campaign_btn = st.button("🎨 Generate Campaign Ideas from Product Directly")
# with colB:
#     data_campaign_btn = st.button("📊 Generate Campaign Ideas Based on Customer Data")

# ------------------------------------------------------------------------------------------------------------------------- #

def build_clusters(classified_users):
    clusters = defaultdict(list)
    for u in classified_users:
        cohort_id = u["classified_cohort_data"]["cohort_id"]
        clusters[cohort_id].append(u)
    return clusters

def classify_users(users: list[dict], cohorts : list[dict]):
    progress = st.progress(0)
    status = st.empty()
    total = len(users)
    results = []

    for idx, interaction in enumerate(users):
        user_id = interaction.get("user_id", f"u_{str(uuid.uuid4())}")
        status.markdown(f"**Classifying '{user_id}', Record {idx+1}/{total}**")
        cohort_classification_agent = CohortClassificationAgent(
            source=interaction,
            cohorts=cohorts,
            brochure_url=None,
            product_website_url=None
        )
        classified = cohort_classification_agent.run()

        classified_cohort_data = None 
        for cohort in cohorts:
            if cohort["cohort_id"] == classified.get("cohort_id", classified.get("primary_classified_cohort_id")):
                classified_cohort_data = cohort
                break

        results.append({
            "user_id": user_id,
            "interaction": interaction,
            "classified_cohort_data": classified_cohort_data
        })
        progress.progress((idx + 1) / total)
    return results


def upload_data():
    def read_csv_detect(uploaded_file):
        import chardet
        raw = uploaded_file.read()
        encoding = chardet.detect(raw)["encoding"]
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding=encoding)

    st.subheader("2️⃣ User Interaction")
    st.markdown("(Either Upload single user JSON or bulk CSV/JSON)")

    col1, col2, col3 = st.columns(3)

    with col1:
        single_json = st.file_uploader(
            label="Single User Interaction (JSON)",
            type=["json"],
            disabled=st.session_state.cohorts is None
        )

    with col2:
        bulk_csv = st.file_uploader(
            label="Bulk User Interactions (CSV)",
            type=["csv"],
            disabled=st.session_state.cohorts is None
        )

    with col3:
        bulk_json = st.file_uploader(
            label="Bulk User Interactions (JSON)",
            type=["json"],
            disabled=st.session_state.cohorts is None
        )

    if bulk_csv:
        df = read_csv_detect(bulk_csv)
        df = df.sample(n = min(10, len(df)), random_state=42)
        users = df.to_dict(orient="records")
        return {"mode": "bulk", "users": users}

    if bulk_json:
        users = json.load(bulk_json)
        if not isinstance(users, list):
            st.error("Bulk JSON must be a list of user objects")
            return None
        return {"mode": "bulk", "users": users}

    if single_json:
        user = json.load(single_json)
        return {"mode": "single", "users": [user]}

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
        classified_users:list[dict] = classify_users(users, st.session_state.cohorts)
        clusters:dict[str, list] = build_clusters(classified_users)
        st.success(f"✅️ Classified {len(classified_users)} user(s)")
        st.session_state.clusters = clusters

if st.session_state.clusters is None:
    st.warning("Please generate cohort clusters first")
    st.stop()

cluster_rows = []
for cohort_id, users in st.session_state.clusters.items():
    cohort_meta = next((c for c in st.session_state.cohorts if c['cohort_id'] == cohort_id), None)
    cluster_rows.append({
        "Cohort Name": cohort_meta["cohort_name"],
        "Cohort ID": cohort_id,
        "Users Count": len(users),
        "Intent Level": cohort_meta["intent_level"],
        "Priority": cohort_meta["priority"]
    })
cluster_df = pd.DataFrame(cluster_rows)

fig=px.pie(cluster_df,names="Cohort Name",values="Users Count",hole=0.0,title="Cohort Share")
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("4️⃣ Select Cohort")
st.markdown("(Select a cohort from the cohort cluster)")

selected_cohort = st.selectbox("Select Cohort:", options=list(st.session_state.clusters.keys()))
users_in_cluster = st.session_state.clusters.get(selected_cohort, [])

st.divider()

st.subheader("5️⃣ Run Pipeline For:")
pipeline_level = st.radio("Run Pipeline For:", options=["Cohort", "Individual User"], horizontal=True)

# ==================== REUSABLE DISPLAY FUNCTIONS ====================

def display_cohort_classification(classified):
    """Display cohort classification results"""
    st.divider()
    st.subheader("👥 Cohort Classification")
    
    with st.expander("Click to expand"):
        summary_df = pd.DataFrame([{
            "Cohort Name": classified["cohort_name"],
            "Cohort ID": classified["cohort_id"],
            "Intent Level": classified["intent_level"],
            "Priority": classified["priority"]
        }])
        st.markdown("**Identified Cohort**")
        st.dataframe(summary_df, hide_index=True, use_container_width=True)
        
        desc_df = pd.DataFrame([{"Description": classified["description"]}])
        st.markdown("**Cohort Description**")
        st.dataframe(desc_df, hide_index=True, use_container_width=True)
        
        signals_df = pd.DataFrame({"Behavioral Signal": classified["behavioral_signals"]})
        st.markdown("**Cohort Signals**")
        st.dataframe(signals_df, hide_index=True, use_container_width=True)
        
        rules_df = pd.DataFrame({"Eligibility Rules" : classified["eligibility_rules"]})
        st.markdown("**Cohort Rules**")
        st.dataframe(rules_df, hide_index=True, use_container_width=True)
        
        tags_df = pd.DataFrame({"Message Style Tag": classified["message_style_tags"]})
        st.markdown("**Cohort Tags**")
        st.dataframe(tags_df, hide_index=True, use_container_width=True)


def display_affinity_engine(affinity):
    """Display affinity engine results"""
    st.divider()
    st.subheader("🔗 Affinity Engine")
    
    with st.expander("Click to expand"):
        st.markdown("**Why these affinities?**")
        st.info(affinity["llm_reasoning"])
        
        scores_df = pd.DataFrame(affinity["affinity_scores"].items(), columns=["Dimension", "Score"]).sort_values("Score")
        st.markdown("**Affinity Scores**")
        st.dataframe(scores_df, use_container_width=True, hide_index=True)
        
        fig_json = affinity["affinity_fig_json"]
        fig = pio.from_json(json.dumps(fig_json))
        st.plotly_chart(fig, use_container_width=True)


# def display_campaign_ideas(campaign: list[dict]):
#     """Display campaign ideas for individual user"""
#     st.divider()
#     st.subheader("🎯 Campaign Ideas")

#     logger.info(f"Generating campaign ideas:\n{json.dumps(campaign, indent=4, default=str)}")
    
#     csv_data = []
#     for camp in campaign:
#         csv_data.append({
#             "Campaign ID": camp['campaign_idea_identifier'],
#             "Campaign Name": camp['campaign_idea_identifier'].replace('_', ' ').title(),
#             "Campaign Explanation": camp['campaign_explanation'],
#             "CTA" : " | ".join(camp['cta']),
#             "Audience": " | ".join(camp['audience']),
#             "Hooks": " | ".join(camp['campaign_assets']['hooks']),
#             "Post Captions": " | ".join(camp['campaign_assets']['post_caption']),
#             "Post Descriptions": " | ".join(camp['campaign_assets']['post_description']),
#             "Hashtags": " ".join(camp['campaign_assets']['hashtags']),
#             "WhatsApp Messages": " | ".join(camp['campaign_assets']['whatsapp_msgs']),
#             "Slogans": " | ".join(camp['campaign_assets']['slogan']),
#             "instagram_caption_with_hashtags": " | ".join(camp['campaign_assets']['instagram_caption_with_hashtags'])
#         })
    
#     csv_df = pd.DataFrame(csv_data)
#     csv_string = csv_df.to_csv(index=False)
    
#     col1, col2 = st.columns(2)
#     with col1:
#         st.download_button(
#             label="📥 Download All Campaigns as CSV",
#             data=csv_string,
#             file_name="campaign_assets.csv",
#             mime="text/csv",
#             use_container_width=True
#         )
    
#     with col2:
#         st.download_button(
#             label="📥 Download All Campaigns as JSON",
#             data=json.dumps(campaign, indent=4),
#             file_name="campaign_assets.json",
#             mime="application/json",
#             use_container_width=True
#         )
    
#     # st.markdown("---")
    
#     for idx, camp in enumerate(campaign):
#         with st.expander(f"{idx + 1}️ {camp['campaign_idea_identifier'].replace('_', ' ').title()}"):

#             st.markdown("**Campaign Objective**")
#             st.info(camp.get("campaign_objective"))

#             st.markdown("**Campaign Overview**")
#             st.warning(camp['campaign_explanation'])

#             cta_df = pd.DataFrame({"CTA": camp['cta']})
#             st.markdown("**CTA**")
#             st.dataframe(cta_df, hide_index=True, use_container_width=True)
            
#             audience_df = pd.DataFrame({"Audience": camp['audience']})
#             st.markdown("**Audience**")
#             st.dataframe(audience_df, hide_index=True, use_container_width=True)
            
#             hooks_df = pd.DataFrame({"Hook Copy": camp['campaign_assets']['hooks']})
#             st.markdown("**Hooks**")
#             st.dataframe(hooks_df, hide_index=True, use_container_width=True)
            
#             caption_df = pd.DataFrame({"Post Caption": camp['campaign_assets']['post_caption']})
#             st.markdown("**Post Captions**")
#             st.dataframe(caption_df, hide_index=True, use_container_width=True)

#             post_desc_df = pd.DataFrame({"Post Description": camp['campaign_assets']['post_description']})
#             st.markdown("**Post Descriptions**")
#             st.dataframe(post_desc_df, hide_index=True, use_container_width=True)
            
#             hashtags_df = pd.DataFrame({"Hashtag": camp['campaign_assets']['hashtags']})
#             st.markdown("**Hashtags**")
#             st.dataframe(hashtags_df, hide_index=True, use_container_width=True)
            
#             wa_df = pd.DataFrame({"WhatsApp Message": camp['campaign_assets']['whatsapp_msgs']})
#             st.markdown("**💬 WhatsApp Messages**")
#             st.dataframe(wa_df, hide_index=True, use_container_width=True)
            
#             slogan_df = pd.DataFrame({"Slogan": camp['campaign_assets']['slogan']})
#             st.markdown("**Slogans**")
#             st.dataframe(slogan_df, hide_index=True, use_container_width=True)

#             insta_df = pd.DataFrame({"Instagram Caption": camp['campaign_assets']['instagram_caption_with_hashtags']})
#             st.markdown("**Instagram Captions**")
#             st.dataframe(insta_df, hide_index=True, use_container_width=True)
            
#             # st.markdown("---")

def display_campaign_ideas(campaign: list[dict]):
    """Display campaign ideas for individual user"""
    st.divider()
    st.subheader("🎯 Campaign Ideas")

    logger.info(f"Generating campaign ideas:\n{json.dumps(campaign, indent=4, default=str)}")
    

    # Preparing CSV for the end-user

    csv_data = []
    for camp in campaign:
        hashtags: list[str] = camp.get("hashtags", [])
        post_sets: list[dict] = camp.get("campaign_post_sets", [])
        cta: list[str] = camp.get("cta", [])
        audience: list[str] = camp.get("audience", [])
        for post_set in post_sets:
            hooks:list[str]  = post_set.get("hooks", [])
            post_caption:list[str]  = post_set.get("post_caption", [])
            slogan:list[str]  = post_set.get("slogan", [])
            messages:list[str]  = post_set.get("messages", [])
            data = {
                "Campaign ID": camp['campaign_idea_identifier'],
                "Campaign Name": camp['campaign_idea_identifier'].replace('_', ' ').title(),
                "Campaign Objective": camp.get('campaign_objective', 'N/A'),
                "Campaign Explanation": camp['campaign_explanation'],
                "Hashtags": " | ".join(hashtags) if hashtags else "",
                "CTA": " | ".join(cta) if cta else "",
                "Audience": " | ".join(audience) if audience else "",
                "Hooks": " | ".join(hooks) if hooks else "",
                "Post Caption": post_caption,
                "Slogan": " | ".join(slogan) if slogan else "",
                "Messages": " | ".join(messages) if messages else ""
            }
            csv_data.append(data)
    
    csv_df = pd.DataFrame(csv_data)
    csv_string = csv_df.to_csv(index=False)

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download All Campaigns as CSV",
            data=csv_string,
            file_name="campaign_assets.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            label="📥 Download All Campaigns as JSON",
            data=json.dumps(campaign, indent=4),
            file_name="campaign_assets.json",
            mime="application/json",
            use_container_width=True
        )


    # Display each campaign with rows for each post
    for idx, camp in enumerate(campaign):
        with st.expander(f"{idx + 1}️⃣ {camp['campaign_idea_identifier'].replace('_', ' ').title()}"):
            campaign_rows = []
            for post_idx, post_set in enumerate(camp.get('campaign_post_sets', []), 1):
                post_caption = post_set.get('post_caption', [])
                row = {
                    "campaign_idea_identifier": camp['campaign_idea_identifier'],
                    "campaign_objective": camp.get('campaign_objective', 'N/A'),
                    "campaign_explanation": camp['campaign_explanation'],
                    "audience": " | ".join(camp['audience']),
                    "cta": " | ".join(camp['cta']),
                    "hashtags": " | ".join(camp['hashtags']),
                    "post_caption": post_caption,
                    "Slogan": " | ".join(post_set.get('slogan', [])),
                    "Messages": " | ".join(post_set.get('messages', []))
                }
                
                campaign_rows.append(row)
            campaign_df = pd.DataFrame(campaign_rows)
            st.dataframe(campaign_df, hide_index=True, use_container_width=True)


def display_cta_buttons(product_link, campaign_data):
    """Display CTA buttons for next steps"""
    st.divider()
    st.subheader("📢 Next Steps")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        whatsapp_button = st.button("💬 Send WhatsApp Message", use_container_width=True)
    with col2:
        redirect_button = st.button("👉 Redirect to Product Page", use_container_width=True)
    with col3:
        add_to_cdp = st.button("💾 Add to CDP", use_container_width=True)
    
    if whatsapp_button:
        st.session_state.show_chatbot = True
        st.rerun()
    
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
        
    if st.session_state.get("show_chatbot", False):
        import random
        from agents.media_extraction_agent import MediaExtractionAgent
        import streamlit.components.v1 as components
        import re
        
        try:
            # product_link = product_link or "https://www.citroen.in/aircross"
            media_agent = MediaExtractionAgent(url=product_link)
            media_extraction_agent_result = media_agent.run()
            logger.info(f"media_extraction_agent_result: {json.dumps(media_extraction_agent_result, indent=4, default=str)}")
            all_images = media_extraction_agent_result.get("images", [])
            image = random.choice(all_images) if all_images else None
            if image:
                image = image.replace(",", "").strip()
        except Exception as e:
            image = None
        
        if isinstance(campaign_data, list):
            all_wa_msgs = []
            for camp in campaign_data:
                for post_set in camp.get('campaign_post_sets', []):
                    all_wa_msgs.extend(post_set.get('messages', []))
            random_wa_msg = random.choice(all_wa_msgs) if all_wa_msgs else "Hello! Check out our product."
        else:
            random_wa_msg = "Hello! Check out our product."
        
        # Build image HTML only if image exists and is valid
        image_html = ""
        image = "https://www.nexaexperience.com/adobe/assets/urn:aaid:aem:9fa63d8c-06c4-49d6-bc8f-456f58079965/as/E_Vitara-Ice-KV_804x584_RYI.jpg?height=584&width=2000&id=1&preferwebp=true"
        image = "https://thumbs.dreamstime.com/b/modern-automotive-showroom-brightly-lit-showcasing-variety-new-cars-including-sleek-sedans-versatile-suvs-large-banner-422519541.jpg"
        if image and image.startswith(('http://', 'https://')):
            image_html = f'<img src="{image}" alt="Product" onerror="this.style.display=\'none\'">'
        
        chatbots_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    background: transparent;
                    padding: 20px;
                }}
                
                .chatbots-wrapper {{
                    display: flex;
                    gap: 30px;
                    flex-wrap: wrap;
                    justify-content: center;
                }}
                
                .chatbot-container {{
                    width: 380px;
                    height: 550px;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    border: 1px solid #e0e0e0;
                    animation: fadeIn 0.4s ease-out;
                }}
                
                @keyframes fadeIn {{
                    from {{
                        opacity: 0;
                        transform: translateY(20px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                
                .chatbot-label {{
                    text-align: center;
                    font-size: 14px;
                    font-weight: 600;
                    color: #666;
                    margin-bottom: 10px;
                }}
                
                /* Web Chatbot Styles */
                .web-chatbot .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                }}
                
                .web-chatbot .body {{
                    flex: 1;
                    padding: 20px;
                    overflow-y: auto;
                    background: #f8f9fa;
                }}
                
                .web-chatbot .message {{
                    background: white;
                    padding: 14px 16px;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                    font-size: 14px;
                    line-height: 1.6;
                    color: #333;
                    border: 1px solid #e8e8e8;
                }}
                
                /* WhatsApp Chatbot Styles */
                .whatsapp-chatbot .header {{
                    background: #128C7E;
                    color: white;
                    padding: 20px;
                }}
                
                .whatsapp-chatbot .body {{
                    flex: 1;
                    padding: 20px;
                    overflow-y: auto;
                    background: #ECE5DD;
                    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23d9d9d9' fill-opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
                }}
                
                .whatsapp-chatbot .message {{
                    background: #DCF8C6;
                    padding: 10px 14px;
                    border-radius: 8px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    font-size: 14px;
                    line-height: 1.5;
                    color: #303030;
                    position: relative;
                    max-width: 85%;
                    float: right;
                    clear: both;
                }}
                
                .whatsapp-chatbot .message::after {{
                    content: '';
                    position: absolute;
                    right: -8px;
                    top: 10px;
                    width: 0;
                    height: 0;
                    border-left: 8px solid #DCF8C6;
                    border-top: 8px solid transparent;
                    border-bottom: 8px solid transparent;
                }}
                
                /* Common Styles */
                .title {{
                    font-weight: 600;
                    font-size: 18px;
                    margin-bottom: 3px;
                }}
                
                .status {{
                    font-size: 13px;
                    opacity: 0.95;
                }}
                
                .message img {{
                    max-width: 100%;
                    border-radius: 8px;
                    margin-bottom: 10px;
                    display: block;
                }}
                
                .message-text {{
                    word-wrap: break-word;
                    white-space: pre-wrap;
                }}
                
                .time {{
                    font-size: 11px;
                    color: #667781;
                    text-align: right;
                    margin-top: 8px;
                }}
                
                .whatsapp-chatbot .time {{
                    color: #667781;
                }}
            </style>
        </head>
        <body>
            <div class="chatbots-wrapper">
                <!-- Web Chatbot -->
                <div>
                    <div class="chatbot-label">🌐 Web Chat</div>
                    <div class="chatbot-container web-chatbot">
                        <div class="header">
                            <div class="title">💬 ChatBot</div>
                            <div class="status">Online</div>
                        </div>
                        <div class="body">
                            <div class="message">
                                {image_html}
                                <div class="message-text">{random_wa_msg}</div>
                                <div class="time">Just now</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- WhatsApp Chatbot -->
                <div>
                    <div class="chatbot-label">💚 WhatsApp</div>
                    <div class="chatbot-container whatsapp-chatbot">
                        <div class="header">
                            <div class="title">💬 WhatsApp Bot</div>
                            <div class="status">Online</div>
                        </div>
                        <div class="body">
                            <div class="message">
                                {image_html}
                                <div class="message-text">{random_wa_msg}</div>
                                <div class="time">Just now ✓✓</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Display both chatbots
        st.markdown("<br>", unsafe_allow_html=True)
        components.html(chatbots_html, height=650)
        
        # Close button below chatbots
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("❌ Close Chatbots", key="close_chatbot", use_container_width=True):
                st.session_state.show_chatbot = False
                st.rerun()

# ==================== MAIN PIPELINE LOGIC ====================

if "pipeline_identifier" not in st.session_state:
    st.session_state.pipeline_identifier = None

# Initialize states for results
if "classified" not in st.session_state:
    st.session_state.classified = None
if "affinity" not in st.session_state:
    st.session_state.affinity = None
if "campaign" not in st.session_state:
    st.session_state.campaign = None

# Determine pipeline identifier and data based on level
if pipeline_level == "Individual User":
    all_user_ids_from_cohort = [u["user_id"] for u in users_in_cluster]
    selected_user_id = st.selectbox("Select User", options=all_user_ids_from_cohort)
    selected_user_data = next((u for u in users_in_cluster if u["user_id"] == selected_user_id), None)
    pipeline_identifier = f"user_{selected_user_id}"
    
    # Show interaction
    st.info(f"Interaction loaded for '{selected_user_id}'")
    with st.expander("📝 View Interaction"):
        st.json(selected_user_data["interaction"])
else:
    # Cohort level
    selected_user_data = users_in_cluster
    pipeline_identifier = f"cohort_{selected_cohort}"

# Check if pipeline identifier changed - reset if so
if st.session_state.pipeline_identifier != pipeline_identifier:
    st.session_state.pipeline_identifier = pipeline_identifier
    st.session_state.pipeline_ran = False
    st.session_state.classified = None
    st.session_state.affinity = None
    st.session_state.campaign = None

# Run Pipeline Button
run_pipeline = st.button("🚀 Run Pipeline")

if run_pipeline:
    st.session_state.pipeline_ran = True
    
    # Run the pipeline based on level
    if pipeline_level == "Individual User":
        # Individual User Pipeline
        
        # Step 1: Cohort Classification
        with st.spinner("📊 Step 1/3: Classifying user into cohort..."):
            classified = selected_user_data["classified_cohort_data"]
            st.session_state.classified = classified
        
        display_cohort_classification(st.session_state.classified)
        st.success("✅ Cohort classification completed!")

        
        # Step 2: Affinity Engine
        with st.spinner("🔗 Step 2/3: Calculating affinity scores..."):
            interaction = selected_user_data["interaction"]
            affinity = AffinityEngineAgent().run(interaction, product_website_url=product_link, brochure_url=brochure_url)
            st.session_state.affinity = affinity
        
        display_affinity_engine(st.session_state.affinity)
        st.success("✅ Affinity calculation completed!")
        
        # Step 3: Campaign Generation
        with st.spinner("🎯 Step 3/3: Generating campaign ideas..."):
            campaign = CampaignIdeaGeneratorAgent(
                source=interaction,
                classified_cohort=classified,
                affinity_score=affinity["affinity_scores"],
                brochure_url=brochure_url,
                product_website_url=product_link
            )
            campaign_output = campaign.run(num_of_campaign_ideas=5)
            st.session_state.campaign = campaign_output
        
        
        display_campaign_ideas(st.session_state.campaign)
        st.success("✅ Campaign generation completed!")
        
        # Display CTA Buttons
        display_cta_buttons(
            product_link=product_link,
            campaign_data=st.session_state.campaign,
        )
        
        # st.balloons()
        
    else:
        # Cohort Pipeline
        
        # Step 1: Cohort Classification
        with st.spinner("📊 Step 1/3: Loading cohort information..."):
            classified = selected_user_data[0]["classified_cohort_data"]
            st.session_state.classified = classified
        
        display_cohort_classification(st.session_state.classified)
        st.success("✅ Cohort information loaded!")

        # Step 2: Affinity Engine
        with st.spinner("🔗 Step 2/3: Calculating cohort affinity scores..."):
            affinity = AffinityEngineAgent().run(interaction_json=classified)
            st.session_state.affinity = affinity
        
        
        display_affinity_engine(st.session_state.affinity)
        st.success("✅ Affinity calculation completed!")
        
        # Step 3: Campaign Generation
        with st.spinner("🎯 Step 3/3: Generating cohort campaign ideas..."):
            campaign = CampaignIdeaGeneratorAgent(
                source=None,
                classified_cohort=classified,
                affinity_score=affinity["affinity_scores"],
                brochure_url=brochure_url,
                product_website_url=product_link
            )
            campaign_output = campaign.run(num_of_campaign_ideas=5)
            st.session_state.campaign = campaign_output
        
        display_campaign_ideas(st.session_state.campaign)
        st.success("✅ Campaign generation completed!")
        
        # Display CTA Buttons
        display_cta_buttons(
            product_link=product_link,
            campaign_data=st.session_state.campaign,
        )
        
        st.balloons()

# Display cached results if pipeline has already been run (not re-running)
elif st.session_state.get("pipeline_ran", False):
    # Display Cohort Classification
    if st.session_state.classified:
        display_cohort_classification(st.session_state.classified)
    
    # Display Affinity Engine
    if st.session_state.affinity:
        display_affinity_engine(st.session_state.affinity)
    
    # Display Campaign Ideas
    if st.session_state.campaign:
        display_campaign_ideas(st.session_state.campaign)
    
    # Display CTA Buttons
    if st.session_state.campaign:
        is_individual = isinstance(st.session_state.campaign, list)
        display_cta_buttons(
            product_link=product_link,
            campaign_data=st.session_state.campaign,
        )



# Aircross Brochure - https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/f12810c0-e7d4-41ab-86aa-f0a939e96e2a-6966058a_AircrossX_Brochure_30.10.pdf
# BasaltX Brochure - https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/7667686b-e77c-4cfb-8a66-c0a1fd6ea223-696605db_BasaltX_Brochure_30.10.pdf
# Meredian Brochure - https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/1f0e5109-ead3-42e9-8af8-b58b8942b10f-6966062a_New-Jeep-Meridian-Brochure.pdf

