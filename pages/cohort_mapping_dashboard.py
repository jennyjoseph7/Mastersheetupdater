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
import io
import random

from agents.cohort_generation_agent import ProductCohortGenerationAgent
from agents.cohort_classification_agent import CohortClassificationAgent
# from agents.campaign_idea_generator_agent import CampaignIdeaGeneratorAgent
# from agents.conversation_agent import DemoConversationAgent
# from agents.affinity_agent import AffinityEngineAgent
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
    st.write("Product Knowledge → Cohorts →")

setup_header()

def setup_session_state():
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
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "classification_results" not in st.session_state:
        st.session_state.classification_results = None
    if "failed_rows" not in st.session_state:
        st.session_state.failed_rows = None
    if "stop_classification" not in st.session_state:
        st.session_state.stop_classification = False
    if st.sidebar.button("🔄 Reset Pipeline"):
        for key in DEFAULT_KEYS:
            st.session_state[key] = None
        st.session_state.pipeline_ran = False
        st.session_state.pipeline_identifier = None
        st.session_state.classified = None
        st.session_state.affinity = None
        st.session_state.campaign = None
        st.session_state.classification_results = None
        st.session_state.failed_rows = None
        st.rerun()

setup_session_state()


def filter_cohort_dict(cohorts: Union[dict, list]) -> list:
    if isinstance(cohorts, dict) and "cohorts" in cohorts: 
        f_cohorts = cohorts["cohorts"]
        return f_cohorts
    if isinstance(cohorts, list):
        return cohorts
    raise ValueError("Invalid cohorts format. Expected a list or an object with a 'cohorts' key.")

tabs = ["Affinity Engine & Customer Profiling", "AskBot"]

affinity_engine_and_customer_profiling, askbot = st.tabs(tabs)

with affinity_engine_and_customer_profiling:
    st.subheader("1️⃣ Product Knowledge → Cohorts")
    st.markdown("(Either provide Product URL or Brochure PDF, or upload your own Cohort Registry JSON)")
    col1, col2, col3 = st.columns(3)

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

    with col3:
        uploaded_cohort_file = st.file_uploader(
            label="Upload Cohort Registry JSON",
            type=["json"],
            help="Upload a JSON file with a 'cohorts' key containing your cohort registry."
        )
        if uploaded_cohort_file is not None:
            try:
                uploaded_cohorts = json.load(uploaded_cohort_file)
                cohorts = filter_cohort_dict(uploaded_cohorts)
                st.session_state.cohorts = cohorts
                st.success(f"✅ Loaded {len(st.session_state.cohorts)} cohorts from uploaded file.")
            except (json.JSONDecodeError, Exception) as e:
                st.error(f"Failed to parse JSON: {e}")

    if st.button("Generate Cohorts", disabled=uploaded_cohort_file is not None):
        if not product_link and not brochure_url:
            st.error("Provide either Product URL or Brochure PDF")
        else:
            with st.spinner("Generating cohorts... (this may take a few minutes)"):
                cohort_generation_agent: object = ProductCohortGenerationAgent(product_website_url=product_link, brochure_url=brochure_url)
                cohorts: list = cohort_generation_agent.run()['cohorts']
                st.session_state.cohorts = cohorts

    if st.session_state.cohorts:
        st.success("✅️ {} Cohorts Generated.".format(len(st.session_state.cohorts)))
        cohort_rows = []
        for cohort in st.session_state.cohorts:
            logger.info(f"Cohort: {cohort}")
            kv_dict = {key : value for key, value in cohort.items()}
            cohort_rows.append(kv_dict)
        cohorts_df = pd.DataFrame(cohort_rows)
        if "idx" in cohorts_df.columns:
            cohorts_df = cohorts_df.set_index("idx")
        st.dataframe(cohorts_df, use_container_width=True)
    else:
        st.warning("⚠️️ Cohorts Registry is empty.")
        st.stop()

    st.divider()

    def build_clusters(classified_users):
        clusters = defaultdict(list)
        for u in classified_users:
            cohort_id = u["classified_cohort_data"]["cohort_id"]
            clusters[cohort_id].append(u)
        return clusters

    def classify_users(users: list[dict], cohorts: list[dict], additional_instructions: str = ""):
        """
        Classifies users into cohorts.
        Returns:
            results (list[dict]): successfully classified rows
            failed_rows (list[dict]): rows that failed with error_trace
        """
        progress = st.progress(0)
        status = st.empty()
        stop_btn = st.empty()
        total = len(users)
        results = []
        failed_rows = []

        for idx, interaction in enumerate(users):
            user_id = interaction.get("user_id", f"u_{str(uuid.uuid4())}")
            status.markdown(f"**Classifying '{user_id}', Record {idx+1}/{total}**")

            if stop_btn.button("⛔ Stop Classification", key=f"stop_btn_{idx}"):
                st.session_state.stop_classification = True
                status.warning(f"⛔ Classification stopped by user after {idx} record(s).")
                break

            try:
                cohort_classification_agent = CohortClassificationAgent(
                    source=interaction,
                    cohorts=cohorts,
                    brochure_url=None,
                    product_website_url=None,
                    additional_instruction=additional_instructions  # pass instructions to agent
                )
                classified: dict = cohort_classification_agent.run()

                if "error" in classified:
                    raise ValueError(f"Agent returned error: {classified['error']}")

                p_cohort = classified.get("cohort_id", classified.get("primary_classified_cohort_id"))
                s_cohorts = classified.get("secondary_classified_cohort_ids", [])
                reasoning = classified.get("reasoning")
                confidence_score = float(classified.get("confidence_score", 0))

                classified_cohort_data = next(
                    (c for c in cohorts if c["cohort_id"] == p_cohort), {}
                )

                payload = {
                    **interaction,  # preserve original columns first
                    "primary_classified_cohort_id": p_cohort,
                    "primary_classified_cohort_name": classified_cohort_data.get("cohort_name", ""),
                    "primary_classified_cohort_data": json.dumps(classified_cohort_data),
                    "secondary_classified_cohort_ids": json.dumps(s_cohorts),
                    "classification_reasoning": reasoning,
                    "confidence_score": confidence_score,
                    "assignment_mode": "ai_assisted",
                }

                if "campaign_id" in classified_cohort_data:
                    payload["campaign_id"] = classified_cohort_data["campaign_id"]

                results.append(payload)

            except Exception as e:
                error_trace = traceback.format_exc()
                logger.error(f"Failed to classify user {user_id}: {error_trace}")
                failed_rows.append({
                    **interaction,
                    "error_message": str(e),
                    "error_trace": error_trace,
                })

            progress.progress((idx + 1) / total)

        stop_btn.empty()
        status.empty()
        return results, failed_rows
    
    def random_assign_users(users: list[dict], cohorts: list[dict], seed: int = 42) -> list[dict]:
        """
        Randomly assigns cohorts to users guaranteeing every cohort is used at least once.

        Strategy:
          1. Shuffle cohort list with the given seed.
          2. Tile shuffled cohorts to cover all users (round-robin), then shuffle
             that full assignment list so the final order is random — not striped.
          3. Each user gets exactly one cohort; all cohorts appear >= floor(n/k) times
             and at most ceil(n/k) times, so distribution is as balanced as possible
             while still being random.
        """
        rng = random.Random(seed)
        n, k = len(users), len(cohorts)

        shuffled_cohorts = cohorts[:]
        rng.shuffle(shuffled_cohorts)

        # Tile: repeat the shuffled list enough times to cover all users
        tiled = (shuffled_cohorts * (n // k + 1))[:n]
        # Final shuffle so assignment order isn't round-robin striped
        rng.shuffle(tiled)

        results = []
        for interaction, cohort in zip(users, tiled):
            payload = {
                **interaction,
                "primary_classified_cohort_id": cohort.get("cohort_id", ""),
                "primary_classified_cohort_name": cohort.get("cohort_name", ""),
                "primary_classified_cohort_data": json.dumps(cohort),
                "secondary_classified_cohort_ids": "[]",
                "classification_reasoning": "Randomly assigned (no AI classification)",
                "confidence_score": None,
                "assignment_mode": "random",
            }
            if "campaign_id" in cohort:
                payload["campaign_id"] = cohort["campaign_id"]
            results.append(payload)
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
            # df = df.sample(n=min(10, len(df)), random_state=42)
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

    # ── Additional Instructions ──────────────────────────────────────────────
    st.subheader("3️⃣ Classification Settings")

    assignment_mode = st.radio(
        "Assignment Mode",
        options=["🤖 AI Agent Classification", "🎲 Random Assignment"],
        horizontal=True,
        help=(
            "AI Agent: Uses the classification agent to intelligently assign cohorts based on user data.\n\n"
            "Random: Randomly assigns cohorts ensuring every cohort is used at least once — "
            "useful for baseline testing or when interaction data is unavailable."
        )
    )
    use_random = assignment_mode == "🎲 Random Assignment"

    if use_random:
        st.info(
            "ℹ️ **Random Assignment** — All cohorts will be used at least once. "
            "Users are distributed as evenly as possible across all cohorts, then shuffled so the order is random."
        )
        # rand_col1, rand_col2 = st.columns([1, 2])
        # with rand_col1:
        random_seed = st.number_input(
            "Random Seed",
            min_value=0,
            max_value=99999,
            value=42,
            step=1,
            help="Fix the seed to get reproducible results. Change it to get a different random assignment."
        )
        # with rand_col2:
        if data and st.session_state.cohorts:
            n_users = len(data["users"])
            n_cohorts = len(st.session_state.cohorts)
            op = divmod(n_users, n_cohorts)
            base, extra = op

            logger.info(f" Output : {op}")

            st.markdown(f"**Preview:** {n_users} users → {n_cohorts} cohorts. | {n_cohorts - extra} cohort(s) will get **{base}** users. | {extra} cohort(s) will get **{base + 1}** users.")
        additional_instructions = ""  # not used in random mode

    else:
        additional_instructions = st.text_area(
            label="Additional Instructions for Cohort Classification (optional)",
            placeholder=(
                "e.g. 'Prioritize price-sensitive cohorts for users with low income signals.'\n"
                "'If location is rural, lean towards utility-focused cohorts.'\n"
                "'Treat missing age as 30-35 range.'"
            ),
            height=120,
            help="These instructions are passed directly to the classification agent for every user record."
        )
        random_seed = 42

    # ── Run Classification ───────────────────────────────────────────────────

    output_format = st.selectbox("Output Format", ["CSV", "JSON"], index=0)

    btn_label = "🎲 Run Random Assignment" if use_random else "▶️ Run AI Cohort Classification"
    run_classification = st.button(
        btn_label,
        disabled=st.session_state.cohorts is None or data is None,
        use_container_width=True
    )

    if run_classification:
        users = data["users"]
        if use_random:
            with st.spinner(f"Randomly assigning cohorts to {len(users)} user(s)..."):
                results = random_assign_users(
                    users=users,
                    cohorts=st.session_state.cohorts,
                    seed=int(random_seed)
                )
            failed_rows = []
            st.session_state.classification_results = results
            st.session_state.failed_rows = failed_rows
        else:
            with st.spinner(f"AI-classifying {len(users)} user(s)..."):
                results, failed_rows = classify_users(
                    users=users,
                    cohorts=st.session_state.cohorts,
                    additional_instructions=additional_instructions
                )
            if st.session_state.stop_classification:
                st.warning(f"⚠️ Classification was stopped early. Showing partial results for {len(results)} classified record(s).")
            st.session_state.stop_classification = False
            st.session_state.classification_results = results
            st.session_state.failed_rows = failed_rows

    # ── Show Results & Downloads ─────────────────────────────────────────────
    if st.session_state.classification_results is not None:
        results = st.session_state.classification_results
        failed_rows = st.session_state.failed_rows or []

        st.divider()
        st.subheader("4️⃣ Classification Results")

        success_count = len(results)
        fail_count = len(failed_rows)

        mode_used = "🎲 Random" if (results and results[0].get("assignment_mode") == "random") else "🤖 AI Agent"
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.metric("Mode", mode_used)
        metric_col2.metric("Total Processed", success_count + fail_count)
        metric_col3.metric("✅ Successfully Classified", success_count)
        metric_col4.metric("❌ Failed", fail_count)

        if results:
            results_df = pd.DataFrame(results)
            st.dataframe(results_df, use_container_width=True)

            # Cohort distribution bar chart
            if "primary_classified_cohort_id" in results_df.columns:
                dist = (
                    results_df["primary_classified_cohort_id"]
                    .value_counts()
                    .reset_index()
                )
                dist.columns = ["Cohort", "Count"]
                fig = px.bar(
                    dist, x="Cohort", y="Count",
                    title="Cohort Distribution",
                    labels={"Cohort": "Cohort", "Count": "Users Assigned"},
                    color="Count", color_continuous_scale="Blues"
                )
                fig.update_layout(showlegend=False, xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

            # Download: classified results
            if output_format == "CSV":
                output_bytes = results_df.to_csv(index=False).encode("utf-8")
                file_name = "classified_users.csv"
                mime = "text/csv"
            else:
                output_bytes = json.dumps(results, indent=2, default=str).encode("utf-8")
                file_name = "classified_users.json"
                mime = "application/json"

            st.download_button(
                label=f"⬇️ Download Classified Results ({output_format})",
                data=output_bytes,
                file_name=file_name,
                mime=mime,
                use_container_width=True,
            )

        # Download: failed rows (only relevant for AI mode)
        if failed_rows:
            st.warning(f"⚠️ {fail_count} record(s) failed classification. Download the error report below.")
            failed_df = pd.DataFrame(failed_rows)
            st.dataframe(failed_df[["user_id", "error_message", "error_trace"] if "user_id" in failed_df.columns else failed_df.columns], use_container_width=True)

            failed_csv = failed_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Failed Rows with Error Trace (CSV)",
                data=failed_csv,
                file_name="failed_classification_rows.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.success("🎉 All records classified successfully — no failures!")

# with askbot:
#     st.divider()
#     st.subheader("5️⃣ AskBot")
#     # askbot()