import streamlit as st
import pandas as pd
import re
import math
import json
import time

from collections import Counter, defaultdict
from typing import List, Literal

import plotly.express as px

from pydantic import BaseModel
from google import genai
from google.genai import types


# ============================================================
# 1. PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="Petrič Stress Analysis Pro",
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
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
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
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. STOPWORDS
# Slovenian stopwords are retained because the application
# analyses Slovenian input text.
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
    short_name: full_name
    for full_name, short_name in CATEGORY_SHORT.items()
}


# These definitions are paraphrases for AI classification.
CATEGORY_DEFINITIONS = {
    "Attentive (physical) unit": (
        "Physical and sensory environment: noise, lighting, temperature, "
        "air quality, ergonomics, spatial arrangement, aesthetics, odors, "
        "and colors."
    ),

    "Performance unit": (
        "Factors related to task performance: deadlines, workload, "
        "administrative procedures, access to information, training, "
        "efficiency of tools and processes, and physical activity used "
        "for stress relief."
    ),

    "Individual Psychological unit": (
        "Internal subjective emotional and psychological states: fear, "
        "anxiety, self-confidence, calmness, feelings, personal meaning, "
        "values, relaxation, self-image, and mental well-being."
    ),

    "Social unit": (
        "Interpersonal, organizational, and status-related factors: "
        "relationships with colleagues, supervisors, family, and friends; "
        "communication, conflicts, bullying, teamwork, organizational "
        "climate, hierarchy, status, fairness, recognition, salary, "
        "job security, and economic conditions. This unit combines the "
        "social and partial-social units from the article."
    ),

    "Health biological unit": (
        "Physical health and biological factors: illness, fatigue, sleep, "
        "hygiene, nutrition, physiological condition, and exhaustion."
    )
}


# Slovenian roots are retained for offline classification.
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
        "administra", "birokra", "obrazc", "poročil", "postopk",
        "navodil", "veščin", "hitenj", "naglic", "stisk",
        "preobremen", "neizkušn", "učinkovit", "biro", "togi",
        "rutin", "nujne", "izobraž", "usposab", "proces",
        "poenostav", "inovac", "rešitev", "urnik", "ure",
        "izvajanj", "regula", "hrm", "direktiv", "ukaluplj",
        "iskanj", "gradiv", "polic", "katalog", "orientac",
        "podatkov", "fond", "isposoj", "job", "balance", "goal",
        "cilj", "študij", "literature", "izvodi", "raziskav",
        "iskanje", "tasks", "program", "training", "exercise",
        "activities", "šport", "rekreac", "tek", "joga",
        "plavanj", "kolo"
    ],

    "Individual Psychological unit": [
        "strah", "tesnob", "samozav", "čustv", "stres", "frustr",
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb",
        "napetos", "psih", "travm", "osebno", "samopodob",
        "nasil", "negativ", "dušev", "žalost", "ogroženost",
        "nelagod", "zadovolj", "psihi", "nemir", "choice", "life",
        "memory", "spomin", "art", "umetnos", "irrational",
        "uncertain", "uncertainty", "peace", "feeling", "hope",
        "values", "vrednot", "ponižanj", "identitet", "dopust",
        "izlet", "potovan", "journey", "sprošč", "relax",
        "medit", "dihan", "narav", "spomini", "praznina",
        "osebnost", "samokontrol", "vera", "mirnost"
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
        "zaupan", "trust", "support", "podpor", "klima",
        "vzdušje", "pripadnost", "ignor", "nerazum", "posluš",
        "organizac", "organizaciji", "organizacijo", "sestank",
        "meeting", "meetings", "management", "leader", "leadership",
        "manager", "plač", "dohod", "denar", "finanč", "nagrad",
        "status", "priznan", "revšč", "standar", "nepravič",
        "nestimul", "krivic", "dostojen", "zaposlit", "služb",
        "karier", "napredov", "varnost", "staž", "benefic",
        "ekonom", "proračun", "pokojnin", "sredstv", "zamudn",
        "opomin", "kazn", "plačev", "plačilo", "money", "salary",
        "financial", "budget", "stability", "znesek", "družb",
        "law", "zakon", "orož", "weapon", "alcohol", "economic",
        "level", "standard", "overcrowding", "crowding",
        "injustice", "punishment", "reward", "recognition"
    ],

    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "spanj", "utrujen",
        "izčrpan", "higien", "čistoč", "sleep", "rest", "dihanje",
        "izčrpanost", "utrujenost", "zdravje", "bolečina", "virus",
        "infekcij", "higiena", "prehran", "diet", "biološ",
        "fiziolo", "telo", "utrujena", "spanja", "telesno",
        "exhaustion"
    ]
}


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
    (45.04, "Moderate"),
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
# 5. GOOGLE MODELS
# ============================================================

AVAILABLE_MODELS = [
    "-- select a model --",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it"
]


# ============================================================
# 6. STRUCTURED AI OUTPUT
# ============================================================

def build_classification_models(allowed_short_names):
    """
    Dynamically creates Pydantic schemas that allow only the currently
    selected short category names, plus None.
    """
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
    definitions_text = "\n".join(
        f"- {CATEGORY_SHORT[full]}: "
        f"{CATEGORY_DEFINITIONS[full]}"
        for full in CATEGORIES_MAP.keys()
        if CATEGORY_SHORT[full] in allowed_short_names
    )

    return f"""
You are an expert in classifying responses from a study about stress among
public-sector employees, based on the Petrič methodology from 2025.

For every row of text, identify meaningful expressions or phrases that
represent an opinion, stressor, positive factor, or suggestion. A row may
contain several expressions separated by commas, semicolons, or the word "and".

Classify each identified expression into exactly one of the following
scientific units:

{definitions_text}

If an expression does not belong to any of the units above, or if it is too
general or meaningless, assign the category "None".

Return the expressions in the original language of the input text.
Do not translate them.

Be comprehensive and identify all meaningful expressions in each row.
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
    """
    Input:
        rows: list of (row_id, text)

    Output:
        dict mapping row_id to:
        [(phrase, full_category_name), ...]
    """
    system_instruction = build_system_instruction(
        allowed_short_names
    )

    payload = "\n".join(
        f"[{row_id}] {text}"
        for row_id, text in rows
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=batch_class_model,
        temperature=0.1
    )

    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=payload,
                config=config
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
                row_id = row["row_id"]

                for item in row.get("items", []):
                    category_short = item.get("category")
                    phrase = item.get("phrase", "").strip()

                    if not phrase:
                        continue

                    if category_short == "None":
                        continue

                    if category_short not in SHORT_TO_FULL:
                        continue

                    result[row_id].append(
                        (
                            phrase.lower(),
                            SHORT_TO_FULL[category_short]
                        )
                    )

            return result

        except Exception as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))

    st.warning(
        f"AI model error after {max_retries} attempts: "
        f"{last_error}"
    )

    return {}


def chunk_list(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def run_ai_classification(
    client,
    model_name,
    dataframe,
    column,
    allowed_short_names,
    batch_size,
    progress_label
):
    row_class_model, _, batch_class_model = (
        build_classification_models(
            allowed_short_names
        )
    )

    rows_text = [
        (index, str(value))
        for index, value in dataframe[column].dropna().items()
    ]

    classified = []
    per_row_categories = []

    progress = st.progress(
        0.0,
        text=progress_label
    )

    batches = list(
        chunk_list(rows_text, batch_size)
    )

    for batch_index, batch in enumerate(batches):
        result = classify_batch_with_ai(
            client=client,
            model_name=model_name,
            rows=batch,
            allowed_short_names=allowed_short_names,
            row_class_model=row_class_model,
            batch_class_model=batch_class_model
        )

        for row_id, _ in batch:
            items = result.get(row_id, [])

            classified.extend(items)

            per_row_categories.append(
                [category for _, category in items]
            )

        progress.progress(
            (batch_index + 1) / max(len(batches), 1),
            text=progress_label
        )

    progress.empty()

    return classified, per_row_categories


# ============================================================
# 7. OFFLINE CLASSIFICATION
# ============================================================

def clean_and_tokenize(text):
    if not isinstance(text, str):
        return []

    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()

    return [
        word
        for word in words
        if word not in SLO_STOPWORDS and len(word) > 2
    ]


def classify_word_single(word, allowed_short_names):
    priority_order = [
        "Social unit",
        "Performance unit",
        "Individual Psychological unit",
        "Health biological unit",
        "Attentive (physical) unit"
    ]

    for category in priority_order:
        if CATEGORY_SHORT[category] not in allowed_short_names:
            continue

        for root in CATEGORIES_MAP[category]:
            pattern = rf"\b{re.escape(root)}\w*\b"

            if re.search(pattern, word):
                return category

    return None


def run_offline_classification(
    dataframe,
    column,
    allowed_short_names
):
    classified = []
    per_row_categories = []

    for row in dataframe[column].dropna():
        row_categories = []

        for keyword in clean_and_tokenize(row):
            category = classify_word_single(
                keyword,
                allowed_short_names
            )

            if category:
                classified.append(
                    (keyword, category)
                )

                row_categories.append(category)

        per_row_categories.append(row_categories)

    return classified, per_row_categories


# ============================================================
# 8. MATHEMATICAL LOGIC
# ============================================================

def calculate_fo_real_aggregate(classified, n_override):
    all_words = [
        word
        for word, _ in classified
    ]

    fo = len(all_words)
    fr = len(set(all_words))

    if fr == 0 or n_override == 0:
        return 0.0001, fo, fr

    rho_o = fo / n_override
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10.0

    return fo_real, fo, fr


def compute_category_factors(
    classified,
    n_override,
    active_categories,
    weighting_mode="volume"
):
    words_by_category = defaultdict(list)

    for word, category in classified:
        words_by_category[category].append(word)

    result = {}

    for category in active_categories:
        words = words_by_category.get(
            category,
            []
        )

        frequency = len(words)
        unique_frequency = len(set(words))

        if weighting_mode == "concentration":
            concentration = (
                frequency / unique_frequency
                if unique_frequency > 0
                else 0.0001
            )
        else:
            concentration = 1.0

        density = (
            frequency / n_override
            if n_override
            else 0.0
        )

        factor = (
            concentration * density
        ) / 10.0

        result[category] = {
            "frequency": frequency,
            "unique_frequency": unique_frequency,
            "concentration": concentration,
            "density": density,
            "factor": factor
        }

    return result


def sigma_argument(f_sf, f_pr, f_pf):
    if f_pf <= 0:
        f_pf = 0.0001

    argument = (f_sf * f_pr) / f_pf

    return max(argument, 0.0)


def sigma_deg(f_sf, f_pr, f_pf):
    argument = sigma_argument(
        f_sf,
        f_pr,
        f_pf
    )

    sigma_rad = math.asin(
        math.sqrt(
            min(argument, 1.0)
        )
    )

    return math.degrees(sigma_rad)


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
        f_pf = factors_pf[category]["factor"]
        f_sf = factors_sf[category]["factor"]
        f_pr = factors_pr[category]["factor"]

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

        raw_scores[category] = weighted_score

    total_score = sum(raw_scores.values())
    results = {}

    if total_score <= 0:
        for category in active_categories:
            results[category] = {
                "sigma": 0.0,
                "weight_share": 0.0
            }

        return results, 0.0

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
                math.sqrt(scaled_argument)
            )
        )

        results[category] = {
            "sigma": sigma,
            "weight_share": share
        }

    return results, total_score


def calculate_energy(sigma):
    initial_energy = 2500.0

    remaining_energy = (
        initial_energy
        - (initial_energy * sigma / 90.0)
    )

    efficiency = (
        remaining_energy / initial_energy
    ) * 100.0

    energy_loss = (
        initial_energy
        - remaining_energy
    )

    return remaining_energy, efficiency, energy_loss


# ============================================================
# 9. MAIN STREAMLIT APPLICATION
# ============================================================

def main():
    with st.sidebar:
        st.markdown("## ⚙️ Settings")

        if st.button(
            "🔄 Reset session",
            use_container_width=True
        ):
            reset_app()

        st.divider()
        st.markdown("### 🤖 AI classification (Google)")

        classification_mode = st.radio(
            "Classification method",
            [
                "AI model (Gemini / Gemma)",
                "Dictionary (offline, without an API call)"
            ]
        )

        api_key = None
        model_name = None
        batch_size = 15

        if classification_mode.startswith("AI"):
            api_key = st.text_input(
                "Google AI API key",
                type="password",
                help="Enter your Google AI API key."
            )

            model_name = st.selectbox(
                "Model",
                AVAILABLE_MODELS,
                index=0
            )

            batch_size = st.slider(
                "Batch size (rows per API call)",
                5,
                40,
                15
            )

        st.divider()
        st.markdown("### 🧭 Scientific units to include")

        included_shorts = st.multiselect(
            "Included units",
            list(CATEGORY_SHORT.values()),
            default=list(CATEGORY_SHORT.values())
        )

        active_categories = [
            SHORT_TO_FULL[short_name]
            for short_name in included_shorts
        ] or list(CATEGORIES_MAP.keys())

        st.divider()

        n_input = st.number_input(
            "Number of respondents (N)",
            min_value=1,
            value=210
        )

        is_summary = st.checkbox(
            "The file contains a summary",
            value=True
        )

        st.divider()

        weighting_label = st.radio(
            "Weighting within each unit",
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

        chart_mode = st.radio(
            "Distribution chart",
            [
                "Bar chart",
                "Treemap",
                "Both"
            ]
        )

        st.divider()

        uploaded_file = st.file_uploader(
            "📁 Upload data",
            type=[
                "txt",
                "csv",
                "xlsx"
            ]
        )

    st.markdown(
        "# 📊 Petrič Stress Analysis Pro"
    )

    st.caption(
        "Classification with Google Gemini/Gemma models · "
        "Five scientific units "
        "(Social = social + partial social)"
    )

    if not uploaded_file:
        st.info(
            "📁 Upload a file to begin the analysis.",
            icon="ℹ️"
        )
        return

    if classification_mode.startswith("AI"):
        if not api_key:
            st.warning(
                "⚠️ Enter your Google AI API key in the sidebar."
            )
            return

        if model_name == AVAILABLE_MODELS[0]:
            st.warning(
                "⚠️ Select a model in the sidebar."
            )
            return

    try:
        if uploaded_file.name.endswith(".xlsx"):
            dataframe = pd.read_excel(
                uploaded_file
            )

        elif uploaded_file.name.endswith(".txt"):
            dataframe = pd.read_csv(
                uploaded_file,
                sep="\t",
                engine="python",
                on_bad_lines="skip"
            )

        else:
            dataframe = pd.read_csv(
                uploaded_file,
                engine="python",
                on_bad_lines="skip"
            )

    except Exception as error:
        st.error(
            f"Error while reading the file: {error}"
        )
        return

    if dataframe.empty:
        st.error(
            "The uploaded file is empty."
        )
        return

    target_columns = dataframe.columns.tolist()

    with st.sidebar:
        st.markdown("### 🧩 Data columns")

        col_pf = st.selectbox(
            "Positive factors (PF)",
            target_columns,
            index=0
        )

        col_sf = st.selectbox(
            "Stress factors (SF)",
            target_columns,
            index=min(
                1,
                len(target_columns) - 1
            )
        )

        col_pr = st.selectbox(
            "Suggestions (PR)",
            target_columns,
            index=min(
                2,
                len(target_columns) - 1
            )
        )

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    analysis = {}

    if classification_mode.startswith("AI"):
        client = get_client(api_key)

        classification_jobs = [
            (
                "PF",
                col_pf,
                "🔵 Classifying positive factors..."
            ),
            (
                "SF",
                col_sf,
                "🔴 Classifying stress factors..."
            ),
            (
                "PR",
                col_pr,
                "🟢 Classifying suggestions..."
            )
        ]

        for role, column, progress_label in classification_jobs:
            classified, per_row = run_ai_classification(
                client=client,
                model_name=model_name,
                dataframe=dataframe,
                column=column,
                allowed_short_names=included_shorts,
                batch_size=batch_size,
                progress_label=progress_label
            )

            analysis[role] = {
                "classified": classified,
                "per_row": per_row,
                "column_name": column
            }

    else:
        classification_jobs = [
            ("PF", col_pf),
            ("SF", col_sf),
            ("PR", col_pr)
        ]

        for role, column in classification_jobs:
            classified, per_row = run_offline_classification(
                dataframe=dataframe,
                column=column,
                allowed_short_names=included_shorts
            )

            analysis[role] = {
                "classified": classified,
                "per_row": per_row,
                "column_name": column
            }

    # --------------------------------------------------------
    # GLOBAL CALCULATIONS
    # --------------------------------------------------------

    f_pf_aggregate, _, _ = calculate_fo_real_aggregate(
        analysis["PF"]["classified"],
        n_input
    )

    f_sf_aggregate, _, _ = calculate_fo_real_aggregate(
        analysis["SF"]["classified"],
        n_input
    )

    f_pr_aggregate, _, _ = calculate_fo_real_aggregate(
        analysis["PR"]["classified"],
        n_input
    )

    if is_summary:
        f_pr_aggregate = min(
            f_pr_aggregate,
            f_sf_aggregate * 1.5
        )

    sigma_total = sigma_deg(
        f_sf_aggregate,
        f_pr_aggregate,
        f_pf_aggregate
    )

    _, efficiency, energy_loss = calculate_energy(
        sigma_total
    )

    # --------------------------------------------------------
    # OVERALL RESULTS
    # --------------------------------------------------------

    st.markdown("## 🎯 Overall results")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)

    metric_1.metric(
        "Stress intensity",
        f"{sigma_total:.2f} °S",
        rate_sigma(sigma_total)
    )

    metric_2.metric(
        "Efficiency",
        f"{efficiency:.1f} %"
    )

    metric_3.metric(
        "Energy loss",
        f"{energy_loss:.0f} Kcal"
    )

    metric_4.metric(
        "Sample size (N)",
        n_input
    )

    st.progress(
        min(sigma_total / 90.0, 1.0)
    )

    # --------------------------------------------------------
    # CATEGORY ANALYSIS
    # --------------------------------------------------------

    st.divider()

    factors_pf = compute_category_factors(
        classified=analysis["PF"]["classified"],
        n_override=n_input,
        active_categories=active_categories,
        weighting_mode=weighting_mode
    )

    factors_sf = compute_category_factors(
        classified=analysis["SF"]["classified"],
        n_override=n_input,
        active_categories=active_categories,
        weighting_mode=weighting_mode
    )

    factors_pr = compute_category_factors(
        classified=analysis["PR"]["classified"],
        n_override=n_input,
        active_categories=active_categories,
        weighting_mode=weighting_mode
    )

    total_sigma_argument = min(
        sigma_argument(
            f_sf_aggregate,
            f_pr_aggregate,
            f_pf_aggregate
        ),
        1.0
    )

    category_sigmas, _ = compute_category_sigmas(
        factors_sf=factors_sf,
        factors_pf=factors_pf,
        factors_pr=factors_pr,
        sigma_total_argument=total_sigma_argument,
        is_summary=is_summary,
        active_categories=active_categories
    )

    result_rows = []

    for category, result in category_sigmas.items():
        result_rows.append({
            "Unit": CATEGORY_SHORT[category],
            "Sigma (°S)": round(
                result["sigma"],
                2
            ),
            "Share (%)": round(
                result["weight_share"] * 100,
                1
            ),
            "Rating": rate_sigma(
                result["sigma"]
            )
        })

    result_df = pd.DataFrame(
        result_rows
    ).sort_values(
        by="Sigma (°S)",
        ascending=False
    )

    # --------------------------------------------------------
    # DISTRIBUTION BY SCIENTIFIC UNIT
    # --------------------------------------------------------

    st.markdown(
        "### Distribution by scientific unit"
    )

    left_column, right_column = st.columns(2)

    with left_column:
        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True
        )

    with right_column:
        if chart_mode in ("Bar chart", "Both"):
            st.plotly_chart(
                px.bar(
                    result_df,
                    x="Unit",
                    y="Sigma (°S)",
                    color="Sigma (°S)",
                    color_continuous_scale="Reds",
                    height=300
                ),
                use_container_width=True
            )

        if chart_mode in ("Treemap", "Both"):
            st.plotly_chart(
                px.treemap(
                    result_df,
                    path=["Unit"],
                    values="Sigma (°S)",
                    color="Sigma (°S)",
                    color_continuous_scale="RdYlGn_r",
                    height=350
                ),
                use_container_width=True
            )

    # --------------------------------------------------------
    # TREEMAP: PF / SF / PR
    # --------------------------------------------------------

    st.markdown(
        "### 🗺️ Treemap: all phrases by role and scientific unit"
    )

    tree_rows = []

    role_labels = {
        "PF": "Positive factors",
        "SF": "Stress factors",
        "PR": "Suggestions"
    }

    for role, role_label in role_labels.items():
        frequency = Counter(
            category
            for _, category
            in analysis[role]["classified"]
        )

        for category, count in frequency.items():
            tree_rows.append({
                "Role": role_label,
                "Scientific unit": CATEGORY_SHORT[category],
                "Frequency": count
            })

    if tree_rows:
        tree_df = pd.DataFrame(tree_rows)

        st.plotly_chart(
            px.treemap(
                tree_df,
                path=["Role", "Scientific unit"],
                values="Frequency",
                color="Frequency",
                color_continuous_scale="Turbo",
                height=450
            ),
            use_container_width=True
        )

    else:
        st.caption(
            "There are no classified expressions "
            "available for the treemap."
        )

    # --------------------------------------------------------
    # QUALITATIVE CLASSIFICATION DETAILS
    # --------------------------------------------------------

    with st.expander(
        "🔍 Detailed word and phrase classification"
    ):
        positive_tab, stress_tab, suggestions_tab = st.tabs([
            "🟢 Positive factors",
            "🔴 Stress factors",
            "🔵 Suggestions"
        ])

        for tab, role in zip(
            [positive_tab, stress_tab, suggestions_tab],
            ["PF", "SF", "PR"]
        ):
            with tab:
                frequency = Counter(
                    category
                    for _, category
                    in analysis[role]["classified"]
                )

                frequency_table = pd.DataFrame([
                    {
                        "Scientific unit": CATEGORY_SHORT.get(
                            category,
                            category
                        ),
                        "Frequency": count
                    }
                    for category, count
                    in frequency.items()
                ])

                st.table(
                    frequency_table
                )

                st.markdown(
                    "**Examples of classified phrases:**"
                )

                sample = analysis[role]["classified"][:40]

                if sample:
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "Phrase": phrase,
                                "Scientific unit": CATEGORY_SHORT[category]
                            }
                            for phrase, category in sample
