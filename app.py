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
        "label": {
            "en": "Breaking the procedural impasse and agreeing a way to restart negotiations",
            "el": "Ξ¥Ο€Ξ­ΟΞ²Ξ±ΟƒΞ· Ο„ΞΏΟ… Ξ΄ΞΉΞ±Ξ΄ΞΉΞΊΞ±ΟƒΟ„ΞΉΞΊΞΏΟ Ξ±Ξ΄ΞΉΞµΞΎΟΞ΄ΞΏΟ… ΞΊΞ±ΞΉ ΟƒΟ…ΞΌΟ†Ο‰Ξ½Ξ―Ξ± Ξ³ΞΉΞ± Ο„ΞΏΞ½ Ο„ΟΟΟ€ΞΏ ΞµΟ€Ξ±Ξ½Ξ­Ξ½Ξ±ΟΞΎΞ·Ο‚ Ο„Ο‰Ξ½ Ξ΄ΞΉΞ±Ο€ΟΞ±Ξ³ΞΌΞ±Ο„ΞµΟΟƒΞµΟ‰Ξ½",
            "tr": "Usule iliΕkin Γ§Δ±kmazΔ±n aΕΔ±lmasΔ± ve mΓΌzakerelerin yeniden baΕlamasΔ± iΓ§in bir yol ΓΌzerinde anlaΕΔ±lmasΔ±",
        },
        "short": {
            "en": "Procedural impasse",
            "el": "Ξ”ΞΉΞ±Ξ΄ΞΉΞΊΞ±ΟƒΟ„ΞΉΞΊΟ Ξ±Ξ΄ΞΉΞ­ΞΎΞΏΞ΄ΞΏ",
            "tr": "Usule iliΕkin Γ§Δ±kmaz",
        },
    },
    "security_guarantees": {
        "label": {
            "en": "How to best resolve the issue of Security and Guarantees",
            "el": "Ξ ΟΟ‚ ΞΌΟ€ΞΏΟΞµΞ― Ξ½Ξ± ΞµΟ€ΞΉΞ»Ο…ΞΈΞµΞ― ΞΊΞ±Ξ»ΟΟ„ΞµΟΞ± Ο„ΞΏ Ξ¶Ξ®Ο„Ξ·ΞΌΞ± Ο„Ξ·Ο‚ Ξ‘ΟƒΟ†Ξ¬Ξ»ΞµΞΉΞ±Ο‚ ΞΊΞ±ΞΉ Ο„Ο‰Ξ½ Ξ•Ξ³Ξ³Ο…Ξ®ΟƒΞµΟ‰Ξ½",
            "tr": "GΓΌvenlik ve Garantiler konusunun en iyi nasΔ±l Γ§Γ¶zΓΌlebileceΔi",
        },
        "short": {
            "en": "Security and Guarantees",
            "el": "Ξ‘ΟƒΟ†Ξ¬Ξ»ΞµΞΉΞ± ΞΊΞ±ΞΉ Ξ•Ξ³Ξ³Ο…Ξ®ΟƒΞµΞΉΟ‚",
            "tr": "GΓΌvenlik ve Garantiler",
        },
    },
    "territory": {
        "label": {"en": "Territory", "el": "Ξ•Ξ΄Ξ±Ο†ΞΉΞΊΟ", "tr": "Toprak"},
        "short": {"en": "Territory", "el": "Ξ•Ξ΄Ξ±Ο†ΞΉΞΊΟ", "tr": "Toprak"},
    },
    "properties": {
        "label": {"en": "Properties", "el": "Ξ ΞµΟΞΉΞΏΟ…ΟƒΞ―ΞµΟ‚", "tr": "MΓΌlkiyet"},
        "short": {"en": "Properties", "el": "Ξ ΞµΟΞΉΞΏΟ…ΟƒΞ―ΞµΟ‚", "tr": "MΓΌlkiyet"},
    },
    "governance_power_sharing": {
        "label": {
            "en": "Governance and Power Sharing",
            "el": "Ξ”ΞΉΞ±ΞΊΟ…Ξ²Ξ­ΟΞ½Ξ·ΟƒΞ· ΞΊΞ±ΞΉ ΞΞ±Ο„Ξ±Ξ½ΞΏΞΌΞ® Ξ•ΞΎΞΏΟ…ΟƒΞ―Ξ±Ο‚",
            "tr": "YΓ¶netim ve GΓΌΓ§ PaylaΕΔ±mΔ±",
        },
        "short": {
            "en": "Governance and Power Sharing",
            "el": "Ξ”ΞΉΞ±ΞΊΟ…Ξ²Ξ­ΟΞ½Ξ·ΟƒΞ· ΞΊΞ±ΞΉ ΞΞ±Ο„Ξ±Ξ½ΞΏΞΌΞ® Ξ•ΞΎΞΏΟ…ΟƒΞ―Ξ±Ο‚",
            "tr": "YΓ¶netim ve GΓΌΓ§ PaylaΕΔ±mΔ±",
        },
    },
}

TOPIC_IDS = list(TOPICS.keys())

COMMUNITY_OPTIONS = {
    "gc": "GC",
    "tc": "TC",
    "other": "Other",
}

CANDIDATE_TITLES = {
    "A": {"en": "Majority-centered", "el": "Ξ•ΟƒΟ„ΞΉΞ±ΟƒΞΌΞ­Ξ½Ξ· ΟƒΟ„Ξ·Ξ½ Ο€Ξ»ΞµΞΉΞΏΟΞ·Ο†Ξ―Ξ±", "tr": "Γ‡oΔunluk odaklΔ±"},
    "B": {"en": "Conditional consensus", "el": "Ξ¥Ο€Ο ΟΟΞΏΟ…Ο‚ ΟƒΟ…Ξ½Ξ±Ξ―Ξ½ΞµΟƒΞ·", "tr": "KoΕullu uzlaΕΔ±"},
    "C": {"en": "Fairness-focused", "el": "Ξ•ΟƒΟ„ΞΉΞ±ΟƒΞΌΞ­Ξ½Ξ· ΟƒΟ„Ξ· Ξ΄ΞΉΞΊΞ±ΞΉΞΏΟƒΟΞ½Ξ·", "tr": "Adalet odaklΔ±"},
    "D": {"en": "Minority-sensitive", "el": "Ξ•Ο…Ξ±Ξ―ΟƒΞΈΞ·Ο„Ξ· ΟƒΟ„ΞΉΟ‚ ΞΌΞµΞΉΞΏΟΞ·Ο†ΞΉΞΊΞ­Ο‚ Ξ±Ξ½Ξ·ΟƒΟ…Ο‡Ξ―ΞµΟ‚", "tr": "AzΔ±nlΔ±k kaygΔ±larΔ±na duyarlΔ±"},
}

LANGUAGE_OPTIONS = {
    "en": "English",
    "el": "Ξ•Ξ»Ξ»Ξ·Ξ½ΞΉΞΊΞ¬",
    "tr": "TΓΌrkΓ§e",
}

LANGUAGE_NAMES = {
    "en": "English",
    "el": "Greek",
    "tr": "Turkish",
}

T = {
    "en": {
        "title": "Cyprus Deliberation Platform",
        "intro": "This platform invites you to take part in an anonymous deliberation process on key dimensions of the Cyprus issue. First, you define your community and choose the topic you want to discuss. You then indicate how important several dimensions of a future peace package are for your own judgement, and write in your own words what kind of arrangement you would support and why.\n\nThe Habermas Machine then uses participant responses within the same topic to generate alternative collective statements. Participants can rank these statements and add comments. The aim is not to force agreement, but to make shared concerns, disagreements, and possible bridging proposals more visible in a structured and transparent way.",
        "language": "Language",
        "topic": "Topic",
        "topic_help": "Responses and generated statements are analysed only within the selected topic.",
        "submit_response": "Submit a response",
        "community": "Please define your community",
        "gc": "Greek Cypriot",
        "tc": "Turkish Cypriot",
        "other": "Other",
        "selected_topic": "Selected topic: {topic}",
        "restart_question": "Please state how important it is for you to define exactly how the negotiations will restart and whether there should be any consequences for the side that the UN decide is to blame in case of collapse",
        "dimension_question": "Please state which dimension of the Cyprus issue has more weight in how you will judge whether to accept or reject an agreed peace package in a referendum",
        "governance": "Governance",
        "security": "Security",
        "territory": "Territory",
        "property": "Property",
        "not_important": "0 = Not at all important",
        "very_important": "100 = Very important",
        "arrangement_question": "What kind of arrangement would you support, in relation to {topic}, and why?",
        "consent": "I consent to anonymous use of my response",
        "submit_button": "Submit Response",
        "must_consent": "You must consent to submit.",
        "enter_response": "Please enter a response.",
        "submitted": "Response submitted successfully!",
        "generate_title": "Generate candidate statements",
        "scope": "Statement scope",
        "all": "All",
        "max_responses": "Maximum responses to use",
        "candidate_caption": "Candidate statements will use only responses about: {topic}",
        "generate_button": "Generate Collective Statements",
        "incomplete_set": "Gemini returned an incomplete candidate set. Please click Generate Collective Statements again. Missing or too short: {labels}.",
        "not_saved": "The incomplete output was not saved.",
        "raw_output": "Raw incomplete output",
        "statements_saved": "Statements generated and saved.",
        "candidate_title": "Candidate Statements",
        "round_caption": "Round ID: {round_id} | Topic: {topic} | Scope: {scope}",
        "incomplete_saved": "This saved statement round is incomplete and should not be ranked. Generate a new collective statement round. Missing or too short: {labels}.",
        "key_tensions": "Key tensions:",
        "no_round": "No statement round has been generated yet.",
        "rank_title": "Rank the candidate statements",
        "generate_first": "Generate statements first, then ranking will appear here.",
        "generate_complete": "Generate a complete statement round before ranking.",
        "rank_instruction": "Rank A-D from 1 (best) to 4 (worst). Each number must be used once.",
        "rank_for": "Rank for {label}",
        "acceptable": "Which statements would you consider acceptable enough to support?",
        "critique": "Short critique or comment",
        "submit_ranking": "Submit Ranking",
        "rank_error": "Please use each rank from 1 to 4 exactly once.",
        "ranking_submitted": "Ranking submitted.",
        "current_result": "Current aggregated result",
        "no_rankings": "No rankings submitted yet for this round.",
        "number_rankings": "Number of rankings: {n}",
        "scores": "Scores: {scores}",
        "winner": "Current winning statement: {winner}",
        "winning_text": "Winning statement text:",
        "missing_winner": "The winning statement text is missing in this saved round. Generate a new round or reset statement_rounds.csv.",
        "refined_title": "Refined collective statement",
        "generate_and_rank": "Generate and rank statements first.",
        "refined_button": "Generate Refined Statement",
        "refined_saved": "Refined statement generated.",
        "no_refined": "No refined statement has been generated yet for this round.",
        "show_responses": "Show collected responses",
        "show_rounds": "Show statement rounds",
        "show_rankings": "Show rankings",
    },
    "el": {
        "title": "Ξ Ξ»Ξ±Ο„Ο†ΟΟΞΌΞ± Ξ”ΞΉΞ±Ξ²ΞΏΟΞ»ΞµΟ…ΟƒΞ·Ο‚ Ξ³ΞΉΞ± Ο„ΞΏ ΞΟ…Ο€ΟΞΉΞ±ΞΊΟ",
        "intro": "Ξ— Ο€Ξ»Ξ±Ο„Ο†ΟΟΞΌΞ± ΟƒΞ±Ο‚ Ο€ΟΞΏΟƒΞΊΞ±Ξ»ΞµΞ― Ξ½Ξ± ΟƒΟ…ΞΌΞΌΞµΟ„Ξ¬ΟƒΟ‡ΞµΟ„Ξµ Ξ±Ξ½ΟΞ½Ο…ΞΌΞ± ΟƒΞµ ΞΌΞΉΞ± Ξ΄ΞΉΞ±Ξ΄ΞΉΞΊΞ±ΟƒΞ―Ξ± Ξ΄ΞΉΞ±Ξ²ΞΏΟΞ»ΞµΟ…ΟƒΞ·Ο‚ Ξ³ΞΉΞ± Ξ²Ξ±ΟƒΞΉΞΊΞ­Ο‚ Ξ΄ΞΉΞ±ΟƒΟ„Ξ¬ΟƒΞµΞΉΟ‚ Ο„ΞΏΟ… ΞΟ…Ο€ΟΞΉΞ±ΞΊΞΏΟ. Ξ ΟΟΟ„Ξ± Ξ΄Ξ·Ξ»ΟΞ½ΞµΟ„Ξµ Ο„Ξ·Ξ½ ΞΊΞΏΞΉΞ½ΟΟ„Ξ·Ο„Ξ¬ ΟƒΞ±Ο‚ ΞΊΞ±ΞΉ ΞµΟ€ΞΉΞ»Ξ­Ξ³ΞµΟ„Ξµ Ο„ΞΏ ΞΈΞ­ΞΌΞ± Ο€ΞΏΟ… ΞΈΞ­Ξ»ΞµΟ„Ξµ Ξ½Ξ± ΟƒΟ…Ξ¶Ξ·Ο„Ξ®ΟƒΞµΟ„Ξµ. Ξ£Ο„Ξ· ΟƒΟ…Ξ½Ξ­Ο‡ΞµΞΉΞ± Ξ΄Ξ·Ξ»ΟΞ½ΞµΟ„Ξµ Ο€ΟΟƒΞΏ ΟƒΞ·ΞΌΞ±Ξ½Ο„ΞΉΞΊΞ­Ο‚ ΞµΞ―Ξ½Ξ±ΞΉ Ξ΄ΞΉΞ¬Ο†ΞΏΟΞµΟ‚ Ξ΄ΞΉΞ±ΟƒΟ„Ξ¬ΟƒΞµΞΉΟ‚ ΞµΞ½ΟΟ‚ ΞΌΞµΞ»Ξ»ΞΏΞ½Ο„ΞΉΞΊΞΏΟ Ο€Ξ±ΞΊΞ­Ο„ΞΏΟ… Ξ»ΟΟƒΞ·Ο‚ Ξ³ΞΉΞ± Ο„Ξ· Ξ΄ΞΉΞΊΞ® ΟƒΞ±Ο‚ ΞΊΟΞ―ΟƒΞ· ΞΊΞ±ΞΉ Ξ³ΟΞ¬Ο†ΞµΟ„Ξµ ΞΌΞµ Ξ΄ΞΉΞΊΞ¬ ΟƒΞ±Ο‚ Ξ»ΟΞ³ΞΉΞ± Ο„ΞΉ ΞµΞ―Ξ΄ΞΏΟ…Ο‚ Ξ΄ΞΉΞµΟ…ΞΈΞ­Ο„Ξ·ΟƒΞ· ΞΈΞ± Ο…Ο€ΞΏΟƒΟ„Ξ·ΟΞ―Ξ¶Ξ±Ο„Ξµ ΞΊΞ±ΞΉ Ξ³ΞΉΞ±Ο„Ξ―.\n\nΞ— ΞΞ·Ο‡Ξ±Ξ½Ξ® Habermas Ο‡ΟΞ·ΟƒΞΉΞΌΞΏΟ€ΞΏΞΉΞµΞ― Ξ­Ο€ΞµΞΉΟ„Ξ± Ο„ΞΉΟ‚ Ξ±Ο€Ξ±Ξ½Ο„Ξ®ΟƒΞµΞΉΟ‚ Ο„Ο‰Ξ½ ΟƒΟ…ΞΌΞΌΞµΟ„ΞµΟ‡ΟΞ½Ο„Ο‰Ξ½ ΟƒΟ„ΞΏ Ξ―Ξ΄ΞΉΞΏ ΞΈΞ­ΞΌΞ± Ξ³ΞΉΞ± Ξ½Ξ± Ξ΄Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ®ΟƒΞµΞΉ ΞµΞ½Ξ±Ξ»Ξ»Ξ±ΞΊΟ„ΞΉΞΊΞ­Ο‚ ΟƒΟ…Ξ»Ξ»ΞΏΞ³ΞΉΞΊΞ­Ο‚ Ξ΄Ξ·Ξ»ΟΟƒΞµΞΉΟ‚. ΞΞΉ ΟƒΟ…ΞΌΞΌΞµΟ„Ξ­Ο‡ΞΏΞ½Ο„ΞµΟ‚ ΞΌΟ€ΞΏΟΞΏΟΞ½ Ξ½Ξ± Ο„ΞΉΟ‚ ΞΊΞ±Ο„Ξ±Ο„Ξ¬ΞΎΞΏΟ…Ξ½ ΞΊΞ±ΞΉ Ξ½Ξ± Ο€ΟΞΏΟƒΞΈΞ­ΟƒΞΏΟ…Ξ½ ΟƒΟ‡ΟΞ»ΞΉΞ±. Ξ ΟƒΟ„ΟΟ‡ΞΏΟ‚ Ξ΄ΞµΞ½ ΞµΞ―Ξ½Ξ±ΞΉ Ξ½Ξ± ΞµΟ€ΞΉΞ²Ξ»Ξ·ΞΈΞµΞ― ΟƒΟ…ΞΌΟ†Ο‰Ξ½Ξ―Ξ±, Ξ±Ξ»Ξ»Ξ¬ Ξ½Ξ± Ξ³Ξ―Ξ½ΞΏΟ…Ξ½ Ο€ΞΉΞΏ ΞΏΟΞ±Ο„Ξ­Ο‚ ΞΏΞΉ ΞΊΞΏΞΉΞ½Ξ­Ο‚ Ξ±Ξ½Ξ·ΟƒΟ…Ο‡Ξ―ΞµΟ‚, ΞΏΞΉ Ξ΄ΞΉΞ±Ο†Ο‰Ξ½Ξ―ΞµΟ‚ ΞΊΞ±ΞΉ Ο€ΞΉΞΈΞ±Ξ½Ξ­Ο‚ Ξ³ΞµΟ†Ο…ΟΟ‰Ο„ΞΉΞΊΞ­Ο‚ Ο€ΟΞΏΟ„Ξ¬ΟƒΞµΞΉΟ‚ ΞΌΞµ Ξ΄ΞΏΞΌΞ·ΞΌΞ­Ξ½ΞΏ ΞΊΞ±ΞΉ Ξ΄ΞΉΞ±Ο†Ξ±Ξ½Ξ® Ο„ΟΟΟ€ΞΏ.",
        "language": "Ξ“Ξ»ΟΟƒΟƒΞ±",
        "topic": "ΞΞ­ΞΌΞ±",
        "topic_help": "ΞΞΉ Ξ±Ο€Ξ±Ξ½Ο„Ξ®ΟƒΞµΞΉΟ‚ ΞΊΞ±ΞΉ ΞΏΞΉ Ο€Ξ±ΟΞ±Ξ³ΟΞΌΞµΞ½ΞµΟ‚ Ξ΄Ξ·Ξ»ΟΟƒΞµΞΉΟ‚ Ξ±Ξ½Ξ±Ξ»ΟΞΏΞ½Ο„Ξ±ΞΉ ΞΌΟΞ½ΞΏ ΞΌΞ­ΟƒΞ± ΟƒΟ„ΞΏ ΞµΟ€ΞΉΞ»ΞµΞ³ΞΌΞ­Ξ½ΞΏ ΞΈΞ­ΞΌΞ±.",
        "submit_response": "Ξ¥Ο€ΞΏΞ²ΞΏΞ»Ξ® Ξ±Ο€Ξ¬Ξ½Ο„Ξ·ΟƒΞ·Ο‚",
        "community": "Ξ Ξ±ΟΞ±ΞΊΞ±Ξ»Ο ΞΏΟΞ―ΟƒΟ„Ξµ Ο„Ξ·Ξ½ ΞΊΞΏΞΉΞ½ΟΟ„Ξ·Ο„Ξ¬ ΟƒΞ±Ο‚",
        "gc": "Ξ•Ξ»Ξ»Ξ·Ξ½ΞΏΞΊΟΟ€ΟΞΉΞΏΟ‚/Ξ±",
        "tc": "Ξ¤ΞΏΟ…ΟΞΊΞΏΞΊΟΟ€ΟΞΉΞΏΟ‚/Ξ±",
        "other": "Ξ†Ξ»Ξ»ΞΏ",
        "selected_topic": "Ξ•Ο€ΞΉΞ»ΞµΞ³ΞΌΞ­Ξ½ΞΏ ΞΈΞ­ΞΌΞ±: {topic}",
        "restart_question": "Ξ Ξ±ΟΞ±ΞΊΞ±Ξ»Ο Ξ΄Ξ·Ξ»ΟΟƒΟ„Ξµ Ο€ΟΟƒΞΏ ΟƒΞ·ΞΌΞ±Ξ½Ο„ΞΉΞΊΟ ΞµΞ―Ξ½Ξ±ΞΉ Ξ³ΞΉΞ± ΞµΟƒΞ¬Ο‚ Ξ½Ξ± ΞΊΞ±ΞΈΞΏΟΞΉΟƒΟ„ΞµΞ― ΞΌΞµ Ξ±ΞΊΟΞ―Ξ²ΞµΞΉΞ± Ο€ΟΟ‚ ΞΈΞ± ΞµΟ€Ξ±Ξ½ΞµΞΊΞΊΞΉΞ½Ξ®ΟƒΞΏΟ…Ξ½ ΞΏΞΉ Ξ΄ΞΉΞ±Ο€ΟΞ±Ξ³ΞΌΞ±Ο„ΞµΟΟƒΞµΞΉΟ‚ ΞΊΞ±ΞΉ ΞΊΞ±Ο„Ξ¬ Ο€ΟΟƒΞΏ ΞΈΞ± Ο€ΟΞ­Ο€ΞµΞΉ Ξ½Ξ± Ο…Ο€Ξ¬ΟΟ‡ΞΏΟ…Ξ½ ΟƒΟ…Ξ½Ξ­Ο€ΞµΞΉΞµΟ‚ Ξ³ΞΉΞ± Ο„Ξ·Ξ½ Ο€Ξ»ΞµΟ…ΟΞ¬ Ο€ΞΏΟ… ΞΏ ΞΞ—Ξ• ΞΈΞ± ΞΊΟΞ―Ξ½ΞµΞΉ Ο…Ο€ΞµΟΞΈΟ…Ξ½Ξ· ΟƒΞµ Ο€ΞµΟΞ―Ο€Ο„Ο‰ΟƒΞ· ΞΊΞ±Ο„Ξ¬ΟΟΞµΟ…ΟƒΞ·Ο‚",
        "dimension_question": "Ξ Ξ±ΟΞ±ΞΊΞ±Ξ»Ο Ξ΄Ξ·Ξ»ΟΟƒΟ„Ξµ Ο€ΞΏΞΉΞ± Ξ΄ΞΉΞ¬ΟƒΟ„Ξ±ΟƒΞ· Ο„ΞΏΟ… ΞΟ…Ο€ΟΞΉΞ±ΞΊΞΏΟ Ξ­Ο‡ΞµΞΉ ΞΌΞµΞ³Ξ±Ξ»ΟΟ„ΞµΟΞ· Ξ²Ξ±ΟΟΟ„Ξ·Ο„Ξ± ΟƒΟ„ΞΏΞ½ Ο„ΟΟΟ€ΞΏ ΞΌΞµ Ο„ΞΏΞ½ ΞΏΟ€ΞΏΞ―ΞΏ ΞΈΞ± ΞΊΟΞ―Ξ½ΞµΟ„Ξµ Ξ±Ξ½ ΞΈΞ± Ξ±Ο€ΞΏΞ΄ΞµΟ‡ΞΈΞµΞ―Ο„Ξµ Ξ® ΞΈΞ± Ξ±Ο€ΞΏΟΟΞ―ΟΞµΟ„Ξµ Ξ­Ξ½Ξ± ΟƒΟ…ΞΌΟ†Ο‰Ξ½Ξ·ΞΌΞ­Ξ½ΞΏ Ο€Ξ±ΞΊΞ­Ο„ΞΏ ΞµΞΉΟΞ®Ξ½Ξ·Ο‚ ΟƒΞµ Ξ΄Ξ·ΞΌΞΏΟΞ®Ο†ΞΉΟƒΞΌΞ±",
        "governance": "Ξ”ΞΉΞ±ΞΊΟ…Ξ²Ξ­ΟΞ½Ξ·ΟƒΞ·",
        "security": "Ξ‘ΟƒΟ†Ξ¬Ξ»ΞµΞΉΞ±",
        "territory": "Ξ•Ξ΄Ξ±Ο†ΞΉΞΊΟ",
        "property": "Ξ ΞµΟΞΉΞΏΟ…ΟƒΞ―ΞµΟ‚",
        "not_important": "0 = ΞΞ±ΞΈΟΞ»ΞΏΟ… ΟƒΞ·ΞΌΞ±Ξ½Ο„ΞΉΞΊΟ",
        "very_important": "100 = Ξ ΞΏΞ»Ο ΟƒΞ·ΞΌΞ±Ξ½Ο„ΞΉΞΊΟ",
        "arrangement_question": "Ξ¤ΞΉ ΞµΞ―Ξ΄ΞΏΟ…Ο‚ Ξ΄ΞΉΞµΟ…ΞΈΞ­Ο„Ξ·ΟƒΞ· ΞΈΞ± Ο…Ο€ΞΏΟƒΟ„Ξ·ΟΞ―Ξ¶Ξ±Ο„Ξµ, ΟƒΞµ ΟƒΟ‡Ξ­ΟƒΞ· ΞΌΞµ Ο„ΞΏ ΞΈΞ­ΞΌΞ± {topic}, ΞΊΞ±ΞΉ Ξ³ΞΉΞ±Ο„Ξ―;",
        "consent": "Ξ£Ο…Ξ½Ξ±ΞΉΞ½Ο ΟƒΟ„Ξ·Ξ½ Ξ±Ξ½ΟΞ½Ο…ΞΌΞ· Ο‡ΟΞ®ΟƒΞ· Ο„Ξ·Ο‚ Ξ±Ο€Ξ¬Ξ½Ο„Ξ·ΟƒΞ®Ο‚ ΞΌΞΏΟ…",
        "submit_button": "Ξ¥Ο€ΞΏΞ²ΞΏΞ»Ξ® Ξ±Ο€Ξ¬Ξ½Ο„Ξ·ΟƒΞ·Ο‚",
        "must_consent": "Ξ ΟΞ­Ο€ΞµΞΉ Ξ½Ξ± Ξ΄ΟΟƒΞµΟ„Ξµ ΟƒΟ…Ξ³ΞΊΞ±Ο„Ξ¬ΞΈΞµΟƒΞ· Ξ³ΞΉΞ± Ξ½Ξ± Ο…Ο€ΞΏΞ²Ξ¬Ξ»ΞµΟ„Ξµ.",
        "enter_response": "Ξ Ξ±ΟΞ±ΞΊΞ±Ξ»Ο Ξ³ΟΞ¬ΟΟ„Ξµ ΞΌΞΉΞ± Ξ±Ο€Ξ¬Ξ½Ο„Ξ·ΟƒΞ·.",
        "submitted": "Ξ— Ξ±Ο€Ξ¬Ξ½Ο„Ξ·ΟƒΞ· Ο…Ο€ΞΏΞ²Ξ»Ξ®ΞΈΞ·ΞΊΞµ ΞΌΞµ ΞµΟ€ΞΉΟ„Ο…Ο‡Ξ―Ξ±!",
        "generate_title": "Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ―Ξ± Ο…Ο€ΞΏΟΞ®Ο†ΞΉΟ‰Ξ½ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½",
        "scope": "Ξ ΞµΞ΄Ξ―ΞΏ Ξ΄Ξ®Ξ»Ο‰ΟƒΞ·Ο‚",
        "all": "ΞΞ»ΞΏΞΉ",
        "max_responses": "ΞΞ­Ξ³ΞΉΟƒΟ„ΞΏΟ‚ Ξ±ΟΞΉΞΈΞΌΟΟ‚ Ξ±Ο€Ξ±Ξ½Ο„Ξ®ΟƒΞµΟ‰Ξ½ Ο€ΞΏΟ… ΞΈΞ± Ο‡ΟΞ·ΟƒΞΉΞΌΞΏΟ€ΞΏΞΉΞ·ΞΈΞΏΟΞ½",
        "candidate_caption": "ΞΞΉ Ο…Ο€ΞΏΟΞ®Ο†ΞΉΞµΟ‚ Ξ΄Ξ·Ξ»ΟΟƒΞµΞΉΟ‚ ΞΈΞ± Ο‡ΟΞ·ΟƒΞΉΞΌΞΏΟ€ΞΏΞΉΞ®ΟƒΞΏΟ…Ξ½ ΞΌΟΞ½ΞΏ Ξ±Ο€Ξ±Ξ½Ο„Ξ®ΟƒΞµΞΉΟ‚ Ξ³ΞΉΞ±: {topic}",
        "generate_button": "Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ―Ξ± ΟƒΟ…Ξ»Ξ»ΞΏΞ³ΞΉΞΊΟΞ½ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½",
        "incomplete_set": "Ξ¤ΞΏ Gemini ΞµΟ€Ξ­ΟƒΟ„ΟΞµΟΞµ ΞµΞ»Ξ»ΞΉΟ€Ξ­Ο‚ ΟƒΟΞ½ΞΏΞ»ΞΏ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½. Ξ Ξ±Ο„Ξ®ΟƒΟ„Ξµ ΞΎΞ±Ξ½Ξ¬ Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ―Ξ± ΟƒΟ…Ξ»Ξ»ΞΏΞ³ΞΉΞΊΟΞ½ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½. Ξ•Ξ»Ξ»ΞΉΟ€ΞµΞ―Ο‚ Ξ® Ο€ΞΏΞ»Ο ΟƒΟΞ½Ο„ΞΏΞΌΞµΟ‚: {labels}.",
        "not_saved": "Ξ¤ΞΏ ΞµΞ»Ξ»ΞΉΟ€Ξ­Ο‚ Ξ±Ο€ΞΏΟ„Ξ­Ξ»ΞµΟƒΞΌΞ± Ξ΄ΞµΞ½ Ξ±Ο€ΞΏΞΈΞ·ΞΊΞµΟΟ„Ξ·ΞΊΞµ.",
        "raw_output": "Ξ‘ΞΊΞ±Ο„Ξ­ΟΞ³Ξ±ΟƒΟ„ΞΏ ΞµΞ»Ξ»ΞΉΟ€Ξ­Ο‚ Ξ±Ο€ΞΏΟ„Ξ­Ξ»ΞµΟƒΞΌΞ±",
        "statements_saved": "ΞΞΉ Ξ΄Ξ·Ξ»ΟΟƒΞµΞΉΟ‚ Ξ΄Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ®ΞΈΞ·ΞΊΞ±Ξ½ ΞΊΞ±ΞΉ Ξ±Ο€ΞΏΞΈΞ·ΞΊΞµΟΟ„Ξ·ΞΊΞ±Ξ½.",
        "candidate_title": "Ξ¥Ο€ΞΏΟΞ®Ο†ΞΉΞµΟ‚ Ξ”Ξ·Ξ»ΟΟƒΞµΞΉΟ‚",
        "round_caption": "ID Ξ³ΟΟΞΏΟ…: {round_id} | ΞΞ­ΞΌΞ±: {topic} | Ξ ΞµΞ΄Ξ―ΞΏ: {scope}",
        "incomplete_saved": "Ξ‘Ο…Ο„ΟΟ‚ ΞΏ Ξ±Ο€ΞΏΞΈΞ·ΞΊΞµΟ…ΞΌΞ­Ξ½ΞΏΟ‚ Ξ³ΟΟΞΏΟ‚ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½ ΞµΞ―Ξ½Ξ±ΞΉ ΞµΞ»Ξ»ΞΉΟ€Ξ®Ο‚ ΞΊΞ±ΞΉ Ξ΄ΞµΞ½ Ο€ΟΞ­Ο€ΞµΞΉ Ξ½Ξ± ΞΊΞ±Ο„Ξ±Ο„Ξ±Ο‡ΞΈΞµΞ―. Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ®ΟƒΟ„Ξµ Ξ½Ξ­ΞΏ Ξ³ΟΟΞΏ. Ξ•Ξ»Ξ»ΞΉΟ€ΞµΞ―Ο‚ Ξ® Ο€ΞΏΞ»Ο ΟƒΟΞ½Ο„ΞΏΞΌΞµΟ‚: {labels}.",
        "key_tensions": "Ξ’Ξ±ΟƒΞΉΞΊΞ­Ο‚ ΞµΞ½Ο„Ξ¬ΟƒΞµΞΉΟ‚:",
        "no_round": "Ξ”ΞµΞ½ Ξ­Ο‡ΞµΞΉ Ξ΄Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ·ΞΈΞµΞ― Ξ±ΞΊΟΞΌΞ· Ξ³ΟΟΞΏΟ‚ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½.",
        "rank_title": "ΞΞ±Ο„Ξ¬Ο„Ξ±ΞΎΞ· Ο…Ο€ΞΏΟΞ®Ο†ΞΉΟ‰Ξ½ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½",
        "generate_first": "Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ®ΟƒΟ„Ξµ Ο€ΟΟΟ„Ξ± Ξ΄Ξ·Ξ»ΟΟƒΞµΞΉΟ‚ ΞΊΞ±ΞΉ ΞΌΞµΟ„Ξ¬ ΞΈΞ± ΞµΞΌΟ†Ξ±Ξ½ΞΉΟƒΟ„ΞµΞ― Ξ· ΞΊΞ±Ο„Ξ¬Ο„Ξ±ΞΎΞ·.",
        "generate_complete": "Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ®ΟƒΟ„Ξµ Ξ­Ξ½Ξ±Ξ½ Ο€Ξ»Ξ®ΟΞ· Ξ³ΟΟΞΏ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½ Ο€ΟΞΉΞ½ Ξ±Ο€Ο Ο„Ξ·Ξ½ ΞΊΞ±Ο„Ξ¬Ο„Ξ±ΞΎΞ·.",
        "rank_instruction": "ΞΞ±Ο„Ξ±Ο„Ξ¬ΞΎΟ„Ξµ Ο„ΞΉΟ‚ A-D Ξ±Ο€Ο 1 (ΞΊΞ±Ξ»ΟΟ„ΞµΟΞ·) Ξ­Ο‰Ο‚ 4 (Ο‡ΞµΞΉΟΟΟ„ΞµΟΞ·). ΞΞ¬ΞΈΞµ Ξ±ΟΞΉΞΈΞΌΟΟ‚ Ο€ΟΞ­Ο€ΞµΞΉ Ξ½Ξ± Ο‡ΟΞ·ΟƒΞΉΞΌΞΏΟ€ΞΏΞΉΞ·ΞΈΞµΞ― ΞΌΞ―Ξ± Ο†ΞΏΟΞ¬.",
        "rank_for": "ΞΞ±Ο„Ξ¬Ο„Ξ±ΞΎΞ· Ξ³ΞΉΞ± {label}",
        "acceptable": "Ξ ΞΏΞΉΞµΟ‚ Ξ΄Ξ·Ξ»ΟΟƒΞµΞΉΟ‚ ΞΈΞ± ΞΈΞµΟ‰ΟΞΏΟΟƒΞ±Ο„Ξµ Ξ±ΟΞΊΞµΟ„Ξ¬ Ξ±Ο€ΞΏΞ΄ΞµΞΊΟ„Ξ­Ο‚ ΟΟƒΟ„Ξµ Ξ½Ξ± Ο„ΞΉΟ‚ Ο…Ο€ΞΏΟƒΟ„Ξ·ΟΞ―ΞΎΞµΟ„Ξµ;",
        "critique": "Ξ£ΟΞ½Ο„ΞΏΞΌΞ· ΞΊΟΞΉΟ„ΞΉΞΊΞ® Ξ® ΟƒΟ‡ΟΞ»ΞΉΞΏ",
        "submit_ranking": "Ξ¥Ο€ΞΏΞ²ΞΏΞ»Ξ® ΞΊΞ±Ο„Ξ¬Ο„Ξ±ΞΎΞ·Ο‚",
        "rank_error": "Ξ Ξ±ΟΞ±ΞΊΞ±Ξ»Ο Ο‡ΟΞ·ΟƒΞΉΞΌΞΏΟ€ΞΏΞΉΞ®ΟƒΟ„Ξµ ΞΊΞ¬ΞΈΞµ ΞΊΞ±Ο„Ξ¬Ο„Ξ±ΞΎΞ· Ξ±Ο€Ο 1 Ξ­Ο‰Ο‚ 4 Ξ±ΞΊΟΞΉΞ²ΟΟ‚ ΞΌΞ―Ξ± Ο†ΞΏΟΞ¬.",
        "ranking_submitted": "Ξ— ΞΊΞ±Ο„Ξ¬Ο„Ξ±ΞΎΞ· Ο…Ο€ΞΏΞ²Ξ»Ξ®ΞΈΞ·ΞΊΞµ.",
        "current_result": "Ξ¤ΟΞ­Ο‡ΞΏΞ½ ΟƒΟ…Ξ³ΞΊΞµΞ½Ο„ΟΟ‰Ο„ΞΉΞΊΟ Ξ±Ο€ΞΏΟ„Ξ­Ξ»ΞµΟƒΞΌΞ±",
        "no_rankings": "Ξ”ΞµΞ½ Ξ­Ο‡ΞΏΟ…Ξ½ Ο…Ο€ΞΏΞ²Ξ»Ξ·ΞΈΞµΞ― Ξ±ΞΊΟΞΌΞ· ΞΊΞ±Ο„Ξ±Ο„Ξ¬ΞΎΞµΞΉΟ‚ Ξ³ΞΉΞ± Ξ±Ο…Ο„ΟΞ½ Ο„ΞΏΞ½ Ξ³ΟΟΞΏ.",
        "number_rankings": "Ξ‘ΟΞΉΞΈΞΌΟΟ‚ ΞΊΞ±Ο„Ξ±Ο„Ξ¬ΞΎΞµΟ‰Ξ½: {n}",
        "scores": "Ξ’Ξ±ΞΈΞΌΞΏΞ»ΞΏΞ³Ξ―ΞµΟ‚: {scores}",
        "winner": "Ξ¤ΟΞ­Ο‡ΞΏΟ…ΟƒΞ± Ξ½ΞΉΞΊΞ®Ο„ΟΞΉΞ± Ξ΄Ξ®Ξ»Ο‰ΟƒΞ·: {winner}",
        "winning_text": "ΞΞµΞ―ΞΌΞµΞ½ΞΏ Ξ½ΞΉΞΊΞ®Ο„ΟΞΉΞ±Ο‚ Ξ΄Ξ®Ξ»Ο‰ΟƒΞ·Ο‚:",
        "missing_winner": "Ξ¤ΞΏ ΞΊΞµΞ―ΞΌΞµΞ½ΞΏ Ο„Ξ·Ο‚ Ξ½ΞΉΞΊΞ®Ο„ΟΞΉΞ±Ο‚ Ξ΄Ξ®Ξ»Ο‰ΟƒΞ·Ο‚ Ξ»ΞµΞ―Ο€ΞµΞΉ Ξ±Ο€Ο Ξ±Ο…Ο„ΟΞ½ Ο„ΞΏΞ½ Ξ±Ο€ΞΏΞΈΞ·ΞΊΞµΟ…ΞΌΞ­Ξ½ΞΏ Ξ³ΟΟΞΏ.",
        "refined_title": "Ξ•Ο€ΞµΞΎΞµΟΞ³Ξ±ΟƒΞΌΞ­Ξ½Ξ· ΟƒΟ…Ξ»Ξ»ΞΏΞ³ΞΉΞΊΞ® Ξ΄Ξ®Ξ»Ο‰ΟƒΞ·",
        "generate_and_rank": "Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ®ΟƒΟ„Ξµ ΞΊΞ±ΞΉ ΞΊΞ±Ο„Ξ±Ο„Ξ¬ΞΎΟ„Ξµ Ο€ΟΟΟ„Ξ± Ξ΄Ξ·Ξ»ΟΟƒΞµΞΉΟ‚.",
        "refined_button": "Ξ”Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ―Ξ± ΞµΟ€ΞµΞΎΞµΟΞ³Ξ±ΟƒΞΌΞ­Ξ½Ξ·Ο‚ Ξ΄Ξ®Ξ»Ο‰ΟƒΞ·Ο‚",
        "refined_saved": "Ξ— ΞµΟ€ΞµΞΎΞµΟΞ³Ξ±ΟƒΞΌΞ­Ξ½Ξ· Ξ΄Ξ®Ξ»Ο‰ΟƒΞ· Ξ΄Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ®ΞΈΞ·ΞΊΞµ.",
        "no_refined": "Ξ”ΞµΞ½ Ξ­Ο‡ΞµΞΉ Ξ΄Ξ·ΞΌΞΉΞΏΟ…ΟΞ³Ξ·ΞΈΞµΞ― Ξ±ΞΊΟΞΌΞ· ΞµΟ€ΞµΞΎΞµΟΞ³Ξ±ΟƒΞΌΞ­Ξ½Ξ· Ξ΄Ξ®Ξ»Ο‰ΟƒΞ· Ξ³ΞΉΞ± Ξ±Ο…Ο„ΟΞ½ Ο„ΞΏΞ½ Ξ³ΟΟΞΏ.",
        "show_responses": "Ξ•ΞΌΟ†Ξ¬Ξ½ΞΉΟƒΞ· ΟƒΟ…Ξ»Ξ»ΞµΞ³ΞΌΞ­Ξ½Ο‰Ξ½ Ξ±Ο€Ξ±Ξ½Ο„Ξ®ΟƒΞµΟ‰Ξ½",
        "show_rounds": "Ξ•ΞΌΟ†Ξ¬Ξ½ΞΉΟƒΞ· Ξ³ΟΟΟ‰Ξ½ Ξ΄Ξ·Ξ»ΟΟƒΞµΟ‰Ξ½",
        "show_rankings": "Ξ•ΞΌΟ†Ξ¬Ξ½ΞΉΟƒΞ· ΞΊΞ±Ο„Ξ±Ο„Ξ¬ΞΎΞµΟ‰Ξ½",
    },
    "tr": {
        "title": "KΔ±brΔ±s MΓΌzakere Platformu",
        "intro": "Bu platform sizi KΔ±brΔ±s meselesinin temel boyutlarΔ± ΓΌzerine anonim bir mΓΌzakere sΓΌrecine katΔ±lmaya davet eder. Γ–nce topluluΔunuzu tanΔ±mlar ve tartΔ±Εmak istediΔiniz konuyu seΓ§ersiniz. Sonra gelecekteki bir barΔ±Ε paketini kabul veya reddetme kararΔ±nΔ±z iΓ§in bazΔ± boyutlarΔ±n ne kadar Γ¶nemli olduΔunu belirtir ve ne tΓΌr bir dΓΌzenlemeyi desteklediΔinizi kendi sΓ¶zlerinizle aΓ§Δ±klarsΔ±nΔ±z.\n\nHabermas Makinesi daha sonra aynΔ± konu iΓ§indeki katΔ±lΔ±mcΔ± yanΔ±tlarΔ±nΔ± kullanarak alternatif kolektif ifadeler ΓΌretir. KatΔ±lΔ±mcΔ±lar bu ifadeleri sΔ±ralayabilir ve yorum ekleyebilir. AmaΓ§ uzlaΕmayΔ± zorlamak deΔil, ortak kaygΔ±larΔ±, anlaΕmazlΔ±klarΔ± ve olasΔ± kΓ¶prΓΌ kurucu Γ¶nerileri yapΔ±landΔ±rΔ±lmΔ±Ε ve Εeffaf biΓ§imde daha gΓ¶rΓΌnΓΌr kΔ±lmaktΔ±r.",
        "language": "Dil",
        "topic": "Konu",
        "topic_help": "YanΔ±tlar ve ΓΌretilen ifadeler yalnΔ±zca seΓ§ilen konu iΓ§inde analiz edilir.",
        "submit_response": "YanΔ±t gΓ¶nder",
        "community": "LΓΌtfen topluluΔunuzu tanΔ±mlayΔ±n",
        "gc": "KΔ±brΔ±slΔ± Rum",
        "tc": "KΔ±brΔ±slΔ± TΓΌrk",
        "other": "DiΔer",
        "selected_topic": "SeΓ§ilen konu: {topic}",
        "restart_question": "MΓΌzakerelerin tam olarak nasΔ±l yeniden baΕlayacaΔΔ±nΔ±n ve Γ§Γ¶kΓΌΕ halinde BM'nin sorumlu gΓ¶rdΓΌΔΓΌ taraf iΓ§in herhangi bir sonuΓ§ olup olmayacaΔΔ±nΔ±n belirlenmesi sizin iΓ§in ne kadar Γ¶nemlidir?",
        "dimension_question": "Referandumda kabul edilmiΕ bir barΔ±Ε paketini kabul veya reddetme kararΔ±nΔ±zda KΔ±brΔ±s meselesinin hangi boyutunun daha fazla aΔΔ±rlΔ±Δa sahip olduΔunu belirtiniz",
        "governance": "YΓ¶netim",
        "security": "GΓΌvenlik",
        "territory": "Toprak",
        "property": "MΓΌlkiyet",
        "not_important": "0 = HiΓ§ Γ¶nemli deΔil",
        "very_important": "100 = Γ‡ok Γ¶nemli",
        "arrangement_question": "{topic} konusu bakΔ±mΔ±ndan ne tΓΌr bir dΓΌzenlemeyi desteklersiniz ve neden?",
        "consent": "YanΔ±tΔ±mΔ±n anonim olarak kullanΔ±lmasΔ±na onay veriyorum",
        "submit_button": "YanΔ±tΔ± gΓ¶nder",
        "must_consent": "GΓ¶ndermek iΓ§in onay vermelisiniz.",
        "enter_response": "LΓΌtfen bir yanΔ±t girin.",
        "submitted": "YanΔ±t baΕarΔ±yla gΓ¶nderildi!",
        "generate_title": "Aday ifadeler ΓΌret",
        "scope": "Δ°fade kapsamΔ±",
        "all": "TΓΌmΓΌ",
        "max_responses": "KullanΔ±lacak en fazla yanΔ±t sayΔ±sΔ±",
        "candidate_caption": "Aday ifadeler yalnΔ±zca Εu konuya iliΕkin yanΔ±tlarΔ± kullanacaktΔ±r: {topic}",
        "generate_button": "Kolektif ifadeler ΓΌret",
        "incomplete_set": "Gemini eksik bir aday ifade seti dΓ¶ndΓΌrdΓΌ. LΓΌtfen Kolektif ifadeler ΓΌret dΓΌΔmesine tekrar basΔ±n. Eksik veya Γ§ok kΔ±sa: {labels}.",
        "not_saved": "Eksik Γ§Δ±ktΔ± kaydedilmedi.",
        "raw_output": "Ham eksik Γ§Δ±ktΔ±",
        "statements_saved": "Δ°fadeler ΓΌretildi ve kaydedildi.",
        "candidate_title": "Aday Δ°fadeler",
        "round_caption": "Tur ID: {round_id} | Konu: {topic} | Kapsam: {scope}",
        "incomplete_saved": "Bu kayΔ±tlΔ± ifade turu eksik ve sΔ±ralanmamalΔ±dΔ±r. Yeni bir kolektif ifade turu ΓΌretin. Eksik veya Γ§ok kΔ±sa: {labels}.",
        "key_tensions": "Temel gerilimler:",
        "no_round": "HenΓΌz bir ifade turu ΓΌretilmedi.",
        "rank_title": "Aday ifadeleri sΔ±ralayΔ±n",
        "generate_first": "Γ–nce ifadeleri ΓΌretin; ardΔ±ndan sΔ±ralama burada gΓ¶rΓΌnecektir.",
        "generate_complete": "SΔ±ralamadan Γ¶nce eksiksiz bir ifade turu ΓΌretin.",
        "rank_instruction": "A-D ifadelerini 1'den (en iyi) 4'e (en kΓ¶tΓΌ) sΔ±ralayΔ±n. Her sayΔ± bir kez kullanΔ±lmalΔ±dΔ±r.",
        "rank_for": "{label} iΓ§in sΔ±ra",
        "acceptable": "Hangi ifadeleri desteklemek iΓ§in yeterince kabul edilebilir bulursunuz?",
        "critique": "KΔ±sa eleΕtiri veya yorum",
        "submit_ranking": "SΔ±ralamayΔ± gΓ¶nder",
        "rank_error": "LΓΌtfen 1'den 4'e kadar her sΔ±rayΔ± tam olarak bir kez kullanΔ±n.",
        "ranking_submitted": "SΔ±ralama gΓ¶nderildi.",
        "current_result": "Mevcut toplu sonuΓ§",
        "no_rankings": "Bu tur iΓ§in henΓΌz sΔ±ralama gΓ¶nderilmedi.",
        "number_rankings": "SΔ±ralama sayΔ±sΔ±: {n}",
        "scores": "Puanlar: {scores}",
        "winner": "Mevcut kazanan ifade: {winner}",
        "winning_text": "Kazanan ifade metni:",
        "missing_winner": "Bu kayΔ±tlΔ± turda kazanan ifade metni eksik.",
        "refined_title": "GeliΕtirilmiΕ kolektif ifade",
        "generate_and_rank": "Γ–nce ifadeleri ΓΌretin ve sΔ±ralayΔ±n.",
        "refined_button": "GeliΕtirilmiΕ ifade ΓΌret",
        "refined_saved": "GeliΕtirilmiΕ ifade ΓΌretildi.",
        "no_refined": "Bu tur iΓ§in henΓΌz geliΕtirilmiΕ ifade ΓΌretilmedi.",
        "show_responses": "Toplanan yanΔ±tlarΔ± gΓ¶ster",
        "show_rounds": "Δ°fade turlarΔ±nΔ± gΓ¶ster",
        "show_rankings": "SΔ±ralamalarΔ± gΓ¶ster",
    },
}

TOPICS.update({
    "procedural_impasse": {
        "label": {
            "en": "Breaking the procedural impasse and agreeing a way to restart negotiations",
            "el": "Υπέρβαση του διαδικαστικού αδιεξόδου και συμφωνία για τον τρόπο επανέναρξης των διαπραγματεύσεων",
            "tr": "Usule ilişkin çıkmazın aşılması ve müzakerelerin yeniden başlaması için bir yol üzerinde anlaşılması",
        },
        "short": {"en": "Procedural impasse", "el": "Διαδικαστικό αδιέξοδο", "tr": "Usule ilişkin çıkmaz"},
    },
    "security_guarantees": {
        "label": {
            "en": "How to best resolve the issue of Security and Guarantees",
            "el": "Πώς μπορεί να επιλυθεί καλύτερα το ζήτημα της Ασφάλειας και των Εγγυήσεων",
            "tr": "Güvenlik ve Garantiler konusunun en iyi nasıl çözülebileceği",
        },
        "short": {"en": "Security and Guarantees", "el": "Ασφάλεια και Εγγυήσεις", "tr": "Güvenlik ve Garantiler"},
    },
    "territory": {
        "label": {"en": "Territory", "el": "Εδαφικό", "tr": "Toprak"},
        "short": {"en": "Territory", "el": "Εδαφικό", "tr": "Toprak"},
    },
    "properties": {
        "label": {"en": "Properties", "el": "Περιουσίες", "tr": "Mülkiyet"},
        "short": {"en": "Properties", "el": "Περιουσίες", "tr": "Mülkiyet"},
    },
    "governance_power_sharing": {
        "label": {"en": "Governance and Power Sharing", "el": "Διακυβέρνηση και Κατανομή Εξουσίας", "tr": "Yönetim ve Güç Paylaşımı"},
        "short": {"en": "Governance and Power Sharing", "el": "Διακυβέρνηση και Κατανομή Εξουσίας", "tr": "Yönetim ve Güç Paylaşımı"},
    },
})

CANDIDATE_TITLES.update({
    "A": {"en": "Majority-centered", "el": "Εστιασμένη στην πλειοψηφία", "tr": "Çoğunluk odaklı"},
    "B": {"en": "Conditional consensus", "el": "Υπό όρους συναίνεση", "tr": "Koşullu uzlaşı"},
    "C": {"en": "Fairness-focused", "el": "Εστιασμένη στη δικαιοσύνη", "tr": "Adalet odaklı"},
    "D": {"en": "Minority-sensitive", "el": "Ευαίσθητη στις μειοψηφικές ανησυχίες", "tr": "Azınlık kaygılarına duyarlı"},
})

LANGUAGE_OPTIONS.update({"en": "English", "el": "Ελληνικά", "tr": "Türkçe"})
LANGUAGE_NAMES.update({"en": "English", "el": "Greek", "tr": "Turkish"})

T["el"] = {
    "title": "Πλατφόρμα Διαβούλευσης για το Κυπριακό",
    "intro": "Η πλατφόρμα σας προσκαλεί να συμμετάσχετε ανώνυμα σε μια διαδικασία διαβούλευσης για βασικές διαστάσεις του Κυπριακού. Πρώτα δηλώνετε την κοινότητά σας και επιλέγετε το θέμα που θέλετε να συζητήσετε. Στη συνέχεια δηλώνετε πόσο σημαντικές είναι διάφορες διαστάσεις ενός μελλοντικού πακέτου λύσης για τη δική σας κρίση και γράφετε με δικά σας λόγια τι είδους διευθέτηση θα υποστηρίζατε και γιατί.\n\nΗ Μηχανή Habermas χρησιμοποιεί έπειτα τις απαντήσεις των συμμετεχόντων στο ίδιο θέμα για να δημιουργήσει εναλλακτικές συλλογικές δηλώσεις. Οι συμμετέχοντες μπορούν να τις κατατάξουν και να προσθέσουν σχόλια. Ο στόχος δεν είναι να επιβληθεί συμφωνία, αλλά να γίνουν πιο ορατές οι κοινές ανησυχίες, οι διαφωνίες και πιθανές γεφυρωτικές προτάσεις με δομημένο και διαφανή τρόπο.",
    "language": "Γλώσσα",
    "topic": "Θέμα",
    "topic_help": "Οι απαντήσεις και οι παραγόμενες δηλώσεις αναλύονται μόνο μέσα στο επιλεγμένο θέμα.",
    "submit_response": "Υποβολή απάντησης",
    "community": "Παρακαλώ ορίστε την κοινότητά σας",
    "gc": "Ελληνοκύπριος/α",
    "tc": "Τουρκοκύπριος/α",
    "other": "Άλλο",
    "selected_topic": "Επιλεγμένο θέμα: {topic}",
    "restart_question": "Παρακαλώ δηλώστε πόσο σημαντικό είναι για εσάς να καθοριστεί με ακρίβεια πώς θα επανεκκινήσουν οι διαπραγματεύσεις και κατά πόσο θα πρέπει να υπάρχουν συνέπειες για την πλευρά που ο ΟΗΕ θα κρίνει υπεύθυνη σε περίπτωση κατάρρευσης",
    "dimension_question": "Παρακαλώ δηλώστε ποια διάσταση του Κυπριακού έχει μεγαλύτερη βαρύτητα στον τρόπο με τον οποίο θα κρίνετε αν θα αποδεχθείτε ή θα απορρίψετε ένα συμφωνημένο πακέτο ειρήνης σε δημοψήφισμα",
    "governance": "Διακυβέρνηση",
    "security": "Ασφάλεια",
    "territory": "Εδαφικό",
    "property": "Περιουσίες",
    "not_important": "0 = Καθόλου σημαντικό",
    "very_important": "100 = Πολύ σημαντικό",
    "arrangement_question": "Τι είδους διευθέτηση θα υποστηρίζατε, σε σχέση με το θέμα {topic}, και γιατί;",
    "consent": "Συναινώ στην ανώνυμη χρήση της απάντησής μου",
    "submit_button": "Υποβολή απάντησης",
    "must_consent": "Πρέπει να δώσετε συγκατάθεση για να υποβάλετε.",
    "enter_response": "Παρακαλώ γράψτε μια απάντηση.",
    "submitted": "Η απάντηση υποβλήθηκε με επιτυχία!",
    "generate_title": "Δημιουργία υποψήφιων δηλώσεων",
    "scope": "Πεδίο δήλωσης",
    "all": "Όλοι",
    "max_responses": "Μέγιστος αριθμός απαντήσεων που θα χρησιμοποιηθούν",
    "candidate_caption": "Οι υποψήφιες δηλώσεις θα χρησιμοποιήσουν μόνο απαντήσεις για: {topic}",
    "generate_button": "Δημιουργία συλλογικών δηλώσεων",
    "incomplete_set": "Το Gemini επέστρεψε ελλιπές σύνολο δηλώσεων. Πατήστε ξανά Δημιουργία συλλογικών δηλώσεων. Ελλιπείς ή πολύ σύντομες: {labels}.",
    "not_saved": "Το ελλιπές αποτέλεσμα δεν αποθηκεύτηκε.",
    "raw_output": "Ακατέργαστο ελλιπές αποτέλεσμα",
    "statements_saved": "Οι δηλώσεις δημιουργήθηκαν και αποθηκεύτηκαν.",
    "candidate_title": "Υποψήφιες Δηλώσεις",
    "round_caption": "ID γύρου: {round_id} | Θέμα: {topic} | Πεδίο: {scope}",
    "incomplete_saved": "Αυτός ο αποθηκευμένος γύρος δηλώσεων είναι ελλιπής και δεν πρέπει να καταταχθεί. Δημιουργήστε νέο γύρο. Ελλιπείς ή πολύ σύντομες: {labels}.",
    "key_tensions": "Βασικές εντάσεις:",
    "no_round": "Δεν έχει δημιουργηθεί ακόμη γύρος δηλώσεων.",
    "rank_title": "Κατάταξη υποψήφιων δηλώσεων",
    "generate_first": "Δημιουργήστε πρώτα δηλώσεις και μετά θα εμφανιστεί η κατάταξη.",
    "generate_complete": "Δημιουργήστε έναν πλήρη γύρο δηλώσεων πριν από την κατάταξη.",
    "rank_instruction": "Κατατάξτε τις A-D από 1 (καλύτερη) έως 4 (χειρότερη). Κάθε αριθμός πρέπει να χρησιμοποιηθεί μία φορά.",
    "rank_for": "Κατάταξη για {label}",
    "acceptable": "Ποιες δηλώσεις θα θεωρούσατε αρκετά αποδεκτές ώστε να τις υποστηρίξετε;",
    "critique": "Σύντομη κριτική ή σχόλιο",
    "submit_ranking": "Υποβολή κατάταξης",
    "rank_error": "Παρακαλώ χρησιμοποιήστε κάθε κατάταξη από 1 έως 4 ακριβώς μία φορά.",
    "ranking_submitted": "Η κατάταξη υποβλήθηκε.",
    "current_result": "Τρέχον συγκεντρωτικό αποτέλεσμα",
    "no_rankings": "Δεν έχουν υποβληθεί ακόμη κατατάξεις για αυτόν τον γύρο.",
    "number_rankings": "Αριθμός κατατάξεων: {n}",
    "scores": "Βαθμολογίες: {scores}",
    "winner": "Τρέχουσα νικήτρια δήλωση: {winner}",
    "winning_text": "Κείμενο νικήτριας δήλωσης:",
    "missing_winner": "Το κείμενο της νικήτριας δήλωσης λείπει από αυτόν τον αποθηκευμένο γύρο.",
    "refined_title": "Επεξεργασμένη συλλογική δήλωση",
    "generate_and_rank": "Δημιουργήστε και κατατάξτε πρώτα δηλώσεις.",
    "refined_button": "Δημιουργία επεξεργασμένης δήλωσης",
    "refined_saved": "Η επεξεργασμένη δήλωση δημιουργήθηκε.",
    "no_refined": "Δεν έχει δημιουργηθεί ακόμη επεξεργασμένη δήλωση για αυτόν τον γύρο.",
    "show_responses": "Εμφάνιση συλλεγμένων απαντήσεων",
    "show_rounds": "Εμφάνιση γύρων δηλώσεων",
    "show_rankings": "Εμφάνιση κατατάξεων",
}

T["tr"] = {
    "title": "Kıbrıs Müzakere Platformu",
    "intro": "Bu platform sizi Kıbrıs meselesinin temel boyutları üzerine anonim bir müzakere sürecine katılmaya davet eder. Önce topluluğunuzu tanımlar ve tartışmak istediğiniz konuyu seçersiniz. Sonra gelecekteki bir barış paketini kabul veya reddetme kararınız için bazı boyutların ne kadar önemli olduğunu belirtir ve ne tür bir düzenlemeyi desteklediğinizi kendi sözlerinizle açıklarsınız.\n\nHabermas Makinesi daha sonra aynı konu içindeki katılımcı yanıtlarını kullanarak alternatif kolektif ifadeler üretir. Katılımcılar bu ifadeleri sıralayabilir ve yorum ekleyebilir. Amaç uzlaşmayı zorlamak değil, ortak kaygıları, anlaşmazlıkları ve olası köprü kurucu önerileri yapılandırılmış ve şeffaf biçimde daha görünür kılmaktır.",
    "language": "Dil",
    "topic": "Konu",
    "topic_help": "Yanıtlar ve üretilen ifadeler yalnızca seçilen konu içinde analiz edilir.",
    "submit_response": "Yanıt gönder",
    "community": "Lütfen topluluğunuzu tanımlayın",
    "gc": "Kıbrıslı Rum",
    "tc": "Kıbrıslı Türk",
    "other": "Diğer",
    "selected_topic": "Seçilen konu: {topic}",
    "restart_question": "Müzakerelerin tam olarak nasıl yeniden başlayacağının ve çöküş halinde BM'nin sorumlu gördüğü taraf için herhangi bir sonuç olup olmayacağının belirlenmesi sizin için ne kadar önemlidir?",
    "dimension_question": "Referandumda kabul edilmiş bir barış paketini kabul veya reddetme kararınızda Kıbrıs meselesinin hangi boyutunun daha fazla ağırlığa sahip olduğunu belirtiniz",
    "governance": "Yönetim",
    "security": "Güvenlik",
    "territory": "Toprak",
    "property": "Mülkiyet",
    "not_important": "0 = Hiç önemli değil",
    "very_important": "100 = Çok önemli",
    "arrangement_question": "{topic} konusu bakımından ne tür bir düzenlemeyi desteklersiniz ve neden?",
    "consent": "Yanıtımın anonim olarak kullanılmasına onay veriyorum",
    "submit_button": "Yanıtı gönder",
    "must_consent": "Göndermek için onay vermelisiniz.",
    "enter_response": "Lütfen bir yanıt girin.",
    "submitted": "Yanıt başarıyla gönderildi!",
    "generate_title": "Aday ifadeler üret",
    "scope": "İfade kapsamı",
    "all": "Tümü",
    "max_responses": "Kullanılacak en fazla yanıt sayısı",
    "candidate_caption": "Aday ifadeler yalnızca şu konuya ilişkin yanıtları kullanacaktır: {topic}",
    "generate_button": "Kolektif ifadeler üret",
    "incomplete_set": "Gemini eksik bir aday ifade seti döndürdü. Lütfen Kolektif ifadeler üret düğmesine tekrar basın. Eksik veya çok kısa: {labels}.",
    "not_saved": "Eksik çıktı kaydedilmedi.",
    "raw_output": "Ham eksik çıktı",
    "statements_saved": "İfadeler üretildi ve kaydedildi.",
    "candidate_title": "Aday İfadeler",
    "round_caption": "Tur ID: {round_id} | Konu: {topic} | Kapsam: {scope}",
    "incomplete_saved": "Bu kayıtlı ifade turu eksik ve sıralanmamalıdır. Yeni bir kolektif ifade turu üretin. Eksik veya çok kısa: {labels}.",
    "key_tensions": "Temel gerilimler:",
    "no_round": "Henüz bir ifade turu üretilmedi.",
    "rank_title": "Aday ifadeleri sıralayın",
    "generate_first": "Önce ifadeleri üretin; ardından sıralama burada görünecektir.",
    "generate_complete": "Sıralamadan önce eksiksiz bir ifade turu üretin.",
    "rank_instruction": "A-D ifadelerini 1'den (en iyi) 4'e (en kötü) sıralayın. Her sayı bir kez kullanılmalıdır.",
    "rank_for": "{label} için sıra",
    "acceptable": "Hangi ifadeleri desteklemek için yeterince kabul edilebilir bulursunuz?",
    "critique": "Kısa eleştiri veya yorum",
    "submit_ranking": "Sıralamayı gönder",
    "rank_error": "Lütfen 1'den 4'e kadar her sırayı tam olarak bir kez kullanın.",
    "ranking_submitted": "Sıralama gönderildi.",
    "current_result": "Mevcut toplu sonuç",
    "no_rankings": "Bu tur için henüz sıralama gönderilmedi.",
    "number_rankings": "Sıralama sayısı: {n}",
    "scores": "Puanlar: {scores}",
    "winner": "Mevcut kazanan ifade: {winner}",
    "winning_text": "Kazanan ifade metni:",
    "missing_winner": "Bu kayıtlı turda kazanan ifade metni eksik.",
    "refined_title": "Geliştirilmiş kolektif ifade",
    "generate_and_rank": "Önce ifadeleri üretin ve sıralayın.",
    "refined_button": "Geliştirilmiş ifade üret",
    "refined_saved": "Geliştirilmiş ifade üretildi.",
    "no_refined": "Bu tur için henüz geliştirilmiş ifade üretilmedi.",
    "show_responses": "Toplanan yanıtları göster",
    "show_rounds": "İfade turlarını göster",
    "show_rankings": "Sıralamaları göster",
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


def tr(key: str, lang: str = "en", **kwargs) -> str:
    text = T.get(lang, T["en"]).get(key, T["en"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def localized_value(value, lang: str = "en") -> str:
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or next(iter(value.values()))
    return str(value)


def topic_label(topic_id: str, lang: str = "en") -> str:
    return localized_value(TOPICS.get(topic_id, TOPICS["security_guarantees"])["label"], lang)


def topic_short_label(topic_id: str, lang: str = "en") -> str:
    return localized_value(TOPICS.get(topic_id, TOPICS["security_guarantees"])["short"], lang)


def candidate_title(label: str, lang: str = "en") -> str:
    return localized_value(CANDIDATE_TITLES.get(label, label), lang)


def community_label(option_key: str, lang: str = "en") -> str:
    return tr(option_key, lang)


def scope_label(scope_code: str, lang: str = "en") -> str:
    if scope_code == "All":
        return tr("all", lang)
    if scope_code == "GC":
        return tr("gc", lang)
    if scope_code == "TC":
        return tr("tc", lang)
    return tr("other", lang)


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


def anchored_slider(label: str, key: str, lang: str = "en", value: int = 50) -> int:
    slider_value = st.slider(label, 0, 100, value, key=key)
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; width:100%; color:#808495; font-size:0.9rem; margin-top:-0.5rem;">
            <span>{tr("not_important", lang)}</span>
            <span>{tr("very_important", lang)}</span>
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
    for lang_code in LANGUAGE_OPTIONS:
        title = candidate_title(label, lang_code)
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


def generate_candidate_statements(
    df_scope: pd.DataFrame,
    scope_label: str,
    issue_label: str,
    language_code: str,
    max_responses: int = 20,
):
    texts = clean_text_series(df_scope["text"])
    texts = texts[texts != ""].tolist()[:max_responses]

    if len(texts) < 3:
        return None, "Not enough valid responses yet. At least 3 are needed."

    opinions = "\n".join([f'Response {i+1}: "{txt}"' for i, txt in enumerate(texts)])

    prompt = f"""
You are the Collective Statement Generator for a Cyprus deliberation platform.

Issue: {issue_label}
Scope: {scope_label}
Output language: {LANGUAGE_NAMES.get(language_code, "English")}

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
- Write all candidate statements and key tensions in {LANGUAGE_NAMES.get(language_code, "English")}.
- If participant responses are in another language, translate their meaning and produce the output in {LANGUAGE_NAMES.get(language_code, "English")}.
- Use this exact format:
A: [complete majority-centered statement]
B: [complete conditional consensus statement]
C: [complete fairness-focused statement]
D: [complete minority-sensitive statement]

After the 4 statements, add this exact heading in English, followed by bullets in {LANGUAGE_NAMES.get(language_code, "English")}:
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


def generate_refined_statement(latest_round, rankings_df, language_code: str):
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
- Write the refined statement in {LANGUAGE_NAMES.get(language_code, "English")}.
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
lang = st.selectbox(
    "Language / Ξ“Ξ»ΟΟƒΟƒΞ± / Dil",
    list(LANGUAGE_OPTIONS.keys()),
    format_func=lambda code: LANGUAGE_OPTIONS[code],
)
st.title(tr("title", lang))
st.write(tr("intro", lang))

selected_topic_id = st.selectbox(
    tr("topic", lang),
    TOPIC_IDS,
    format_func=lambda topic_id: topic_label(topic_id, lang),
    help=tr("topic_help", lang),
)
selected_topic_label = topic_label(selected_topic_id, lang)
selected_topic_label_en = topic_label(selected_topic_id, "en")

# =========================================================
# RESPONSE FORM
# =========================================================
st.subheader(tr("submit_response", lang))

community_key = st.selectbox(
    tr("community", lang),
    list(COMMUNITY_OPTIONS.keys()),
    format_func=lambda key: community_label(key, lang),
)
community = COMMUNITY_OPTIONS[community_key]
st.caption(tr("selected_topic", lang, topic=selected_topic_label))

negotiation_restart = anchored_slider(
    tr("restart_question", lang),
    key="negotiation_restart",
    lang=lang,
)

st.markdown(
    f"**{tr('dimension_question', lang)}**"
)

governance = anchored_slider(tr("governance", lang), key="governance_weight", lang=lang)
security = anchored_slider(tr("security", lang), key="security_weight", lang=lang)
territory = anchored_slider(tr("territory", lang), key="territory_weight", lang=lang)
property_q = anchored_slider(tr("property", lang), key="property_weight", lang=lang)

text = st.text_area(tr("arrangement_question", lang, topic=selected_topic_label))
consent = st.checkbox(tr("consent", lang))

if st.button(tr("submit_button", lang)):
    if not consent:
        st.warning(tr("must_consent", lang))
    elif not text.strip():
        st.warning(tr("enter_response", lang))
    else:
        new_row = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "community": community,
            "topic_id": selected_topic_id,
            "issue": selected_topic_label_en,
            "negotiation_restart": negotiation_restart,
            "governance": governance,
            "security": security,
            "territory": territory,
            "property": property_q,
            "text": text.strip(),
            "is_seed": False,
        }

        responses_df = insert_record(RESPONSES_TABLE, RESPONSES_FILE, responses_df, new_row, responses_cols)
        st.success(tr("submitted", lang))
        responses_df = normalize_response_topics(responses_df)

# =========================================================
# GENERATE CANDIDATE STATEMENTS
# =========================================================
st.subheader(tr("generate_title", lang))

scope = st.selectbox(
    tr("scope", lang),
    ["All", "GC", "TC", "Other"],
    key="scope_select",
    format_func=lambda scope_code: scope_label(scope_code, lang),
)
max_responses = st.slider(tr("max_responses", lang), 3, 30, 12)
st.caption(tr("candidate_caption", lang, topic=selected_topic_label))

if st.button(tr("generate_button", lang)):
    working_df = responses_df[responses_df["topic_id"] == selected_topic_id].copy()

    if scope != "All":
        working_df = working_df[working_df["community"] == scope]

    working_df = working_df[working_df["text"].notna()].copy()
    if not working_df.empty:
        working_df["text"] = clean_text_series(working_df["text"])
        working_df = working_df[working_df["text"] != ""]

    generated_text, error = generate_candidate_statements(
        working_df,
        scope_label(scope, lang),
        selected_topic_label,
        lang,
        max_responses=max_responses,
    )

    if error:
        st.error(error)
    else:
        parsed = parse_candidate_statements(generated_text)
        missing_statements = validate_candidate_statements(parsed)
        if missing_statements:
            st.error(tr("incomplete_set", lang, labels=", ".join(missing_statements)))
            st.caption(tr("not_saved", lang))
            st.text_area(tr("raw_output", lang), generated_text, height=220)
            st.stop()

        round_id = str(uuid.uuid4())

        new_round = {
            "round_id": round_id,
            "timestamp": datetime.now().isoformat(),
            "scope": scope,
            "topic_id": selected_topic_id,
            "issue": selected_topic_label_en,
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
        st.success(tr("statements_saved", lang))
        rounds_df = normalize_round_topics(rounds_df)

# =========================================================
# DISPLAY LATEST ROUND
# =========================================================
st.subheader(tr("candidate_title", lang))

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
        tr(
            "round_caption",
            lang,
            round_id=latest_round["round_id"],
            topic=topic_short_label(selected_topic_id, lang),
            scope=scope_label(safe_text(latest_round["scope"]), lang),
        )
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
        st.warning(tr("incomplete_saved", lang, labels=", ".join(incomplete_existing)))

    for label in ["A", "B", "C", "D"]:
        value = statement_map[label]
        if value:
            st.markdown(f"**{label}: {candidate_title(label, lang)}**  \n{value}")

    key_tensions = safe_text(latest_round.get("key_tensions", ""))
    if key_tensions:
        st.markdown("---")
        st.markdown(f"**{tr('key_tensions', lang)}**")
        st.write(key_tensions)
else:
    st.info(tr("no_round", lang))

# =========================================================
# RANKING FORM
# =========================================================
st.subheader(tr("rank_title", lang))

if latest_round is None:
    st.info(tr("generate_first", lang))
elif not latest_round_complete:
    st.info(tr("generate_complete", lang))
else:
    ranking_community_key = st.selectbox(
        tr("community", lang),
        list(COMMUNITY_OPTIONS.keys()),
        key="ranking_community",
        format_func=lambda key: community_label(key, lang),
    )
    participant_community = COMMUNITY_OPTIONS[ranking_community_key]

    st.write(tr("rank_instruction", lang))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rank_a = st.selectbox(tr("rank_for", lang, label="A"), [1, 2, 3, 4], key="rank_a")
    with col2:
        rank_b = st.selectbox(tr("rank_for", lang, label="B"), [1, 2, 3, 4], key="rank_b")
    with col3:
        rank_c = st.selectbox(tr("rank_for", lang, label="C"), [1, 2, 3, 4], key="rank_c")
    with col4:
        rank_d = st.selectbox(tr("rank_for", lang, label="D"), [1, 2, 3, 4], key="rank_d")

    acceptable = st.multiselect(
        tr("acceptable", lang),
        ["A", "B", "C", "D"],
        key="acceptable_statements"
    )

    critique = st.text_area(tr("critique", lang), key="critique_text")

    if st.button(tr("submit_ranking", lang)):
        ranks = [rank_a, rank_b, rank_c, rank_d]
        if sorted(ranks) != [1, 2, 3, 4]:
            st.error(tr("rank_error", lang))
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
            st.success(tr("ranking_submitted", lang))

# =========================================================
# CURRENT WINNER
# =========================================================
st.subheader(tr("current_result", lang))

if latest_round is not None:
    result = borda_count(rankings_df, latest_round["round_id"])
    if result is None:
        st.info(tr("no_rankings", lang))
    else:
        st.write(tr("number_rankings", lang, n=result["n_rankings"]))
        st.write(tr("scores", lang, scores=result["scores"]))
        st.success(tr("winner", lang, winner=result["winner"]))

        winner_map = {
            "A": safe_text(latest_round.get("statement_a", "")),
            "B": safe_text(latest_round.get("statement_b", "")),
            "C": safe_text(latest_round.get("statement_c", "")),
            "D": safe_text(latest_round.get("statement_d", "")),
        }

        winning_text = winner_map.get(result["winner"], "")
        st.markdown(f"**{tr('winning_text', lang)}**")
        if winning_text:
            st.write(winning_text)
        else:
            st.warning(tr("missing_winner", lang))

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
st.subheader(tr("refined_title", lang))

if latest_round is None:
    st.info(tr("generate_and_rank", lang))
else:
    current_round_id = latest_round["round_id"]

    if st.button(tr("refined_button", lang)):
        refined_text, error = generate_refined_statement(latest_round, rankings_df, lang)

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

            st.success(tr("refined_saved", lang))

    current_refined = safe_text(latest_round.get("refined_statement", ""))
    if current_refined:
        st.write(current_refined)
    else:
        st.info(tr("no_refined", lang))

# =========================================================
# OPTIONAL DATA DISPLAY
# =========================================================
if st.checkbox(tr("show_responses", lang)):
    st.dataframe(responses_df[responses_df["topic_id"] == selected_topic_id].tail(20))

if st.checkbox(tr("show_rounds", lang)):
    st.dataframe(rounds_df[rounds_df["topic_id"] == selected_topic_id].tail(10))

if st.checkbox(tr("show_rankings", lang)):
    st.dataframe(rankings_df.tail(20))
