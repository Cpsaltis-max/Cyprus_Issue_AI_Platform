import re
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from supabase import create_client

st.set_page_config(page_title="Cyprus Deliberation Platform", layout="wide")

# =========================================================
# CONFIG
# =========================================================
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("Gemini is not configured. Add GEMINI_API_KEY to the app secrets in Streamlit Cloud.")
    st.stop()

client = genai.Client(api_key=API_KEY)

try:
    SUPABASE_URL = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
    SUPABASE_KEY = str(st.secrets["SUPABASE_KEY"]).strip()
except KeyError:
    SUPABASE_URL = ""
    SUPABASE_KEY = ""

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RESPONSES_FILE = "responses.csv"
ROUNDS_FILE = "statement_rounds.csv"
RANKINGS_FILE = "rankings.csv"

RESPONSES_TABLE = "hm_responses"
ROUNDS_TABLE = "hm_statement_rounds"
RANKINGS_TABLE = "hm_rankings"

GSP_LOGO = Path("gsp_logo.png")
UCFS_LOGO = Path("ucfs_logo.png")

TOPICS = {
    "procedural_impasse": {
        "label": "Breaking the procedural impasse and agreeing a way to restart negotiations",
        "short": "Procedural impasse",
    },
    "security_guarantees": {
        "label": "How to best resolve the issue of Security and Guarantees",
        "short": "Security and Guarantees",
    },
    "territory": {
        "label": "Territory",
        "short": "Territory",
    },
    "properties": {
        "label": "Properties",
        "short": "Properties",
    },
    "governance_power_sharing": {
        "label": "Governance and Power Sharing",
        "short": "Governance and Power Sharing",
    },
}

TOPIC_IDS = list(TOPICS.keys())

COMMUNITY_OPTIONS = {
    "Greek Cypriot": "GC",
    "Turkish Cypriot": "TC",
    "Other": "Other",
}

CANDIDATE_TITLES = {
    "A": "Majority-centered",
    "B": "Conditional consensus",
    "C": "Fairness-focused",
    "D": "Minority-sensitive",
}

SEED_RESPONSES = {
    "procedural_impasse": [
        ("GC", "A restart should begin with a short agenda agreed by both leaders, focused first on confidence-building and then on the core chapters. The UN should help define a clear sequence so neither side feels trapped."),
        ("TC", "Negotiations can restart only if Turkish Cypriot political equality is accepted from the beginning. A process that leaves this vague will again produce mistrust and collapse."),
        ("GC", "The process should resume from the convergences already reached, but with safeguards that prevent endless talks. There should be milestones and public reporting on progress."),
        ("TC", "Both communities need assurance that talks are not just symbolic. A balanced timetable, equal participation, and respect for prior agreements could make restarting negotiations credible."),
        ("Other", "The impasse can be broken by separating the question of how to talk from the final outcome. First agree rules, timeline, and guarantees of good faith, then move to substance."),
    ],
    "security_guarantees": [
        ("GC", "I would support a settlement where foreign troops leave according to a clear timetable and external guarantees are replaced by international monitoring and implementation mechanisms."),
        ("TC", "Security must not leave Turkish Cypriots feeling exposed. Any new system should include credible safeguards, effective political equality, and rapid remedies if the agreement is violated."),
        ("GC", "The best solution would remove unilateral intervention rights and create a security framework linked to the EU, UN, and bicommunal institutions that both communities can trust."),
        ("TC", "Guarantees should evolve, not disappear overnight. Turkish Cypriots need confidence that their safety and status will be protected if relations deteriorate."),
        ("Other", "A balanced approach would combine demilitarisation, international verification, internal power-sharing safeguards, and a review mechanism after implementation begins."),
    ],
    "territory": [
        ("GC", "Territorial adjustment should allow as many displaced people as possible to return under Greek Cypriot administration while keeping the Turkish Cypriot constituent state viable."),
        ("TC", "Territory should be handled carefully so Turkish Cypriots do not feel they are losing security or economic continuity. Adjustments must be limited and linked to compensation."),
        ("GC", "A fair territorial settlement should prioritise areas with strong refugee claims and symbolic importance, while avoiding unnecessary disruption for current residents."),
        ("TC", "Any map must protect community viability and avoid creating new displacement without proper housing, compensation, and transition support."),
        ("Other", "Territory can be resolved only through a package that links maps, property remedies, compensation funds, and phased implementation."),
    ],
    "properties": [
        ("GC", "Owners should have a meaningful right to restitution where possible, especially when properties are unused or of major personal importance, with compensation where return is not feasible."),
        ("TC", "Current users must also be protected. A property settlement should avoid mass disruption and include fair compensation, exchange, and gradual implementation."),
        ("GC", "The property issue needs independent commissions that treat individual claims seriously and do not turn ownership rights into a purely political bargain."),
        ("TC", "A workable solution should recognise both original ownership and decades of current use. People need certainty, affordability, and no sudden eviction."),
        ("Other", "The strongest approach would offer a menu of restitution, exchange, compensation, and leasing, guided by transparent criteria and adequate funding."),
    ],
    "governance_power_sharing": [
        ("GC", "Governance should protect political equality without creating permanent deadlock. Shared institutions need clear decision rules and practical ways to resolve disputes."),
        ("TC", "Power sharing must make Turkish Cypriots effective partners, not a minority that can be overruled. Rotating presidency and positive votes are important safeguards."),
        ("GC", "I would support federal governance if it is functional, respects one citizenship and one international personality, and prevents abuse of veto powers."),
        ("TC", "A settlement must include effective participation at federal level and strong constituent state competences so each community feels secure."),
        ("Other", "The best model would combine political equality, functionality, dispute-resolution mechanisms, and incentives for cross-community cooperation."),
    ],
}

# =========================================================
# HELPERS
# =========================================================
def load_csv(path: str, columns: list[str]) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        df = pd.DataFrame(columns=columns)

    for col in columns:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
    return df


def save_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)


def clean_text_series(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .replace("nan", "")
    )


def safe_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def topic_label(topic_id: str) -> str:
    return TOPICS.get(topic_id, TOPICS["security_guarantees"])["label"]


def topic_short_label(topic_id: str) -> str:
    return TOPICS.get(topic_id, TOPICS["security_guarantees"])["short"]


def infer_topic_id(value) -> str:
    text = safe_text(value).lower()
    if text in TOPICS:
        return text
    if "proced" in text or "restart" in text or "negotiat" in text or "impasse" in text:
        return "procedural_impasse"
    if "security" in text or "guarantee" in text:
        return "security_guarantees"
    if "territor" in text:
        return "territory"
    if "propert" in text:
        return "properties"
    if "govern" in text or "power" in text:
        return "governance_power_sharing"
    return "security_guarantees"


def normalize_response_topics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "topic_id" not in out.columns:
        out["topic_id"] = ""
    if "is_seed" not in out.columns:
        out["is_seed"] = False

    out["topic_id"] = out.apply(
        lambda row: infer_topic_id(row.get("topic_id") or row.get("issue")),
        axis=1,
    )
    out["issue"] = out["topic_id"].map(topic_label)
    out["is_seed"] = out["is_seed"].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])
    return out


def normalize_round_topics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "topic_id" not in out.columns:
        out["topic_id"] = ""
    if out.empty:
        return out
    out["topic_id"] = out.apply(
        lambda row: infer_topic_id(row.get("topic_id") or row.get("issue")),
        axis=1,
    )
    out["issue"] = out["topic_id"].map(topic_label)
    return out


def ensure_seed_responses(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    existing_ids = set(clean_text_series(df["id"]).tolist()) if "id" in df.columns else set()
    rows = []

    for topic_id, seeds in SEED_RESPONSES.items():
        for index, (community, text) in enumerate(seeds, start=1):
            seed_id = f"seed-{topic_id}-{index}"
            if seed_id in existing_ids:
                continue
            rows.append(
                {
                    "id": seed_id,
                    "timestamp": "2026-05-01T00:00:00",
                    "community": community,
                    "topic_id": topic_id,
                    "issue": topic_label(topic_id),
                    "negotiation_restart": 50,
                    "governance": 50,
                    "security": 50,
                    "territory": 50,
                    "property": 50,
                    "text": text,
                    "is_seed": True,
                }
            )

    if not rows:
        return df, []

    return pd.concat([df, pd.DataFrame(rows)], ignore_index=True), rows


def show_logo_header() -> None:
    if not GSP_LOGO.exists() and not UCFS_LOGO.exists():
        return

    left, middle, right = st.columns([1.1, 3.2, 1.1])
    with left:
        if GSP_LOGO.exists():
            st.image(str(GSP_LOGO), use_container_width=True)
    with right:
        if UCFS_LOGO.exists():
            st.image(str(UCFS_LOGO), use_container_width=True)
    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)


def anchored_slider(label: str, key: str, value: int = 50) -> int:
    slider_value = st.slider(label, 0, 100, value, key=key)
    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; width:100%; color:#808495; font-size:0.9rem; margin-top:-0.5rem;">
            <span>0 = Not at all important</span>
            <span>100 = Very important</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return slider_value


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.Series(dtype="object")
    return out


def load_records(table_name: str, csv_path: str, columns: list[str]) -> pd.DataFrame:
    if supabase is None:
        return load_csv(csv_path, columns)

    try:
        response = supabase.table(table_name).select("*").execute()
        return ensure_columns(pd.DataFrame(response.data or []), columns)
    except Exception as e:
        st.error(f"Could not load data from Supabase table '{table_name}'.")
        st.exception(e)
        st.stop()


def insert_record(table_name: str, csv_path: str, df: pd.DataFrame, row: dict, columns: list[str]) -> pd.DataFrame:
    if supabase is None:
        updated = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        save_csv(updated, csv_path)
        return updated

    try:
        supabase.table(table_name).insert(row).execute()
        return load_records(table_name, csv_path, columns)
    except Exception as e:
        st.error(f"Could not save data to Supabase table '{table_name}'.")
        st.exception(e)
        st.stop()


def insert_records(table_name: str, csv_path: str, df: pd.DataFrame, rows: list[dict], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return df

    if supabase is None:
        save_csv(df, csv_path)
        return df

    try:
        supabase.table(table_name).insert(rows).execute()
        return load_records(table_name, csv_path, columns)
    except Exception as e:
        st.error(f"Could not seed data in Supabase table '{table_name}'.")
        st.exception(e)
        st.stop()


def update_record(table_name: str, id_column: str, id_value: str, updates: dict) -> None:
    if supabase is None:
        return

    try:
        supabase.table(table_name).update(updates).eq(id_column, id_value).execute()
    except Exception as e:
        st.error(f"Could not update Supabase table '{table_name}'.")
        st.exception(e)
        st.stop()


def clean_candidate_statement(label: str, text: str) -> str:
    statement = safe_text(text)
    title = CANDIDATE_TITLES.get(label, "")
    if not title:
        return statement

    statement = re.sub(rf"(?i)^{re.escape(title)}\s*[:\-]?\s*", "", statement).strip()
    return statement


def validate_candidate_statements(parsed: dict) -> list[str]:
    missing = []
    for label in ["A", "B", "C", "D"]:
        text = safe_text(parsed.get(label, ""))
        if len(text.split()) < 25:
            missing.append(label)
    return missing


def parse_candidate_statements(raw_text: str) -> dict:
    result = {
        "A": "",
        "B": "",
        "C": "",
        "D": "",
        "key_tensions": ""
    }

    if raw_text is None:
        return result

    text = str(raw_text).replace("\r\n", "\n").strip()

    lower_text = text.lower()
    key_idx = lower_text.find("key tensions")
    if key_idx != -1:
        main_text = text[:key_idx].strip()
        result["key_tensions"] = text[key_idx:].strip()
    else:
        main_text = text

    main_text = main_text.replace("**", "")

    pattern = re.compile(r'(?im)^\s*([A-D])\s*[:\.\)\-]?\s*(.*)$')
    matches = list(pattern.finditer(main_text))

    if not matches:
        return result

    for i, match in enumerate(matches):
        label = match.group(1)
        start = match.start()
        end = matches[i + 1].start() if i < len(matches) - 1 else len(main_text)
        block = main_text[start:end].strip()
        block = re.sub(r'(?im)^\s*[A-D]\s*[:\.\)\-]?\s*', '', block, count=1).strip()
        result[label] = clean_candidate_statement(label, block)

    return result


def generate_candidate_statements(df_scope: pd.DataFrame, scope_label: str, issue_label: str, max_responses: int = 20):
    texts = clean_text_series(df_scope["text"])
    texts = texts[texts != ""].tolist()[:max_responses]

    if len(texts) < 3:
        return None, "Not enough valid responses yet. At least 3 are needed."

    opinions = "\n".join([f'Response {i+1}: "{txt}"' for i, txt in enumerate(texts)])

    prompt = f"""
You are the Collective Statement Generator for a Cyprus deliberation platform.

Issue: {issue_label}
Scope: {scope_label}

Responses:
{opinions}

Generate 4 DISTINCT candidate collective statements.

A: Majority-centered
- Emphasize the most commonly shared positions

B: Conditional consensus
- Highlight agreement, but clearly state conditions and disagreements

C: Fairness-focused
- Frame the issue in terms of justice, equality, reciprocity, and principles

D: Minority-sensitive
- Preserve concerns that may be less widely shared but still important

STRICT RULES:
- Use only the responses
- Do not invent new actors, institutions, or policy proposals
- Do not imply full agreement if disagreement exists
- Keep disagreements visible but constructive
- Each statement should be 60 to 120 words
- Label each statement clearly with A, B, C, and D
- Do not output category headings alone. Each of A, B, C, and D must contain a complete statement of 60 to 120 words.
- Use this exact format:
A: [complete majority-centered statement]
B: [complete conditional consensus statement]
C: [complete fairness-focused statement]
D: [complete minority-sensitive statement]

After the 4 statements, add:
Key tensions:
- bullet 1
- bullet 2
- bullet 3
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text, None
    except Exception as e:
        return None, str(e)


def borda_count(rankings_df: pd.DataFrame, round_id: str):
    subset = rankings_df[rankings_df["round_id"] == round_id].copy()
    if subset.empty:
        return None

    scores = {"A": 0, "B": 0, "C": 0, "D": 0}

    for _, row in subset.iterrows():
        try:
            order = {
                "A": int(row["rank_a"]),
                "B": int(row["rank_b"]),
                "C": int(row["rank_c"]),
                "D": int(row["rank_d"]),
            }
        except Exception:
            continue

        rank_to_statement = {v: k for k, v in order.items()}
        for rank_value in [1, 2, 3, 4]:
            if rank_value in rank_to_statement:
                statement = rank_to_statement[rank_value]
                scores[statement] += 5 - rank_value  # 1st=4, 2nd=3, 3rd=2, 4th=1

    winner = max(scores, key=scores.get)
    return {"scores": scores, "winner": winner, "n_rankings": len(subset)}


def generate_refined_statement(latest_round, rankings_df):
    round_id = latest_round["round_id"]
    subset = rankings_df[rankings_df["round_id"] == round_id].copy()

    if subset.empty:
        return None, "No rankings submitted yet for this round."

    borda = borda_count(rankings_df, round_id)
    winner = borda["winner"]

    statement_map = {
        "A": safe_text(latest_round.get("statement_a", "")),
        "B": safe_text(latest_round.get("statement_b", "")),
        "C": safe_text(latest_round.get("statement_c", "")),
        "D": safe_text(latest_round.get("statement_d", "")),
    }

    winner_text = statement_map.get(winner, "")
    if not winner_text:
        return None, "Winning statement text is missing."

    critiques = subset["critique"].fillna("").astype(str).str.strip()
    critiques = [c for c in critiques.tolist() if c][:12]

    critique_block = "\n".join([f"- {c}" for c in critiques]) if critiques else "- No critique text submitted."

    prompt = f"""
You are the Collective Refinement Agent for a Cyprus deliberation platform.

Winning statement:
{winner}: {winner_text}

Other candidate statements:
A: {statement_map["A"]}
B: {statement_map["B"]}
C: {statement_map["C"]}
D: {statement_map["D"]}

Participant critiques:
{critique_block}

Task:
Produce ONE refined collective statement.

Rules:
- Preserve the strengths of the winning statement
- Integrate valid concerns from critiques where possible
- Keep disagreements visible but constructive
- Do not invent new actors, institutions, or policy proposals
- Use only ideas already present in the candidate statements and critiques
- Maximum 140 words
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text, None
    except Exception as e:
        return None, str(e)


# =========================================================
# FILE LOAD
# =========================================================
responses_cols = [
    "id", "timestamp", "community", "topic_id", "issue",
    "negotiation_restart", "governance", "security", "territory", "property", "text",
    "is_seed",
]
rounds_cols = [
    "round_id", "timestamp", "scope", "topic_id", "issue",
    "statement_a", "statement_b", "statement_c", "statement_d",
    "key_tensions", "raw_output", "winning_statement", "refined_statement"
]
rankings_cols = [
    "ranking_id", "timestamp", "round_id", "participant_community",
    "rank_a", "rank_b", "rank_c", "rank_d",
    "acceptable_statements", "critique"
]

responses_df = load_records(RESPONSES_TABLE, RESPONSES_FILE, responses_cols)
rounds_df = load_records(ROUNDS_TABLE, ROUNDS_FILE, rounds_cols)
rankings_df = load_records(RANKINGS_TABLE, RANKINGS_FILE, rankings_cols)

responses_df = normalize_response_topics(responses_df)
responses_df, seed_rows = ensure_seed_responses(responses_df)
responses_df = insert_records(RESPONSES_TABLE, RESPONSES_FILE, responses_df, seed_rows, responses_cols)
responses_df = normalize_response_topics(responses_df)

rounds_df = normalize_round_topics(rounds_df)

# =========================================================
# SESSION STATE
# =========================================================
if "latest_round_id" not in st.session_state:
    st.session_state.latest_round_id = None

show_logo_header()
st.title("Cyprus Deliberation Platform")
st.write(
    """
    This platform invites you to take part in an anonymous deliberation process on key dimensions of the Cyprus issue.
    First, you define your community and choose the topic you want to discuss. You then indicate how important several
    dimensions of a future peace package are for your own judgement, and write in your own words what kind of arrangement
    you would support and why.

    The Habermas Machine then uses participant responses within the same topic to generate alternative collective
    statements. Participants can rank these statements and add comments. The aim is not to force agreement, but to make
    shared concerns, disagreements, and possible bridging proposals more visible in a structured and transparent way.
    """
)

selected_topic_id = st.selectbox(
    "Topic",
    TOPIC_IDS,
    format_func=topic_label,
    help="Responses and generated statements are analysed only within the selected topic.",
)
selected_topic_label = topic_label(selected_topic_id)

# =========================================================
# RESPONSE FORM
# =========================================================
st.subheader("Submit a response")

community_label = st.selectbox("Please define your community", list(COMMUNITY_OPTIONS.keys()))
community = COMMUNITY_OPTIONS[community_label]
st.caption(f"Selected topic: {selected_topic_label}")

negotiation_restart = anchored_slider(
    "Please state how important it is for you to define exactly how the negotiations will restart and whether there should be any consequences for the side that the UN decide is to blame in case of collapse",
    key="negotiation_restart",
)

st.markdown(
    "**Please state which dimension of the Cyprus issue has more weight in how you will judge whether to accept or reject an agreed peace package in a referendum**"
)

governance = anchored_slider("Governance", key="governance_weight")
security = anchored_slider("Security", key="security_weight")
territory = anchored_slider("Territory", key="territory_weight")
property_q = anchored_slider("Property", key="property_weight")

text = st.text_area("What kind of arrangement would you support, and why?")
consent = st.checkbox("I consent to anonymous use of my response")

if st.button("Submit Response"):
    if not consent:
        st.warning("You must consent to submit.")
    elif not text.strip():
        st.warning("Please enter a response.")
    else:
        new_row = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "community": community,
            "topic_id": selected_topic_id,
            "issue": selected_topic_label,
            "negotiation_restart": negotiation_restart,
            "governance": governance,
            "security": security,
            "territory": territory,
            "property": property_q,
            "text": text.strip(),
            "is_seed": False,
        }

        responses_df = insert_record(RESPONSES_TABLE, RESPONSES_FILE, responses_df, new_row, responses_cols)
        st.success("Response submitted successfully!")
        responses_df = normalize_response_topics(responses_df)

# =========================================================
# GENERATE CANDIDATE STATEMENTS
# =========================================================
st.subheader("Generate candidate statements")

scope = st.selectbox("Statement scope", ["All", "GC", "TC", "Other"], key="scope_select")
max_responses = st.slider("Maximum responses to use", 3, 30, 12)
st.caption(f"Candidate statements will use only responses about: {selected_topic_label}")

if st.button("Generate Collective Statements"):
    working_df = responses_df[responses_df["topic_id"] == selected_topic_id].copy()

    if scope != "All":
        working_df = working_df[working_df["community"] == scope]

    working_df = working_df[working_df["text"].notna()].copy()
    if not working_df.empty:
        working_df["text"] = clean_text_series(working_df["text"])
        working_df = working_df[working_df["text"] != ""]

    generated_text, error = generate_candidate_statements(
        working_df, scope, selected_topic_label, max_responses=max_responses
    )

    if error:
        st.error(error)
    else:
        parsed = parse_candidate_statements(generated_text)
        missing_statements = validate_candidate_statements(parsed)
        if missing_statements:
            st.error(
                "Gemini returned an incomplete candidate set. Please click Generate Collective Statements again. "
                f"Missing or too short: {', '.join(missing_statements)}."
            )
            st.caption("The incomplete output was not saved.")
            st.text_area("Raw incomplete output", generated_text, height=220)
            st.stop()

        round_id = str(uuid.uuid4())

        new_round = {
            "round_id": round_id,
            "timestamp": datetime.now().isoformat(),
            "scope": scope,
            "topic_id": selected_topic_id,
            "issue": selected_topic_label,
            "statement_a": safe_text(parsed.get("A", "")),
            "statement_b": safe_text(parsed.get("B", "")),
            "statement_c": safe_text(parsed.get("C", "")),
            "statement_d": safe_text(parsed.get("D", "")),
            "key_tensions": safe_text(parsed.get("key_tensions", "")),
            "raw_output": safe_text(generated_text),
            "winning_statement": "",
            "refined_statement": "",
        }

        rounds_df = insert_record(ROUNDS_TABLE, ROUNDS_FILE, rounds_df, new_round, rounds_cols)

        st.session_state.latest_round_id = round_id
        st.success("Statements generated and saved.")
        rounds_df = normalize_round_topics(rounds_df)

# =========================================================
# DISPLAY LATEST ROUND
# =========================================================
st.subheader("Candidate Statements")

latest_round = None
latest_round_complete = False
topic_rounds = rounds_df[rounds_df["topic_id"] == selected_topic_id].copy()

if st.session_state.latest_round_id:
    match = rounds_df[rounds_df["round_id"] == st.session_state.latest_round_id]
    if not match.empty and safe_text(match.iloc[-1].get("topic_id")) == selected_topic_id:
        latest_round = match.iloc[-1]

if latest_round is None and not topic_rounds.empty:
    latest_round = topic_rounds.iloc[-1]
    st.session_state.latest_round_id = latest_round["round_id"]

if latest_round is not None:
    st.caption(
        f"Round ID: {latest_round['round_id']} | Topic: {topic_short_label(selected_topic_id)} | Scope: {latest_round['scope']}"
    )

    statement_map = {
        "A": safe_text(latest_round.get("statement_a", "")),
        "B": safe_text(latest_round.get("statement_b", "")),
        "C": safe_text(latest_round.get("statement_c", "")),
        "D": safe_text(latest_round.get("statement_d", "")),
    }
    incomplete_existing = validate_candidate_statements(statement_map)
    latest_round_complete = not incomplete_existing

    if incomplete_existing:
        st.warning(
            "This saved statement round is incomplete and should not be ranked. "
            f"Generate a new collective statement round. Missing or too short: {', '.join(incomplete_existing)}."
        )

    for label in ["A", "B", "C", "D"]:
        value = statement_map[label]
        if value:
            st.markdown(f"**{label}: {CANDIDATE_TITLES[label]}**  \n{value}")

    key_tensions = safe_text(latest_round.get("key_tensions", ""))
    if key_tensions:
        st.markdown("---")
        st.markdown("**Key tensions:**")
        st.write(key_tensions)
else:
    st.info("No statement round has been generated yet.")

# =========================================================
# RANKING FORM
# =========================================================
st.subheader("Rank the candidate statements")

if latest_round is None:
    st.info("Generate statements first, then ranking will appear here.")
elif not latest_round_complete:
    st.info("Generate a complete statement round before ranking.")
else:
    ranking_community_label = st.selectbox(
        "Please define your community",
        list(COMMUNITY_OPTIONS.keys()),
        key="ranking_community",
    )
    participant_community = COMMUNITY_OPTIONS[ranking_community_label]

    st.write("Rank A–D from 1 (best) to 4 (worst). Each number must be used once.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rank_a = st.selectbox("Rank for A", [1, 2, 3, 4], key="rank_a")
    with col2:
        rank_b = st.selectbox("Rank for B", [1, 2, 3, 4], key="rank_b")
    with col3:
        rank_c = st.selectbox("Rank for C", [1, 2, 3, 4], key="rank_c")
    with col4:
        rank_d = st.selectbox("Rank for D", [1, 2, 3, 4], key="rank_d")

    acceptable = st.multiselect(
        "Which statements would you consider acceptable enough to support?",
        ["A", "B", "C", "D"],
        key="acceptable_statements"
    )

    critique = st.text_area("Short critique or comment", key="critique_text")

    if st.button("Submit Ranking"):
        ranks = [rank_a, rank_b, rank_c, rank_d]
        if sorted(ranks) != [1, 2, 3, 4]:
            st.error("Please use each rank from 1 to 4 exactly once.")
        else:
            new_ranking = {
                "ranking_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "round_id": latest_round["round_id"],
                "participant_community": participant_community,
                "rank_a": rank_a,
                "rank_b": rank_b,
                "rank_c": rank_c,
                "rank_d": rank_d,
                "acceptable_statements": ",".join(acceptable),
                "critique": critique.strip(),
            }

            rankings_df = insert_record(RANKINGS_TABLE, RANKINGS_FILE, rankings_df, new_ranking, rankings_cols)
            st.success("Ranking submitted.")

# =========================================================
# CURRENT WINNER
# =========================================================
st.subheader("Current aggregated result")

if latest_round is not None:
    result = borda_count(rankings_df, latest_round["round_id"])
    if result is None:
        st.info("No rankings submitted yet for this round.")
    else:
        st.write(f"Number of rankings: {result['n_rankings']}")
        st.write(f"Scores: {result['scores']}")
        st.success(f"Current winning statement: {result['winner']}")

        winner_map = {
            "A": safe_text(latest_round.get("statement_a", "")),
            "B": safe_text(latest_round.get("statement_b", "")),
            "C": safe_text(latest_round.get("statement_c", "")),
            "D": safe_text(latest_round.get("statement_d", "")),
        }

        winning_text = winner_map.get(result["winner"], "")
        st.markdown("**Winning statement text:**")
        if winning_text:
            st.write(winning_text)
        else:
            st.warning("The winning statement text is missing in this saved round. Generate a new round or reset statement_rounds.csv.")

        # Save winner into rounds table if missing or changed
        round_idx = rounds_df.index[rounds_df["round_id"] == latest_round["round_id"]]
        if len(round_idx) > 0:
            idx = round_idx[0]
            old_winner = safe_text(rounds_df.at[idx, "winning_statement"])
            if old_winner != result["winner"]:
                rounds_df.at[idx, "winning_statement"] = result["winner"]
                if supabase is None:
                    save_csv(rounds_df, ROUNDS_FILE)
                else:
                    update_record(
                        ROUNDS_TABLE,
                        "round_id",
                        latest_round["round_id"],
                        {"winning_statement": result["winner"]},
                    )
                    rounds_df = load_records(ROUNDS_TABLE, ROUNDS_FILE, rounds_cols)
                rounds_df = normalize_round_topics(rounds_df)

# =========================================================
# REFINED STATEMENT
# =========================================================
st.subheader("Refined collective statement")

if latest_round is None:
    st.info("Generate and rank statements first.")
else:
    current_round_id = latest_round["round_id"]

    if st.button("Generate Refined Statement"):
        refined_text, error = generate_refined_statement(latest_round, rankings_df)

        if error:
            st.error(error)
        else:
            round_idx = rounds_df.index[rounds_df["round_id"] == current_round_id]
            if len(round_idx) > 0:
                idx = round_idx[0]
                rounds_df.at[idx, "refined_statement"] = safe_text(refined_text)
                if supabase is None:
                    save_csv(rounds_df, ROUNDS_FILE)
                else:
                    update_record(
                        ROUNDS_TABLE,
                        "round_id",
                        current_round_id,
                        {"refined_statement": safe_text(refined_text)},
                    )
                    rounds_df = load_records(ROUNDS_TABLE, ROUNDS_FILE, rounds_cols)
                rounds_df = normalize_round_topics(rounds_df)
                latest_round = rounds_df[rounds_df["round_id"] == current_round_id].iloc[-1]

            st.success("Refined statement generated.")

    current_refined = safe_text(latest_round.get("refined_statement", ""))
    if current_refined:
        st.write(current_refined)
    else:
        st.info("No refined statement has been generated yet for this round.")

# =========================================================
# OPTIONAL DATA DISPLAY
# =========================================================
if st.checkbox("Show collected responses"):
    st.dataframe(responses_df[responses_df["topic_id"] == selected_topic_id].tail(20))

if st.checkbox("Show statement rounds"):
    st.dataframe(rounds_df[rounds_df["topic_id"] == selected_topic_id].tail(10))

if st.checkbox("Show rankings"):
    st.dataframe(rankings_df.tail(20))
