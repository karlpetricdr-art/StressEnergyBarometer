import streamlit as st
import pandas as pd
import re
import math
import json
import time
import html
import base64
from io import BytesIO
from collections import Counter, defaultdict
from typing import List, Literal

import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import streamlit.components.v1 as components

from pyvis.network import Network

from pydantic import BaseModel
from google import genai
from google.genai import types


# ============================================================
# 1. PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Stress degree and kcal analysis PRO",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================
# 2. CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        background-color: #f7f9fc;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1 {
        font-weight: 800;
        letter-spacing: -0.5px;
    }

    h2, h3 {
        font-weight: 700;
    }

    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #e5e9f0;
        box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        min-height: 145px;
    }

    .small-muted {
        color: #64748b;
        font-size: 0.82rem;
    }

    .stress-high {
        color: #dc2626;
        font-weight: 800;
    }

    .stress-medium {
        color: #ea580c;
        font-weight: 700;
    }

    .stress-low {
        color: #16a34a;
        font-weight: 700;
    }

    .network-help {
        background: #f8fafc;
        border: 1px solid #dbe3ec;
        border-radius: 10px;
        padding: 12px 15px;
        margin: 10px 0 15px 0;
        color: #475569;
        font-size: 0.9rem;
    }

    .st-key-action_btn_container button {
        background: linear-gradient(145deg, #16a34a, #15803d) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow:
            3px 3px 8px rgba(21, 128, 61, 0.35),
            -2px -2px 6px rgba(255, 255, 255, 0.25) !important;
    }

    .st-key-action_btn_container button:hover {
        background: linear-gradient(145deg, #15803d, #166534) !important;
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] {
        background-color: #030c1b !important;
        background-image: none !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        background-color: #030c1b !important;
    }

    [data-testid="stSidebar"]::before,
    [data-testid="stSidebar"]::after {
        content: "";
        position: absolute;
        border-radius: 999px;
        pointer-events: none;
        opacity: 0.78;
    }

    [data-testid="stSidebar"]::before {
        width: 150px;
        height: 150px;
        top: 115px;
        right: -78px;
        border: 1px solid rgba(255,255,255,0.18);
        box-shadow:
            0 0 0 20px rgba(255,255,255,0.035),
            0 0 0 42px rgba(255,255,255,0.025);
    }

    [data-testid="stSidebar"]::after {
        width: 95px;
        height: 95px;
        bottom: 64px;
        left: -48px;
        background: rgba(74, 222, 128, 0.12);
        box-shadow: 0 0 40px rgba(74, 222, 128, 0.20);
    }

    .control-panel-title {
        margin: 0 0 0.25rem 0;
        color: #0f172a;
    }

    .control-panel-subtitle {
        margin: 0 0 1rem 0;
        color: #64748b;
        font-size: 0.92rem;
    }

    .section-label {
        display: inline-block;
        margin-bottom: 0.5rem;
        color: #0f172a;
        font-weight: 800;
        font-size: 1rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 2b. ULTRA-IMPACT BRANDING & ENERGY DRAIN ANALYTICS
# ============================================================

# Definiramo prazen Base64, da ne bo NameError napake
LOGO_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

SIDEBAR_LOGO_HTML = (
    "<html><head><style>"
    "html,body{margin:0;padding:0;background:#000000;font-family:'Arial Black',Gadget,sans-serif;color:white;}"
    ".sidebar-container{padding:20px 15px;display:flex;flex-direction:column;align-items:center;background:#000000;}"
    ".brand-circle{width:100px;height:100px;background:white;border-radius:50%;"
    "display:flex;justify-content:center;align-items:center;margin-bottom:30px;"
    "box-shadow:0 0 30px rgba(59,130,246,0.5);border:4px solid #3b82f6;}"
    ".pyramid-svg{width:0;height:0;border-left:30px solid transparent;border-right:30px solid transparent;"
    "border-bottom:50px solid #030c1b;}"
    ".impact-card{width:100%;background:rgba(255,255,255,0.03);border-radius:20px;padding:25px 20px;"
    "border:1px solid rgba(255,255,255,0.1);box-shadow:0 20px 50px rgba(0,0,0,0.5);box-sizing:border-box;}"
    ".status-tag{font-size:0.7rem;font-weight:900;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;display:block;}"
    ".red-text{color:#ff4b4b;} .blue-text{color:#00d2ff;}"
    ".mega-bar{height:22px;background:#111;border-radius:30px;margin-bottom:30px;padding:3px;border:1px solid #333;overflow:hidden;}"
    ".fill-stress{height:100%;width:92%;background:linear-gradient(90deg,#ff4b4b,#880000);border-radius:30px;"
    "box-shadow:0 0 20px rgba(255,75,75,0.6);animation: pulse 1.5s infinite;}"
    ".fill-energy{height:100%;width:12%;background:linear-gradient(90deg,#00d2ff,#004488);border-radius:30px;"
    "box-shadow:0 0 10px rgba(0,210,255,0.4);}.center-math{font-size:1.8rem;font-weight:900;text-align:center;margin:20px 0;letter-spacing:-1px;}"
    ".drain-arrow{color:#ff4b4b;font-size:1.5rem;display:block;margin:-5px 0;}"
    ".warning-box{background:#ff4b4b;color:white;padding:15px;border-radius:12px;text-align:center;"
    "font-size:0.85rem;font-weight:900;box-shadow:0 10px 20px rgba(255,75,75,0.3);}.warning-box span{display:block;font-size:0.6rem;text-transform:uppercase;margin-top:5px;opacity:0.8;}"
    ".link-group{width:100%;margin-top:22px;}.group-title{color:#00d2ff;font-size:0.68rem;font-weight:900;letter-spacing:2px;text-transform:uppercase;margin:0 0 9px 4px;}"
    ".side-link{display:block;color:#ffffff !important;text-decoration:none !important;font-family:Arial,sans-serif;font-size:0.78rem;font-weight:700;"
    "padding:8px 10px;margin:4px 0;border:1px solid rgba(255,255,255,0.14);border-radius:8px;background:rgba(255,255,255,0.045);transition:all .2s;}"
    ".side-link:hover{background:rgba(0,210,255,0.12);border-color:#00d2ff;color:#ffffff !important;}"
    ".side-footer{margin-top:20px;font-size:0.55rem;opacity:0.4;letter-spacing:1px;text-align:center;}"
    "@keyframes pulse { 0% { opacity:1; } 50% { opacity:0.6; } 100% { opacity:1; } }"
    "</style></head><body>"
    "<div class='sidebar-container'>"
    "<div class='brand-circle'><div class='pyramid-svg'></div></div>"
    "<div class='impact-card'>"
    "<span class='status-tag red-text'>Stress Intensity (&sigma;)</span>"
    "<div class='mega-bar'><div class='fill-stress'></div></div>"
    "<div class='center-math'>&sigma; &uarr; <span class='drain-arrow'>&DoubleDownArrow;</span> W<sub>EU</sub> &darr;</div>"
    "<span class='status-tag blue-text'>Useful Energy (W_EU)</span>"
    "<div class='mega-bar'><div class='fill-energy'></div></div>"
    "<div class='warning-box'>KCAL DRAIN: CRITICAL<span>Internal friction exceeds output</span></div>"
    "</div>"
    "<div class='link-group'>"
    "<div class='group-title'>Academic identity</div>"
    "<a class='side-link' href='https://sites.google.com/view/drkarlpetric/domov' target='_blank'>Dr. Karl Petrič — Home</a>"
    "<a class='side-link' href='https://orcid.org/0000-0003-0715-710X' target='_blank'>ORCID iD</a>"
    "<a class='side-link' href='https://bib.cobiss.net/bibliographies/si/webBiblio/bib201_20260816_114808_a878947.html' target='_blank'>Personal bibliography</a>"
    "</div>"
    "<div class='link-group'>"
    "<div class='group-title'>Research & publications</div>"
    "<a class='side-link' href='https://zenodo.org/records/21885685' target='_blank'>Hierarchology/Hierarchography 5th ed.</a>"
    "<a class='side-link' href='https://www.researchgate.net/scientific-contributions/Karl-Petric-2338161528' target='_blank'>ResearchGate</a>"
    "<a class='side-link' href='https://works.hcommons.org/search?q=Karl%20Petri%C4%8D&l=list&p=1&s=10&sort=bestmatch' target='_blank'>Knowledge Commons</a>"
    "</div>"
    "<div class='link-group'>"
    "<div class='group-title'>Applications & media</div>"
    "<a class='side-link' href='https://sisapplicationtriadknowledgeideaspy-vd4xsrhfkfcehnyjyfq7f3.streamlit.app/' target='_blank'>SIS Universal Knowledge Synthesizer</a>"
    "<a class='side-link' href='https://stressenergybarometer-2qlqgyp8y9jj3b8zcz7fba.streamlit.app/' target='_blank'>Stress Barometer</a>"
    "<a class='side-link' href='https://x.com/' target='_blank'>X — videos & updates</a>"
    "</div>"
    "<div class='side-footer'>PETRIČ ANALYTICS ENGINE PRO</div>"
    "</div></body></html>"
)

# ============================================================
# 3. STOPWORDS
# ============================================================

SLO_STOPWORDS = {
    "se", "si", "oh", "na", "potem", "in", "ter", "bi", "da", "pa",
    "že", "tudi", "iz", "za", "še", "samo", "le", "tako", "kot",
    "sem", "smo", "ste", "so", "je", "bil", "biti", "ali", "v",
    "pri", "o", "z", "s", "k", "h", "vse", "vsi", "vsega", "vsemu",
    "vsem", "tisti", "tista", "tisto", "tistih", "tistem", "tistimi",
    "nekaj", "včasih", "npr", "itd", "itn", "ker", "ko", "kadar",
    "kam", "kjer", "kaj", "kdo", "kdaj", "zakaj", "kako", "vendar",
    "ampak", "toda", "torej", "zato", "saj", "namreč", "zlasti",
    "predvsem", "sploh", "šele", "kar", "naj", "gre", "marsikaj",
    "marsikdo", "nekdo", "nekateri", "nekatera", "nekatero", "pod",
    "med", "nad", "pred", "brez", "ob", "po", "skozi", "čez",
    "proti", "kljub", "zaradi", "namesto", "razen", "okoli", "okrog",
    "tem",

    "the", "and", "to", "of", "a", "is", "it", "with", "some",
    "more", "being", "able", "use", "make", "nice", "your", "this",
    "that", "from", "for", "are", "was", "were"
}


# ============================================================
# 4. SCIENTIFIC CLASSIFICATION
# ============================================================

CATEGORY_SHORT = {
    "Attentive (physical) unit": "Attentive",
    "Performance unit": "Performance",
    "Individual Psychological unit": "Psychological",
    "Social unit": "Social",
    "Health biological unit": "Health"
}


SHORT_TO_FULL = {
    v: k for k, v in CATEGORY_SHORT.items()
}


CATEGORY_DEFINITIONS = {

    "Attentive (physical) unit": (
        "Physical/sensory environment: noise, lighting, temperature, air, "
        "ergonomics, orderliness and aesthetics of the space, smells, colors."
    ),

    "Performance unit": (
        "Factors related to performing tasks: deadlines, workload, "
        "administrative procedures, information accessibility, training, "
        "efficiency of tools/processes, physical activity as a form of relief."
    ),

    "Individual Psychological unit": (
        "Inner subjective emotional/psychological states of the individual: fear, "
        "anxiety, self-confidence, calmness, feelings, personal meaning, values, "
        "inner relaxation, self-image, mental well-being."
    ),

    "Social unit": (
        "Interpersonal and organizational/status-related factors: relationships "
        "with coworkers, superiors, family, and friends; communication, conflicts, "
        "bullying, teamwork, organizational climate, hierarchy, AS WELL AS status, "
        "fairness, recognition, pay, job security, and economic factors "
        "(this unit combines 'social' and 'partial social' from the article)."
    ),

    "Health biological unit": (
        "Physical health and biological factors: illness, fatigue, sleep, "
        "hygiene, nutrition, physiological condition, exhaustion."
    ),
}


# ============================================================
# 5. OFFLINE CLASSIFICATION DICTIONARY
# ============================================================

CATEGORIES_MAP = {

    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem",
        "prostor", "pisarn", "ergonom", "oprem", "tišin", "zrak",
        "prah", "gneč", "tehni", "poškodb", "varna", "objekt",
        "sodobn", "naprav", "urejenost", "etiket", "izolac",
        "barv", "rastlin", "vonjav", "stol", "miz", "prezrač",
        "notranj", "location", "environment", "lighting", "toplota",
        "hlad", "umazano", "onesnaž", "arhitekt", "opremljenost",
        "hrupn", "svetloba", "tišina", "classical", "music",
        "flower", "klasič", "glasb", "rož", "cvet", "flowers"
    ],

    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "čas",
        "administra", "birokra", "obrazc", "poročil",
        "postopk", "navodil", "veščin", "hitenj", "naglic",
        "stisk", "preobremen", "neizkušn", "učinkovit",
        "biro", "togi", "rutin", "nujne", "izobraž",
        "usposab", "proces", "poenostav", "inovac", "rešitev",
        "urnik", "ure", "izvajanj", "regula", "hrm", "direktiv",
        "ukaluplj", "iskanj", "gradiv", "polic", "katalog",
        "orientac", "podatkov", "fond", "isposoj", "job",
        "balance", "goal", "cilj", "študij", "literature",
        "izvodi", "raziskav", "iskanje", "tasks", "program",
        "training", "exercise", "activities", "šport", "rekreac",
        "tek", "joga", "plavanj", "kolo"
    ],

    "Individual Psychological unit": [
        "strah", "tesnob", "samozav", "čustv", "stres",
        "frustr", "mir", "negotov", "nervoz", "panik", "nemoč",
        "skrb", "napetos", "psih", "travm", "osebno",
        "samopodob", "nasil", "negativ", "dušev", "žalost",
        "ogroženost", "nelagod", "zadovolj", "psihi", "nemir",
        "choice", "life", "memory", "spomin", "art", "umetnos",
        "irrational", "uncertain", "uncertainty", "peace",
        "feeling", "hope", "values", "vrednot", "ponižanj",
        "identitet", "dopust", "izlet", "potovan", "journey",
        "sprošč", "relax", "medit", "dihan", "narav", "spomini",
        "praznina", "osebnost", "samokontrol", "vera", "mirnost"
    ],

    "Social unit": [
        "odnos", "odnosih", "odnosov", "sodelav", "sodelovanje",
        "sodelov", "šef", "vodstv", "nadrejen", "vodja", "direktor",
        "družin", "family", "prijatel", "friends", "friend",
        "komunik", "pogovor", "talk", "prepir", "konflikt",
        "conflict", "mobing", "mobbing", "šikan", "harass",
        "harassment", "bully", "bullying", "zahrbt", "vzvišen",
        "nesram", "aroganc", "egoiz", "neiskren", "rival",
        "rivalstvo", "polit", "hierarh", "timsko", "team",
        "teamwork", "druženj", "uporabnik", "osebj", "človek",
        "zaupan", "trust", "support", "podpor", "klima", "vzdušje",
        "pripadnost", "ignor", "nerazum", "posluš", "organizac",
        "organizaciji", "organizacijo", "sestank", "meeting",
        "meetings", "management", "leader", "leadership", "manager",
        "plač", "dohod", "denar", "finanč", "nagrad", "status",
        "priznan", "revšč", "standar", "nepravič", "nestimul",
        "krivic", "dostojen", "zaposlit", "služb", "karier",
        "napredov", "varnost", "staž", "benefic", "ekonom",
        "proračun", "pokojnin", "sredstv", "zamudn", "opomin",
        "kazn", "plačev", "plačilo", "money", "salary", "financial",
        "budget", "stability", "znesek", "družb", "law", "zakon",
        "orož", "weapon", "alcohol", "economic", "level", "standard",
        "overcrowding", "crowding", "injustice", "punishment",
        "reward", "recognition"
    ],

    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "spanj", "utrujen", "izčrpan",
        "higien", "čistoč", "sleep", "rest", "dihanje", "izčrpanost",
        "utrujenost", "zdravje", "bolečina", "virus", "infekcij",
        "higiena", "prehran", "diet", "biološ", "fiziolo", "telo",
        "utrujena", "spanja", "telesno", "exhaustion"
    ]
}


# ============================================================
# 6. SCIENTIFIC SLOPE WEIGHTS
# ============================================================

SLOPE_WEIGHTS = {
    "Attentive (physical) unit": 0.85,
    "Performance unit": 1.05,
    "Individual Psychological unit": 1.00,
    "Social unit": 1.30,
    "Health biological unit": 0.90
}


RATING_SCALE = [
    (15.04, "Very low"),
    (30.04, "Low"),
    (45.04, "Medium"),
    (60.04, "Higher"),
    (75.04, "High"),
    (90.01, "Very high")
]


def rate_sigma(sigma):

    for threshold, label in RATING_SCALE:

        if sigma <= threshold:
            return label

    return "Very high"


# ============================================================
# 7. GOOGLE MODELS
# ============================================================

AVAILABLE_MODELS = [
    "-- select a model --",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
]


MODEL_NOTES = {

    "gemini-3.5-flash-lite":
        "Fast Flash-Lite model for high-throughput classification.",

    "gemini-3.1-flash-lite":
        "Fast and efficient Flash-Lite model for classification.",

    "gemini-2.5-flash-lite":
        "Lightweight Flash-Lite model suitable for fast classification.",

    "gemini-3.5-flash":
        "More capable general Flash model.",

    "gemini-3.6-flash":
        "Higher-capability Flash model when available to the API key.",

    "gemma-4-26b-a4b-it":
        "Gemma model for classification.",

    "gemma-4-31b-it":
        "Gemma model for classification.",
}


# ============================================================
# 8. STRUCTURED OUTPUT
# ============================================================

def build_classification_models(allowed_short_names):

    allowed = tuple(allowed_short_names) + ("None",)

    class ClassifiedItem(BaseModel):
        phrase: str
        category: Literal[allowed]

    class RowClassification(BaseModel):
        row_id: int
        items: List[ClassifiedItem]

    class BatchClassification(BaseModel):
        rows: List[RowClassification]

    return (
        ClassifiedItem,
        RowClassification,
        BatchClassification
    )


def build_system_instruction(allowed_short_names):

    defs_text = "\n".join(
        f"- {CATEGORY_SHORT[full]}: {CATEGORY_DEFINITIONS[full]}"
        for full in CATEGORIES_MAP.keys()
        if CATEGORY_SHORT[full] in allowed_short_names
    )

    return f"""
You are an expert in classifying responses in a study on stress
among public servants (Petrič methodology, 2025).

For each row of text, identify individual meaningful
expressions/phrases that represent an opinion, stressor, positive
factor, or suggestion.

There may be several expressions in one row, separated by commas,
semicolons, conjunctions, or other natural language structures.

Classify each recognized expression into EXACTLY ONE of the following
scientific units:

{defs_text}

If an expression does not belong to any of the units above or is too
general/meaningless, assign the category "None".

Return the expressions in the original language of the text.
Do not translate them.

Be exhaustive and include all meaningful expressions in the row,
not just one.

Preserve Slovenian characters such as č, š and ž exactly as they occur.
"""


@st.cache_resource(show_spinner=False)
def get_client(api_key):

    return genai.Client(api_key=api_key)


def classify_batch_with_ai(
    client,
    model_name,
    rows,
    allowed_short_names,
    row_class_model,
    batch_class_model,
    max_retries=3
):

    system_instruction = build_system_instruction(
        allowed_short_names
    )

    payload = "\n".join(
        f"[{rid}] {text}"
        for rid, text in rows
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=batch_class_model,
        temperature=0.1,
    )

    last_err = None

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model=model_name,
                contents=payload,
                config=config,
            )

            raw = response.text

            raw = re.sub(
                r"^```json|```$",
                "",
                raw.strip(),
                flags=re.MULTILINE
            ).strip()

            data = json.loads(raw)

            result = defaultdict(list)

            for row in data.get("rows", []):

                rid = row["row_id"]

                for item in row.get("items", []):

                    cat_short = item.get("category")

                    phrase = item.get(
                        "phrase",
                        ""
                    ).strip()

                    if (
                        not phrase
                        or cat_short == "None"
                        or cat_short not in SHORT_TO_FULL
                    ):
                        continue

                    result[rid].append(
                        (
                            phrase.lower(),
                            SHORT_TO_FULL[cat_short]
                        )
                    )

            return result

        except Exception as e:

            last_err = e

            time.sleep(
                1.5 * (attempt + 1)
            )

    st.warning(
        f"Error when calling the AI model after "
        f"{max_retries} attempts: {last_err}"
    )

    return {}


def chunk_list(lst, size):

    if size <= 0:
        size = 1

    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def run_ai_classification(
    client,
    model_name,
    df,
    col,
    allowed_short_names,
    batch_size,
    progress_label
):

    if col not in df.columns:

        raise ValueError(
            f"Selected column '{col}' does not exist in the dataset."
        )

    if batch_size <= 0:
        batch_size = 1

    (
        row_class_model,
        _,
        batch_class_model
    ) = build_classification_models(
        allowed_short_names
    )

    rows_text = [
        (i, str(v))
        for i, v in df[col].dropna().items()
    ]

    classified = []
    per_row_categories = []
    per_row_items = []

    progress = st.progress(
        0.0,
        text=progress_label
    )

    batches = list(
        chunk_list(
            rows_text,
            batch_size
        )
    )

    for b_i, batch in enumerate(batches):

        result = classify_batch_with_ai(
            client,
            model_name,
            batch,
            allowed_short_names,
            row_class_model,
            batch_class_model
        )

        for rid, _ in batch:

            items = result.get(
                rid,
                []
            )

            classified.extend(items)

            per_row_categories.append(
                [c for _, c in items]
            )

            per_row_items.append(
                items
            )

        progress.progress(
            (b_i + 1) / max(len(batches), 1),
            text=progress_label
        )

    progress.empty()

    return (
        classified,
        per_row_categories,
        per_row_items
    )


# ============================================================
# 9. OFFLINE CLASSIFICATION
# ============================================================

def clean_and_tokenize(text):

    if not isinstance(text, str):
        return []

    text = text.lower()

    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE
    )

    words = text.split()

    return [
        w
        for w in words
        if w not in SLO_STOPWORDS
        and len(w) > 2
    ]


def classify_word_single(
    word,
    allowed_short_names
):

    priority_order = [
        "Social unit",
        "Performance unit",
        "Individual Psychological unit",
        "Health biological unit",
        "Attentive (physical) unit"
    ]

    for cat in priority_order:

        if CATEGORY_SHORT[cat] not in allowed_short_names:
            continue

        for koren in CATEGORIES_MAP[cat]:

            pattern = (
                rf"\b{re.escape(koren)}\w*\b"
            )

            if re.search(
                pattern,
                word,
                flags=re.IGNORECASE
            ):
                return cat

    return None


def run_offline_classification(
    df,
    col,
    allowed_short_names
):

    if col not in df.columns:

        raise ValueError(
            f"Selected column '{col}' does not exist in the dataset."
        )

    classified = []
    per_row_categories = []
    per_row_items = []

    for row in df[col].dropna():

        row_cats = []
        row_items = []

        for kw in clean_and_tokenize(row):

            cat = classify_word_single(
                kw,
                allowed_short_names
            )

            if cat:

                classified.append(
                    (kw, cat)
                )

                row_cats.append(cat)

                row_items.append(
                    (kw, cat)
                )

        per_row_categories.append(
            row_cats
        )

        per_row_items.append(
            row_items
        )

    return (
        classified,
        per_row_categories,
        per_row_items
    )


# ============================================================
# 10. MATHEMATICAL LOGIC
# ============================================================

def calculate_fo_real_aggregate(
    classified,
    n_override
):

    all_words = [
        w for w, _ in classified
    ]

    fo = len(all_words)

    fr = len(
        set(all_words)
    )

    if fr == 0 or n_override == 0:

        return (
            0.0001,
            fo,
            fr
        )

    rho_o = fo / n_override

    c_o = fo / fr

    fo_real = (
        c_o * rho_o
    ) / 10.0

    return (
        fo_real,
        fo,
        fr
    )


def compute_category_factors(
    classified,
    n_override,
    active_categories,
    weighting_mode="volume"
):

    words_by_cat = defaultdict(list)

    for word, category in classified:

        words_by_cat[category].append(
            word
        )

    result = {}

    for category in active_categories:

        words = words_by_cat.get(
            category,
            []
        )

        fE = len(words)

        frE = len(
            set(words)
        )

        if weighting_mode == "concentration":

            CE = (
                fE / frE
                if frE > 0
                else 0.0001
            )

        else:

            CE = 1.0

        rho = (
            fE / n_override
            if n_override
            else 0.0
        )

        F = (
            CE * rho
        ) / 10.0

        result[category] = {
            "fE": fE,
            "frE": frE,
            "CE": CE,
            "rho": rho,
            "F": F
        }

    return result


def sigma_argument(
    f_sf,
    f_pr,
    f_pf
):

    if f_pf <= 0:
        f_pf = 0.0001

    argument = (
        f_sf * f_pr
    ) / f_pf

    return max(
        argument,
        0.0
    )


def sigma_deg(
    f_sf,
    f_pr,
    f_pf
):

    arg = sigma_argument(
        f_sf,
        f_pr,
        f_pf
    )

    sigma_rad = math.asin(
        math.sqrt(
            min(arg, 1.0)
        )
    )

    return math.degrees(
        sigma_rad
    )


def compute_category_sigmas(
    factors_sf,
    factors_pf,
    factors_pr,
    sigma_total_argument,
    is_summary,
    active_categories
):

    raw_scores = {}

    for category in active_categories:

        f_pf = factors_pf[
            category
        ]["F"]

        f_sf = factors_sf[
            category
        ]["F"]

        f_pr = factors_pr[
            category
        ]["F"]

        if is_summary and f_sf > 0:

            f_pr = min(
                f_pr,
                f_sf * 1.5
            )

        argument = sigma_argument(
            f_sf,
            f_pr,
            f_pf
        )

        bonus = (
            1.15
            if category == "Social unit"
            else 1.0
        )

        weighted_score = (
            argument
            * SLOPE_WEIGHTS[category]
            * bonus
        )

        raw_scores[category] = (
            weighted_score
        )

    total_score = sum(
        raw_scores.values()
    )

    results = {}

    if total_score <= 0:

        for category in active_categories:

            results[category] = {
                "sigma": 0.0,
                "weight_share": 0.0
            }

        return (
            results,
            0.0
        )

    for category in active_categories:

        share = (
            raw_scores[category]
            / total_score
        )

        scaled_argument = min(
            sigma_total_argument * share,
            1.0
        )

        sigma = math.degrees(
            math.asin(
                math.sqrt(
                    scaled_argument
                )
            )
        )

        results[category] = {
            "sigma": sigma,
            "weight_share": share
        }

    return (
        results,
        total_score
    )


def calculate_energy(sigma):

    W_I = 2500.0

    W_EU = (
        W_I
        - (W_I * sigma / 90.0)
    )

    eta = (
        W_EU / W_I
    ) * 100.0

    loss = (
        W_I - W_EU
    )

    return (
        W_EU,
        eta,
        loss
    )


# ============================================================
# 11. FACTOR / OPINION NETWORK
# ============================================================

ROLE_LABELS = {
    "PF": "Positive",
    "SF": "Stress-related",
    "PR": "Opinion / suggestion"
}


ROLE_CRITICALITY = {
    "PF": 0.5,
    "SF": 3.0,
    "PR": 1.5
}


NETWORK_CATEGORY_COLORS = {
    "Attentive (physical) unit": "#3b82f6",
    "Performance unit": "#8b5cf6",
    "Individual Psychological unit": "#f59e0b",
    "Social unit": "#ef4444",
    "Health biological unit": "#10b981"
}


NETWORK_ROLE_COLORS = {
    "PF": "#2563eb",
    "SF": "#dc2626",
    "PR": "#16a34a"
}


def normalize_network_phrase(phrase):

    return re.sub(
        r"\s+",
        " ",
        str(phrase).strip().lower()
    )


def build_network_data(
    analysis,
    max_nodes=25
):

    """
    Builds the common graph data used by both:

    1. Plotly report network.
    2. PyVis interactive network.

    The important difference is that the application network is
    rendered with PyVis, which allows the user to drag nodes
    directly with the mouse.
    """

    node_data = defaultdict(
        lambda: {
            "count": 0,
            "roles": Counter(),
            "categories": Counter(),
            "criticality": 0.0
        }
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Use the original row positions where possible.
    # This prevents PF/SF/PR answers from being incorrectly
    # merged when columns contain different numbers of
    # non-empty cells.
    # --------------------------------------------------------

    row_documents = defaultdict(set)

    for role in ROLE_LABELS:

        items_by_row = analysis[role].get(
            "items_by_original_row",
            {}
        )

        for original_row, items in items_by_row.items():

            for phrase, category in items:

                key = normalize_network_phrase(
                    phrase
                )

                if not key or len(key) < 2:
                    continue

                node_data[key]["count"] += 1

                node_data[key]["roles"][role] += 1

                node_data[key]["categories"][category] += 1

                node_data[key]["criticality"] += (
                    ROLE_CRITICALITY[role]
                    * SLOPE_WEIGHTS.get(
                        category,
                        1.0
                    )
                )

                row_documents[original_row].add(
                    key
                )

    if not node_data:
        return None

    max_nodes = max(
        5,
        min(
            50,
            int(max_nodes)
        )
    )

    selected = sorted(
        node_data,
        key=lambda x: (
            node_data[x]["criticality"],
            node_data[x]["count"]
        ),
        reverse=True
    )[:max_nodes]

    selected_set = set(selected)

    graph = nx.Graph()

    for node in selected:

        d = node_data[node]

        category = (
            d["categories"]
            .most_common(1)[0][0]
        )

        role = (
            d["roles"]
            .most_common(1)[0][0]
        )

        graph.add_node(
            node,
            criticality=d["criticality"],
            count=d["count"],
            category=category,
            role=role
        )

    edge_counts = Counter()

    for row_nodes in row_documents.values():

        nodes = sorted(
            row_nodes.intersection(
                selected_set
            )
        )

        for i in range(len(nodes)):

            for j in range(i + 1, len(nodes)):

                edge_counts[
                    (nodes[i], nodes[j])
                ] += 1

    for (a, b), strength in edge_counts.items():

        graph.add_edge(
            a,
            b,
            strength=strength
        )

    return graph


# ============================================================
# 12. PLOTLY NETWORK FOR REPORT
# ============================================================

def build_plotly_network(graph):

    if graph is None or len(graph.nodes) == 0:
        return None

    if len(graph) == 1:

        only_node = next(
            iter(graph.nodes)
        )

        pos = {
            only_node: (0, 0)
        }

    else:

        pos = nx.spring_layout(
            graph,
            seed=42,
            k=1.7 / math.sqrt(
                max(
                    len(graph.nodes),
                    1
                )
            ),
            iterations=150,
            weight="strength"
        )

    fig = go.Figure()

    edge_styles = [
        (
            "strong",
            3,
            4.5,
            "solid",
            "Strong connection"
        ),
        (
            "medium",
            2,
            2.5,
            "solid",
            "Moderate connection"
        ),
        (
            "weak",
            1,
            1.2,
            "dash",
            "Weak / dashed connection"
        )
    ]

    for (
        style_name,
        min_strength,
        width,
        dash,
        legend_name
    ) in edge_styles:

        x = []
        y = []

        for a, b, data in graph.edges(
            data=True
        ):

            strength = data["strength"]

            qualifies = (
                strength >= min_strength
                if style_name != "weak"
                else strength == 1
            )

            if not qualifies:
                continue

            x.extend([
                pos[a][0],
                pos[b][0],
                None
            ])

            y.extend([
                pos[a][1],
                pos[b][1],
                None
            ])

        if x:

            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    line=dict(
                        width=width,
                        dash=dash
                    ),
                    hoverinfo="skip",
                    name=legend_name
                )
            )

    for category in CATEGORY_SHORT:

        nodes = [
            n
            for n in graph.nodes
            if graph.nodes[n]["category"]
            == category
        ]

        if not nodes:
            continue

        xs = [
            pos[n][0]
            for n in nodes
        ]

        ys = [
            pos[n][1]
            for n in nodes
        ]

        sizes = [
            16
            + 9
            * math.sqrt(
                max(
                    graph.nodes[n]["criticality"],
                    0.1
                )
            )
            for n in nodes
        ]

        hover = [
            (
                f"<b>{html.escape(n)}</b><br>"
                f"Unit: "
                f"{CATEGORY_SHORT[graph.nodes[n]['category']]}<br>"
                f"Role: "
                f"{ROLE_LABELS[graph.nodes[n]['role']]}<br>"
                f"Occurrences: "
                f"{graph.nodes[n]['count']}<br>"
                f"Criticality: "
                f"{graph.nodes[n]['criticality']:.2f}"
            )
            for n in nodes
        ]

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                text=nodes,
                textposition="top center",
                marker=dict(
                    size=sizes,
                    line=dict(width=1)
                ),
                hovertext=hover,
                hoverinfo="text",
                name=CATEGORY_SHORT[category]
            )
        )

    fig.update_layout(
        title=(
            "Factor & opinion network — "
            "node size = criticality"
        ),
        height=720,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0
        ),
        margin=dict(
            l=20,
            r=20,
            t=80,
            b=20
        )
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        visible=False
    )

    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        visible=False,
        scaleanchor="x",
        scaleratio=1
    )

    return fig


# ============================================================
# 13. PYVIS INTERACTIVE NETWORK
# ============================================================

def build_pyvis_network(graph):

    if graph is None or len(graph.nodes) == 0:

        return None

    net = Network(
        height="720px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#1f2937",
        directed=False,
        notebook=False,
        cdn_resources="in_line"
    )

    # --------------------------------------------------------
    # PHYSICS
    # --------------------------------------------------------

    net.set_options(
        """
        {
          "interaction": {
            "dragNodes": true,
            "dragView": true,
            "zoomView": true,
            "hover": true,
            "navigationButtons": true,
            "keyboard": true
          },

          "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based",

            "forceAtlas2Based": {
              "gravitationalConstant": -70,
              "centralGravity": 0.008,
              "springLength": 160,
              "springConstant": 0.045,
              "damping": 0.82,
              "avoidOverlap": 1.0
            },

            "minVelocity": 0.75,
            "stabilization": {
              "enabled": true,
              "iterations": 250,
              "updateInterval": 25,
              "fit": true
            }
          },

          "nodes": {
            "shape": "dot",
            "font": {
              "size": 15,
              "face": "Arial",
              "strokeWidth": 3,
              "strokeColor": "#ffffff"
            },
            "borderWidth": 1.5
          },

          "edges": {
            "smooth": {
              "enabled": true,
              "type": "dynamic"
            },
            "color": {
              "inherit": false,
              "color": "#94a3b8",
              "highlight": "#334155"
            },
            "selectionWidth": 2,
            "hoverWidth": 2
          }
        }
        """
    )

    # --------------------------------------------------------
    # NODES
    # --------------------------------------------------------

    for node in graph.nodes:

        data = graph.nodes[node]

        category = data["category"]

        role = data["role"]

        criticality = float(
            data["criticality"]
        )

        size = (
            18
            + 10
            * math.sqrt(
                max(
                    criticality,
                    0.1
                )
            )
        )

        color = NETWORK_CATEGORY_COLORS.get(
            category,
            "#64748b"
        )

        role_label = ROLE_LABELS.get(
            role,
            role
        )

        tooltip = (
            f"<b>{html.escape(node)}</b><br>"
            f"Unit: "
            f"{html.escape(CATEGORY_SHORT.get(category, category))}<br>"
            f"Role: "
            f"{html.escape(role_label)}<br>"
            f"Occurrences: "
            f"{data['count']}<br>"
            f"Criticality: "
            f"{criticality:.2f}<br>"
            f"Slope weight: "
            f"{SLOPE_WEIGHTS.get(category, 1.0):.2f}"
        )

        net.add_node(
            node,
            label=node,
            title=tooltip,
            size=size,
            color={
                "background": color,
                "border": "#334155",
                "highlight": {
                    "background": color,
                    "border": "#111827"
                },
                "hover": {
                    "background": color,
                    "border": "#111827"
                }
            },
            borderWidth=2,
            font={
                "size": 15,
                "face": "Arial",
                "strokeWidth": 3,
                "strokeColor": "#ffffff"
            }
        )

    # --------------------------------------------------------
    # EDGES
    # --------------------------------------------------------

    for a, b, data in graph.edges(
        data=True
    ):

        strength = int(
            data.get(
                "strength",
                1
            )
        )

        if strength >= 3:

            width = 5

            color = {
                "color": "#64748b",
                "highlight": "#1e293b",
                "hover": "#1e293b"
            }

        elif strength == 2:

            width = 3

            color = {
                "color": "#94a3b8",
                "highlight": "#475569",
                "hover": "#475569"
            }

        else:

            width = 1.5

            color = {
                "color": "#cbd5e1",
                "highlight": "#64748b",
                "hover": "#64748b"
            }

        net.add_edge(
            a,
            b,
            value=strength,
            width=width,
            dashes=(strength == 1),
            title=(
                f"Co-occurrence: {strength}"
            ),
            color=color
        )

    # --------------------------------------------------------
    # GENERATE HTML
    # --------------------------------------------------------

    return net.generate_html()


# ============================================================
# 14. NETWORK TABLE
# ============================================================

def build_network_table(graph):

    if graph is None:

        return None

    rows = []

    for node in sorted(
        graph.nodes,
        key=lambda x:
            graph.nodes[x]["criticality"],
        reverse=True
    ):

        rows.append(
            {
                "Node": node,
                "Unit": CATEGORY_SHORT[
                    graph.nodes[node]["category"]
                ],
                "Role": ROLE_LABELS[
                    graph.nodes[node]["role"]
                ],
                "Occurrences": graph.nodes[node]["count"],
                "Criticality": round(
                    graph.nodes[node]["criticality"],
                    2
                )
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 15. HTML REPORT EXPORT
# ============================================================

def build_report_html(
    title,
    model_name,
    classification_mode,
    sigma_total,
    W_EU,
    eta,
    loss,
    n_input,
    res_df,
    unit_fig,
    role_tree_fig,
    network_fig,
    net_df,
    text_sections=None
):

    generated = time.strftime(
        "%Y-%m-%d %H:%M"
    )

    parts = [

        f"<h1>{html.escape(title)}</h1>",

        (
            f"<p>"
            f"<b>Generated / Ustvarjeno:</b> "
            f"{generated}<br>"
            f"<b>Mode / Način:</b> "
            f"{html.escape(classification_mode)}<br>"
            f"<b>Model:</b> "
            f"{html.escape(model_name or 'Offline dictionary')}<br>"
            f"<b>N:</b> {n_input}"
            f"</p>"
        ),

        (
            "<h2>"
            "Overall results / Skupni rezultati"
            "</h2>"
        ),

        (
            "<div class='result-box'>"
            "<p>"
            "<b>Stress intensity / Stresna intenzivnost:</b> "
            f"{sigma_total:.2f} °S<br>"
            "<b>Rating / Ocena:</b> "
            f"{html.escape(rate_sigma(sigma_total))}<br>"
            "<b>Efficiency / Učinkovitost:</b> "
            f"{eta:.1f}%<br>"
            "<b>Energy loss / Izguba energije:</b> "
            f"{loss:.0f} Kcal<br>"
            "<b>Useful energy / Koristna energija:</b> "
            f"{W_EU:.0f} Kcal"
            "</p>"
            "</div>"
        ),

        (
            "<h2>"
            "Distribution by scientific unit / "
            "Porazdelitev po znanstvenih enotah"
            "</h2>"
        ),

        res_df.to_html(
            index=False,
            border=0,
            classes="report-table",
            justify="left"
        )
    ]

    # --------------------------------------------------------
    # TEXT SECTIONS
    # --------------------------------------------------------

    if text_sections:

        for heading, body in text_sections:

            safe_body = (
                html.escape(
                    str(body)
                ).replace(
                    "\n",
                    "<br>"
                )
            )

            parts.append(
                f"<h2>{html.escape(str(heading))}</h2>"
            )

            parts.append(
                f"<div class='text-section'>"
                f"{safe_body}"
                f"</div>"
            )

    # --------------------------------------------------------
    # PLOTLY VISUALIZATIONS
    # --------------------------------------------------------

    plotly_added = False

    visualizations = [

        (
            "Stress intensity by scientific unit / "
            "Stresna intenzivnost po znanstvenih enotah",
            unit_fig
        ),

        (
            "All classified phrases by role and unit / "
            "Vsi klasificirani izrazi po vlogi in enoti",
            role_tree_fig
        ),

        (
            "Factor and opinion network / "
            "Omrežje dejavnikov in mnenj",
            network_fig
        )
    ]

    for heading, fig in visualizations:

        if fig is None:
            continue

        parts.append(
            f"<h2>{html.escape(heading)}</h2>"
        )

        try:

            plot_html = fig.to_html(
                full_html=False,
                include_plotlyjs=(
                    "cdn"
                    if not plotly_added
                    else False
                ),
                config={
                    "responsive": True,
                    "displaylogo": False
                }
            )

            parts.append(
                plot_html
            )

            plotly_added = True

        except Exception as e:

            parts.append(
                "<p><i>"
                "Visualization could not be embedded "
                "in the HTML report: "
                f"{html.escape(str(e))}"
                "</i></p>"
            )

    # --------------------------------------------------------
    # NETWORK TABLE
    # --------------------------------------------------------

    if (
        net_df is not None
        and not net_df.empty
    ):

        parts.append(
            "<h2>"
            "Critical network nodes / "
            "Kritična vozlišča omrežja"
            "</h2>"
        )

        parts.append(
            net_df.to_html(
                index=False,
                border=0,
                classes="report-table",
                justify="left"
            )
        )

    # --------------------------------------------------------
    # COMPLETE HTML
    # --------------------------------------------------------

    return f"""<!doctype html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta http-equiv="Content-Type"
      content="text/html; charset=UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>{html.escape(title)}</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    font-family:
        "Segoe UI",
        "Noto Sans",
        Arial,
        Helvetica,
        sans-serif;

    margin: 0;
    padding: 35px;

    color: #1f2937;
    background: #ffffff;

    line-height: 1.55;

    font-size: 15px;
}}

h1 {{
    color: #111827;
    font-size: 30px;
    margin-bottom: 8px;
}}

h2 {{
    color: #1f2937;
    font-size: 21px;
    margin-top: 42px;
    margin-bottom: 15px;

    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 7px;
}}

p {{
    margin: 8px 0 14px;
}}

.result-box {{
    background: #f8fafc;
    border: 1px solid #dbe3ec;
    border-radius: 12px;
    padding: 16px 20px;
    margin: 15px 0 25px;
}}

.text-section {{
    white-space: normal;
    background: #f8fafc;
    border-left: 4px solid #94a3b8;
    padding: 12px 16px;
    margin: 10px 0 20px;
}}

.report-table {{
    border-collapse: collapse;
    width: 100%;
    margin: 15px 0 30px;
    font-size: 14px;
}}

.report-table th,
.report-table td {{
    border: 1px solid #d1d5db;
    padding: 8px 10px;
    text-align: left;
    vertical-align: top;
}}

.report-table th {{
    background: #f1f5f9;
    font-weight: 700;
}}

.report-table tr:nth-child(even) {{
    background: #f8fafc;
}}

.js-plotly-plot {{
    width: 100% !important;
    margin: 10px 0 35px 0;
}}

.footer {{
    margin-top: 50px;
    padding-top: 15px;
    border-top: 1px solid #e5e7eb;
    color: #64748b;
    font-size: 12px;
}}

@media print {{

    body {{
        padding: 15px;
        font-size: 12px;
    }}

    h1 {{
        font-size: 24px;
    }}

    h2 {{
        font-size: 17px;
        page-break-after: avoid;
    }}

    .js-plotly-plot {{
        page-break-inside: avoid;
    }}

    .report-table {{
        page-break-inside: avoid;
    }}
}}

</style>

</head>

<body>

{''.join(parts)}

<div class="footer">
    Petrič Stress Analysis Pro<br>
    Scientific basis: Karl Petrič, <i>Gaining knowledge through understanding distress and positive factors in social environments</i>, European Review of Applied Sociology, 2025. DOI: 10.2478/eras-2025-0003
</div>

</body>

</html>"""


# ============================================================
# 16. MAIN STREAMLIT APPLICATION
# ============================================================

def main():

    # --------------------------------------------------------
    # SIDEBAR LOGO
    # --------------------------------------------------------

    with st.sidebar:

        components.html(
            SIDEBAR_LOGO_HTML,
            height=158,
            scrolling=False
        )

    # --------------------------------------------------------
    # HEADER AND CENTRAL CONTROL PANEL
    # --------------------------------------------------------

    st.markdown(
        "# 📊 Stress degree and kcal analysis PRO"
    )

    st.caption(
        "Classification with Google Gemini/Gemma models · "
        "5 scientific units "
        "(Social = social + partial social)"
    )

    with st.container(border=True):

        header_left, header_right = st.columns(
            [5, 1],
            vertical_alignment="center"
        )

        with header_left:

            st.markdown(
                "<h3 class='control-panel-title'>⚙️ Analysis control panel</h3>",
                unsafe_allow_html=True
            )

            st.markdown(
                "<p class='control-panel-subtitle'>"
                "Configure classification, analysis scope, visualization "
                "and data input in one central workspace."
                "</p>",
                unsafe_allow_html=True
            )

        with header_right:

            if st.button(
                "🔄 Reset session",
                use_container_width=True
            ):

                reset_app()

        ai_column, analysis_column, data_column = st.columns(
            [1.25, 1, 1],
            gap="large"
        )

        with ai_column:

            st.markdown(
                "<span class='section-label'>🤖 AI Classification (Google)</span>",
                unsafe_allow_html=True
            )

            classification_mode = st.radio(
                "Classification mode",
                [
                    "AI model (Gemini / Gemma)",
                    "Dictionary (offline, no API call)"
                ]
            )

            api_key = None
            model_name = None
            batch_size = 15

            if classification_mode.startswith("AI"):

                api_key = st.text_input(
                    "Google AI API key",
                    type="password",
                    help=(
                        "Get a free key at "
                        "https://aistudio.google.com/apikey"
                    )
                )

                model_name = st.selectbox(
                    "Model",
                    AVAILABLE_MODELS,
                    index=0
                )

                if (
                    model_name
                    != AVAILABLE_MODELS[0]
                ):

                    st.caption(
                        MODEL_NOTES.get(
                            model_name,
                            ""
                        )
                    )

                batch_size = st.slider(
                    "Batch size (rows per call)",
                    0,
                    50,
                    15
                )

                if batch_size == 0:

                    st.warning(
                        "Batch size 0 is not valid for "
                        "an API call; it will be treated as 1."
                    )

                    batch_size = 1

            st.divider()

            st.markdown(
                "<span class='section-label'>🧭 Scientific units</span>",
                unsafe_allow_html=True
            )

            included_shorts = st.multiselect(
                "Included scientific units",
                list(CATEGORY_SHORT.values()),
                default=list(
                    CATEGORY_SHORT.values()
                )
            )

            active_categories = [
                SHORT_TO_FULL[s]
                for s in included_shorts
            ]

            if not active_categories:

                active_categories = list(
                    CATEGORIES_MAP.keys()
                )

        with analysis_column:

            st.markdown(
                "<span class='section-label'>🧪 Sample and calculation</span>",
                unsafe_allow_html=True
            )

            n_input = st.number_input(
                "Number of respondents (N)",
                min_value=1,
                value=210
            )

            is_summary = st.checkbox(
                "The file contains a SUMMARY",
                value=True
            )

            weighting_label = st.radio(
                "Weighting within the unit",
                [
                    "Volume (frequency)",
                    "Concentration (repeatability)"
                ]
            )

            weighting_mode = (
                "volume"
                if "Volume" in weighting_label
                else "concentration"
            )

            st.divider()

            st.markdown(
                "<span class='section-label'>📈 Visualization</span>",
                unsafe_allow_html=True
            )

            chart_mode = st.radio(
                "Distribution display",
                [
                    "Bar chart",
                    "Treemap (colorful)",
                    "Both"
                ]
            )

            network_nodes = st.slider(
                "Number of network nodes",
                min_value=5,
                max_value=50,
                value=25,
                step=1,
                help=(
                    "The most critical factors/opinions "
                    "become the largest nodes."
                )
            )

        with data_column:

            st.markdown(
                "<span class='section-label'>📁 Data input</span>",
                unsafe_allow_html=True
            )

            uploaded_file = st.file_uploader(
                "Upload data",
                type=[
                    "txt",
                    "csv",
                    "xlsx"
                ]
            )

            # ------------------------------------------------
            # Reset the "run" trigger whenever a new/changed
            # file is uploaded, so the user has to press
            # Action again before the analysis (re)starts.
            # ------------------------------------------------

            if uploaded_file is not None:

                file_signature = (
                    f"{uploaded_file.name}_"
                    f"{uploaded_file.size}"
                )

                if st.session_state.get(
                    "uploaded_file_signature"
                ) != file_signature:

                    st.session_state[
                        "uploaded_file_signature"
                    ] = file_signature

                    st.session_state[
                        "analysis_triggered"
                    ] = False

                st.success(
                    f"Loaded: {uploaded_file.name}"
                )

            else:

                st.session_state[
                    "analysis_triggered"
                ] = False

            with st.container(key="action_btn_container"):

                run_clicked = st.button(
                    "▶️ Action — Run analysis",
                    use_container_width=True,
                    type="primary",
                    disabled=(uploaded_file is None)
                )

            if run_clicked:

                st.session_state[
                    "analysis_triggered"
                ] = True

            if (
                uploaded_file is not None
                and not st.session_state.get(
                    "analysis_triggered",
                    False
                )
            ):

                st.caption(
                    "File loaded. Click **Action** to run "
                    "the analysis."
                )

    # --------------------------------------------------------
    # FILE CHECK
    # --------------------------------------------------------

    if not uploaded_file:

        st.info(
            "📁 Upload a file in the central control panel to start the analysis.",
            icon="ℹ️"
        )

        st.markdown(
            "### 📚 Scientific basis"
        )
        st.markdown(
            "**Petrič, K.** *Gaining knowledge through understanding distress and positive factors in social environments.* "
            "**European Review of Applied Sociology**, 2025-06-03, Journal article. "
            "DOI: [10.2478/eras-2025-0003](https://doi.org/10.2478/eras-2025-0003)"
        )

        return

    if not st.session_state.get(
        "analysis_triggered",
        False
    ):

        st.info(
            "▶️ File loaded. Click the **Action** button "
            "in the central control panel to run the analysis.",
            icon="▶️"
        )

        return

    # --------------------------------------------------------
    # AI SETTINGS CHECK
    # --------------------------------------------------------

    if classification_mode.startswith("AI"):

        if not api_key:

            st.warning(
                "⚠️ Enter a Google AI API key in the central control panel "
                "to use AI classification."
            )

            return

        if model_name == AVAILABLE_MODELS[0]:

            st.warning(
                "⚠️ Select a model in the central control panel."
            )

            return

    # --------------------------------------------------------
    # READ DATA
    # --------------------------------------------------------

    try:

        if uploaded_file.name.lower().endswith(
            ".xlsx"
        ):

            df = pd.read_excel(
                uploaded_file
            )

        elif uploaded_file.name.lower().endswith(
            ".txt"
        ):

            df = pd.read_csv(
                uploaded_file,
                sep="\t",
                engine="python",
                on_bad_lines="skip"
            )

        else:

            df = pd.read_csv(
                uploaded_file,
                engine="python",
                on_bad_lines="skip"
            )

    except Exception as e:

        st.error(
            f"Error reading the file: {e}"
        )

        return

    # --------------------------------------------------------
    # DATASET VALIDATION
    # --------------------------------------------------------

    if df.empty:

        st.error(
            "The uploaded dataset is empty."
        )

        return

    if len(df.columns) == 0:

        st.error(
            "The uploaded dataset contains no columns."
        )

        return

    target_cols = df.columns.tolist()

    # --------------------------------------------------------
    # COLUMN SELECTION
    # --------------------------------------------------------

    with st.container(border=True):

        st.markdown(
            "### 🧩 Column selection"
        )

        # IMPORTANT:
        # All three labels are now fully English.

        col_pf = st.selectbox(
            "Positive factors (PF)",
            target_cols,
            index=0
        )

        col_sf = st.selectbox(
            "Stress-related factors (SF)",
            target_cols,
            index=min(
                1,
                len(target_cols) - 1
            )
        )

        col_pr = st.selectbox(
            "Suggestions (PR)",
            target_cols,
            index=min(
                2,
                len(target_cols) - 1
            )
        )

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    analysis = {}

    if classification_mode.startswith("AI"):

        try:

            client = get_client(
                api_key
            )

        except Exception as e:

            st.error(
                f"Could not initialize Google AI client: {e}"
            )

            return

        for role, col, label in [

            (
                "PF",
                col_pf,
                "🔵 Classifying positive factors ..."
            ),

            (
                "SF",
                col_sf,
                "🔴 Classifying stress-related factors ..."
            ),

            (
                "PR",
                col_pr,
                "🟢 Classifying suggestions ..."
            )

        ]:

            try:

                (
                    cls,
                    per_row,
                    per_row_items
                ) = run_ai_classification(
                    client,
                    model_name,
                    df,
                    col,
                    included_shorts,
                    batch_size,
                    label
                )

            except Exception as e:

                st.error(
                    f"Classification error for {role}: {e}"
                )

                cls = []
                per_row = []
                per_row_items = []

            # ------------------------------------------------
            # Preserve original dataframe row IDs for network
            # ------------------------------------------------

            items_by_original_row = {}

            non_empty_rows = [
                (i, str(v))
                for i, v in df[col].dropna().items()
            ]

            for index, items in zip(
                [i for i, _ in non_empty_rows],
                per_row_items
            ):

                items_by_original_row[
                    index
                ] = items

            analysis[role] = {
                "classified": cls,
                "per_row": per_row,
                "per_row_items": per_row_items,
                "items_by_original_row":
                    items_by_original_row,
                "col_name": col
            }

    else:

        for role, col in [
            ("PF", col_pf),
            ("SF", col_sf),
            ("PR", col_pr)
        ]:

            try:

                (
                    cls,
                    per_row,
                    per_row_items
                ) = run_offline_classification(
                    df,
                    col,
                    included_shorts
                )

            except Exception as e:

                st.error(
                    f"Offline classification error "
                    f"for {role}: {e}"
                )

                cls = []
                per_row = []
                per_row_items = []

            # ------------------------------------------------
            # Preserve original dataframe row IDs for network
            # ------------------------------------------------

            items_by_original_row = {}

            non_empty_rows = [
                (i, v)
                for i, v in df[col].dropna().items()
            ]

            for index, items in zip(
                [i for i, _ in non_empty_rows],
                per_row_items
            ):

                items_by_original_row[
                    index
                ] = items

            analysis[role] = {
                "classified": cls,
                "per_row": per_row,
                "per_row_items": per_row_items,
                "items_by_original_row":
                    items_by_original_row,
                "col_name": col
            }

    # ========================================================
    # GLOBAL CALCULATION
    # ========================================================

    f_pf_agg, _, _ = calculate_fo_real_aggregate(
        analysis["PF"]["classified"],
        n_input
    )

    f_sf_agg, _, _ = calculate_fo_real_aggregate(
        analysis["SF"]["classified"],
        n_input
    )

    f_pr_agg, _, _ = calculate_fo_real_aggregate(
        analysis["PR"]["classified"],
        n_input
    )

    if is_summary:

        f_pr_agg = min(
            f_pr_agg,
            f_sf_agg * 1.5
        )

    sigma_total = sigma_deg(
        f_sf_agg,
        f_pr_agg,
        f_pf_agg
    )

    W_EU, eta, loss = calculate_energy(
        sigma_total
    )

    # ========================================================
    # OVERALL RESULTS
    # ========================================================

    st.markdown(
        "## 🎯 Overall Results"
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Stress intensity",
        f"{sigma_total:.2f} °S",
        rate_sigma(sigma_total)
    )

    m2.metric(
        "Efficiency",
        f"{eta:.1f} %"
    )

    m3.metric(
        "Energy loss",
        f"{loss:.0f} Kcal"
    )

    m4.metric(
        "Sample (N)",
        n_input
    )

    st.progress(
        min(
            sigma_total / 90.0,
            1.0
        )
    )

    # ========================================================
    # BREAKDOWN BY UNIT
    # ========================================================

    st.divider()

    f_pf_cat = compute_category_factors(
        analysis["PF"]["classified"],
        n_input,
        active_categories,
        weighting_mode
    )

    f_sf_cat = compute_category_factors(
        analysis["SF"]["classified"],
        n_input,
        active_categories,
        weighting_mode
    )

    f_pr_cat = compute_category_factors(
        analysis["PR"]["classified"],
        n_input,
        active_categories,
        weighting_mode
    )

    sig_total_arg = min(
        sigma_argument(
            f_sf_agg,
            f_pr_agg,
            f_pf_agg
        ),
        1.0
    )

    cat_sigmas, _ = compute_category_sigmas(
        f_sf_cat,
        f_pf_cat,
        f_pr_cat,
        sig_total_arg,
        is_summary,
        active_categories
    )

    rows = []

    for cat, data in cat_sigmas.items():

        rows.append(
            {
                "Unit": CATEGORY_SHORT[cat],
                "σ (°S)": round(
                    data["sigma"],
                    2
                ),
                "Share (%)": round(
                    data["weight_share"] * 100,
                    1
                ),
                "Rating": rate_sigma(
                    data["sigma"]
                )
            }
        )

    res_df = (
        pd.DataFrame(rows)
        .sort_values(
            by="σ (°S)",
            ascending=False
        )
    )

    # ========================================================
    # DISTRIBUTION BY SCIENTIFIC UNIT
    # ========================================================

    st.markdown(
        "### Distribution by Scientific Unit"
    )

    col_left, col_right = st.columns(
        [1, 1]
    )

    unit_fig = px.bar(
        res_df,
        x="Unit",
        y="σ (°S)",
        color="σ (°S)",
        color_continuous_scale="Reds",
        height=300,
        title=(
            "Stress intensity by scientific unit"
        )
    )

    with col_left:

        st.dataframe(
            res_df,
            use_container_width=True,
            hide_index=True
        )

    with col_right:

        if chart_mode in (
            "Bar chart",
            "Both"
        ):

            st.plotly_chart(
                unit_fig,
                use_container_width=True
            )

        if chart_mode in (
            "Treemap (colorful)",
            "Both"
        ):

            unit_treemap_fig = px.treemap(
                res_df,
                path=["Unit"],
                values="σ (°S)",
                color="σ (°S)",
                color_continuous_scale="RdYlGn_r",
                height=350,
                title=(
                    "Stress profile by scientific unit"
                )
            )

            st.plotly_chart(
                unit_treemap_fig,
                use_container_width=True
            )

    # ========================================================
    # TREEMAP PF / SF / PR
    # ========================================================

    st.markdown(
        "### 🗺️ Treemap: All Phrases by Role and Unit"
    )

    tree_rows = []

    role_labels = {
        "PF": "Positive",
        "SF": "Stress-related",
        "PR": "Suggestions"
    }

    for role, label in role_labels.items():

        freq = Counter(
            c
            for _, c
            in analysis[role]["classified"]
        )

        for cat, count in freq.items():

            tree_rows.append(
                {
                    "Role": label,
                    "Unit": CATEGORY_SHORT[cat],
                    "Frequency": count
                }
            )

    role_tree_fig = None

    if tree_rows:

        tree_df = pd.DataFrame(
            tree_rows
        )

        role_tree_fig = px.treemap(
            tree_df,
            path=[
                "Role",
                "Unit"
            ],
            values="Frequency",
            color="Frequency",
            color_continuous_scale="Turbo",
            height=450,
            title=(
                "All classified phrases by role and unit"
            )
        )

        st.plotly_chart(
            role_tree_fig,
            use_container_width=True
        )

    else:

        st.caption(
            "There are no classified expressions "
            "to display in the treemap."
        )

    # ========================================================
    # FACTOR / OPINION NETWORK
    # ========================================================

    st.divider()

    st.markdown(
        "## 🕸️ Factor and Opinion Network"
    )

    st.markdown(
        """
        <div class="network-help">
        <b>Interactive network:</b>
        drag individual nodes with the mouse to reposition them.
        Use the mouse wheel to zoom, drag the background to move the
        entire network, and use the navigation controls for additional
        positioning. Larger nodes represent higher criticality.
        </div>
        """,
        unsafe_allow_html=True
    )

    graph = build_network_data(
        analysis,
        network_nodes
    )

    network_fig = build_plotly_network(
        graph
    )

    interactive_network_html = build_pyvis_network(
        graph
    )

    net_df = build_network_table(
        graph
    )

    if interactive_network_html is not None:

        # ----------------------------------------------------
        # IMPORTANT:
        # PyVis provides real mouse-dragging of nodes.
        # ----------------------------------------------------

        components.html(
            interactive_network_html,
            height=750,
            scrolling=False
        )

        st.caption(
            "Node size = criticality. "
            "Strong links are thick solid lines, "
            "moderate links are thinner solid lines, "
            "and weak links are dashed. "
            "Links represent co-occurrence in the same "
            "respondent answer. "
            "Nodes can be freely moved with the mouse."
        )

        with st.expander(
            "Critical Nodes / Opinions"
        ):

            if net_df is not None:

                st.dataframe(
                    net_df,
                    use_container_width=True,
                    hide_index=True
                )

    else:

        st.info(
            "No classified factors/opinions are available "
            "for the network."
        )

    # ========================================================
    # QUALITATIVE REVIEW
    # ========================================================

    with st.expander(
        "🔍 Classification Details for Words/Phrases"
    ):

        t1, t2, t3 = st.tabs(
            [
                "🟢 Positive",
                "🔴 Stress-related",
                "🔵 Suggestions"
            ]
        )

        for tab, role in zip(
            [t1, t2, t3],
            ["PF", "SF", "PR"]
        ):

            with tab:

                freq = Counter(
                    category
                    for _, category
                    in analysis[role]["classified"]
                )

                if freq:

                    st.table(
                        pd.DataFrame(
                            [
                                {
                                    "Unit":
                                        CATEGORY_SHORT.get(
                                            category,
                                            category
                                        ),
                                    "Frequency":
                                        count
                                }
                                for category, count
                                in freq.items()
                            ]
                        )
                    )

                else:

                    st.caption(
                        "No classified expressions."
                    )

                st.markdown(
                    "**Examples of classified phrases:**"
                )

                sample = (
                    analysis[role]["classified"][:40]
                )

                if sample:

                    sample_df = pd.DataFrame(
                        [
                            {
                                "Phrase": phrase,
                                "Unit":
                                    CATEGORY_SHORT[
                                        category
                                    ]
                            }
                            for phrase, category
                            in sample
                        ]
                    )

                    st.dataframe(
                        sample_df,
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.caption(
                        "No examples available."
                    )

    # ========================================================
    # HTML REPORT EXPORT
    # ========================================================

    st.divider()

    st.markdown(
        "## 💾 Save report"
    )

    st.caption(
        "The HTML report contains all calculations, tables, "
        "text and interactive Plotly visualizations. "
        "Slovenian and English characters "
        "(č, š, ž, Č, Š, Ž) are fully supported."
    )

    report_title = (
        "Stress degree and kcal analysis PRO — Report"
    )

    html_report = build_report_html(
        report_title,
        model_name,
        classification_mode,
        sigma_total,
        W_EU,
        eta,
        loss,
        n_input,
        res_df,
        unit_fig,
        role_tree_fig,
        network_fig,
        net_df,
        text_sections=[
            (
                "Method",
                (
                    "PF = positive factors; "
                    "SF = stress-related factors; "
                    "PR = suggestions/opinions. "
                    "The network is based on co-occurrence "
                    "of classified expressions within the "
                    "same respondent answer."
                )
            ),
            (
                "Network interpretation",
                (
                    "Node size represents criticality. "
                    "Stress-related expressions receive "
                    "the highest role weight, followed by "
                    "suggestions/opinions and positive factors. "
                    "Scientific unit slope weights are also applied. "
                    "The interactive application network allows "
                    "nodes to be freely repositioned with the mouse."
                )
            )
        ]
    )

    # --------------------------------------------------------
    # HTML DOWNLOAD
    # --------------------------------------------------------

    st.download_button(
        "⬇️ Save Complete Report as HTML",
        data=html_report.encode(
            "utf-8"
        ),
        file_name=(
            "petric_stress_analysis_report.html"
        ),
        mime="text/html; charset=utf-8",
        use_container_width=True
    )


# ============================================================
# 17. APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
