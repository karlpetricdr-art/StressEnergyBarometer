import streamlit as st
import pandas as pd
import re
import math
import json
import time
from collections import Counter, defaultdict
from typing import List, Literal, Optional

import plotly.express as px
import plotly.graph_objects as go

from pydantic import BaseModel
from google import genai
from google.genai import types


# ============================================================
# 1. NASTAVITVE STRANI
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

st.markdown("""
<style>
.main { background-color: #f7f9fc; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
h1 { font-weight: 800; letter-spacing: -0.5px; }
h2, h3 { font-weight: 700; }
.metric-card {
    background: white; border-radius: 16px; padding: 20px;
    border: 1px solid #e5e9f0; box-shadow: 0 4px 14px rgba(0,0,0,0.05);
    min-height: 145px;
}
.small-muted { color: #64748b; font-size: 0.82rem; }
.stress-high { color: #dc2626; font-weight: 800; }
.stress-medium { color: #ea580c; font-weight: 700; }
.stress-low { color: #16a34a; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. STOPWORDS (za slovarski / offline način in čiščenje)
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
    "proti", "kljub", "zaradi", "namesto", "razen", "okoli", "okrog", "tem",
    "the", "and", "to", "of", "a", "is", "it", "with", "some",
    "more", "being", "able", "use", "make", "nice", "your", "this",
    "that", "from", "for", "are", "was", "were"
}


# ============================================================
# 4. ZNANSTVENA KLASIFIKACIJA (Petrič, 2025)
#
# 5 združenih enot: partial-social + social = "Social unit"
# (izbrana struktura, skupaj s strukturnim nagibom pri Social,
# ker odraža sistemsko/socialno propagacijo stresorjev).
# ============================================================

CATEGORY_SHORT = {
    "Attentive (physical) unit": "Attentive",
    "Performance unit": "Performance",
    "Individual Psychological unit": "Psychological",
    "Social unit": "Social",
    "Health biological unit": "Health"
}
SHORT_TO_FULL = {v: k for k, v in CATEGORY_SHORT.items()}

# Definicije enot za AI klasifikacijo - lastna parafraza vsebine članka,
# ne dobesedni navedki.
CATEGORY_DEFINITIONS = {
    "Attentive (physical) unit": (
        "Physical/sensory environment: noise, lighting, temperature, air, "
        "ergonomics, order and aesthetics of the space, odors, colors."
    ),
    "Performance unit": (
        "Factors related to performing tasks: deadlines, workload, "
        "administrative procedures, information availability, training, "
        "efficiency of tools/processes, physical activity when used for recovery."
    ),
    "Individual Psychological unit": (
        "Internal subjective emotional/psychological states: fear, anxiety, "
        "self-confidence, calm, feelings, personal meaning, values, "
        "inner relaxation, self-image, psychological well-being."
    ),
    "Social unit": (
        "Interpersonal, organizational and status factors: relationships with colleagues, "
        "supervisors, family and friends; communication, conflicts, bullying, "
        "teamwork, organizational climate, hierarchy, plus status, "
        "fairness, recognition, pay, job security and economic "
        "factors."
    ),
    "Health biological unit": (
        "Physical health and biological factors: illness, fatigue, sleep, "
        "hygiene, nutrition, physiological condition, exhaustion."
    ),
}

# Star slovar za OFFLINE (fallback) način klasifikacije brez AI modela.
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
        "odnos", "odnosih", "odnosov", "sodelav", "sodelovanje", "sodelov",
        "šef", "vodstv", "nadrejen", "vodja", "direktor", "družin",
        "family", "prijatel", "friends", "friend", "komunik", "pogovor",
        "talk", "prepir", "konflikt", "conflict", "mobing", "mobbing",
        "šikan", "harass", "harassment", "bully", "bullying", "zahrbt",
        "vzvišen", "nesram", "aroganc", "egoiz", "neiskren", "rival",
        "rivalstvo", "polit", "hierarh", "timsko", "team", "teamwork",
        "druženj", "uporabnik", "osebj", "človek", "zaupan", "trust",
        "support", "podpor", "klima", "vzdušje", "pripadnost", "ignor",
        "nerazum", "posluš", "organizac", "organizaciji", "organizacijo",
        "sestank", "meeting", "meetings", "management", "leader",
        "leadership", "manager", "plač", "dohod", "denar", "finanč",
        "nagrad", "status", "priznan", "revšč", "standar", "nepravič",
        "nestimul", "krivic", "dostojen", "zaposlit", "služb", "karier",
        "napredov", "varnost", "staž", "benefic", "ekonom", "proračun",
        "pokojnin", "sredstv", "zamudn", "opomin", "kazn", "plačev",
        "plačilo", "money", "salary", "financial", "budget", "stability",
        "znesek", "družb", "law", "zakon", "orož", "weapon", "alcohol",
        "economic", "level", "standard", "overcrowding", "crowding",
        "injustice", "punishment", "reward", "recognition"
    ],
    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "spanj", "utrujen", "izčrpan",
        "higien", "čistoč", "sleep", "rest", "dihanje", "izčrpanost",
        "utrujenost", "zdravje", "bolečina", "virus", "infekcij",
        "higiena", "prehran", "diet", "biološ", "fiziolo", "telo",
        "utrujena", "spanja", "telesno", "exhaustion"
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
    (15.04, "Zelo nizka"),
    (30.04, "Nizka"),
    (45.04, "Srednja"),
    (60.04, "Višja"),
    (75.04, "Visoka"),
    (90.01, "Zelo visoka")
]


def rate_sigma(sigma):
    for threshold, label in RATING_SCALE:
        if sigma <= threshold:
            return label
    return "Zelo visoka"


# ============================================================
# 5. GOOGLE MODELI (Gemini / Gemma) - na voljo za izbiro
#
# Uporabnik VSAKIČ izbere model sam - ni vsiljenega privzetega.
# ============================================================

AVAILABLE_MODELS = [
    "-- izberite model --",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
]


# ============================================================
# 6. STRUKTURIRANI IZHOD (pydantic sheme za AI klasifikacijo)
# ============================================================

def build_classification_models(allowed_short_names):
    """Dinamično zgradi pydantic sheme, ki dovolijo samo trenutno
    vključene kratke oznake enot (+ 'None' za nerazvrščeno)."""
    allowed = tuple(allowed_short_names) + ("None",)

    class ClassifiedItem(BaseModel):
        phrase: str
        category: Literal[allowed]

    class RowClassification(BaseModel):
        row_id: int
        items: List[ClassifiedItem]

    class BatchClassification(BaseModel):
        rows: List[RowClassification]

    return ClassifiedItem, RowClassification, BatchClassification


def build_system_instruction(allowed_short_names, role):
    defs_text = "\n".join(
        f"- {CATEGORY_SHORT[full]}: {CATEGORY_DEFINITIONS[full]}"
        for full in CATEGORIES_MAP.keys()
        if CATEGORY_SHORT[full] in allowed_short_names
    )
    role_text = {
        "PF": "You are classifying POSITIVE FACTORS: protective, beneficial, supportive or restorative conditions.",
        "SF": "You are classifying STRESS FACTORS: problems, burdens, demands, threats, deficiencies, conflicts or conditions that increase stress.",
        "PR": "You are classifying PROPOSALS: suggestions, requested changes, solutions or actions intended to improve the situation. Classify the actual target of the proposal, not generic words such as 'improve' or 'better'.",
    }[role]
    return f"""You are an expert in classifying survey responses about psychosocial stress in public-sector employees using the Petrič methodology (2025).

CURRENT ROLE: {role}
{role_text}

For every row, identify ALL meaningful words or phrases expressing the current role. A row may contain multiple items. Each item must be assigned to EXACTLY ONE scientific unit:

{defs_text}

Important classification rules:
1. Classify by MEANING AND CONTEXT, not by isolated keywords.
2. Keep meaningful multi-word expressions together when they form one concept, e.g. 'delovnem mestu'.
3. Do not return grammatical filler or stop words such as 'več', 'the', 'and', 'to', etc.
4. A generic word must not be classified when it has no meaningful stress-related context.
5. Words such as 'delo'/'work' normally belong to Performance unit only when they refer to performing tasks, workload, duties or work processes.
6. Organizational obligations, employment conditions, status, recognition, pay, job security and organizational social conditions belong to Social unit when that is the meaning in context.
7. 'Environment' belongs to Attentive (physical) unit only when it clearly means the physical/sensory surroundings. Organizational or social environment belongs to Social unit.
8. For proposals, classify the actual target/problem being proposed for change, not merely the improvement verb.
9. For positive factors, classify the beneficial condition itself; do not classify a merely negated problem as positive.
10. Return phrases in the original language; do not translate them.
11. If an expression does not fit any active unit or is too vague, use 'None'.
12. Be comprehensive but precise: prefer meaningful phrases over noisy single words."""


@st.cache_resource(show_spinner=False)
def get_client(api_key):
    return genai.Client(api_key=api_key)


def classify_batch_with_ai(client, model_name, rows, allowed_short_names, role,
                            row_class_model, batch_class_model, max_retries=3):
    """rows: list of (row_id, text). Vrne dict row_id -> [(phrase, category_full), ...]"""
    system_instruction = build_system_instruction(allowed_short_names, role)
    payload = "\n".join(f"[{rid}] {text}" for rid, text in rows)

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
            raw = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
            data = json.loads(raw)

            result = defaultdict(list)
            for row in data.get("rows", []):
                rid = row["row_id"]
                for item in row.get("items", []):
                    cat_short = item.get("category")
                    phrase = item.get("phrase", "").strip()
                    phrase = re.sub(r"\s+", " ", phrase).strip(" ,.;:-")
                    if not phrase or cat_short == "None" or cat_short not in SHORT_TO_FULL:
                        continue
                    phrase_words = phrase.split()
                    if len(phrase_words) == 1 and phrase.lower() in SLO_STOPWORDS:
                        continue
                    if len(phrase_words) > 1 and all(w.lower() in SLO_STOPWORDS for w in phrase_words):
                        continue
                    result[rid].append((phrase.lower(), SHORT_TO_FULL[cat_short]))
            return result
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    st.warning(f"Napaka pri klicu AI modela po {max_retries} poskusih: {last_err}")
    return {}


def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def run_ai_classification(client, model_name, df, col, allowed_short_names,
                           batch_size, progress_label):
    row_class_model, _, batch_class_model = build_classification_models(allowed_short_names)

    rows_text = [(i, str(v)) for i, v in df[col].dropna().items()]
    classified = []
    per_row_categories = []
    row_id_to_idx = {}

    progress = st.progress(0.0, text=progress_label)
    batches = list(chunk_list(rows_text, batch_size))
    for b_i, batch in enumerate(batches):
        result = classify_batch_with_ai(
            client, model_name, batch, allowed_short_names, role,
            row_class_model, batch_class_model
        )
        for rid, _ in batch:
            items = result.get(rid, [])
            classified.extend(items)
            per_row_categories.append([c for _, c in items])
        progress.progress((b_i + 1) / max(len(batches), 1), text=progress_label)
    progress.empty()

    return classified, per_row_categories


# ============================================================
# 7. OFFLINE (slovarski) NAČIN - fallback brez AI
# ============================================================

def clean_and_tokenize(text):
    if not isinstance(text, str):
        return []
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]


def classify_word_single(word, allowed_short_names):
    priority_order = [
        "Social unit", "Performance unit", "Individual Psychological unit",
        "Health biological unit", "Attentive (physical) unit"
    ]
    for cat in priority_order:
        if CATEGORY_SHORT[cat] not in allowed_short_names:
            continue
        for koren in CATEGORIES_MAP[cat]:
            if re.search(rf"\b{re.escape(koren)}\w*\b", word):
                return cat
    return None


def run_offline_classification(df, col, allowed_short_names):
    classified = []
    per_row_categories = []
    for row in df[col].dropna():
        row_cats = []
        for kw in clean_and_tokenize(row):
            cat = classify_word_single(kw, allowed_short_names)
            if cat:
                classified.append((kw, cat))
                row_cats.append(cat)
        per_row_categories.append(row_cats)
    return classified, per_row_categories


# ============================================================
# 8. MATEMATIČNA LOGIKA (PETRIČEVA METODA) - nespremenjeno
# ============================================================

def calculate_fo_real_aggregate(classified, n_override):
    all_words = [w for w, _ in classified]
    fo = len(all_words)
    fr = len(set(all_words))
    if fr == 0 or n_override == 0:
        return 0.0001, fo, fr
    rho_o = fo / n_override
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10.0
    return fo_real, fo, fr


def compute_category_factors(classified, n_override, active_categories, weighting_mode="volume"):
    words_by_cat = defaultdict(list)
    for word, category in classified:
        words_by_cat[category].append(word)

    result = {}
    for category in active_categories:
        words = words_by_cat.get(category, [])
        fE = len(words)
        frE = len(set(words))
        if weighting_mode == "concentration":
            CE = fE / frE if frE > 0 else 0.0001
        else:
            CE = 1.0
        rho = fE / n_override if n_override else 0.0
        F = (CE * rho) / 10.0
        result[category] = {"fE": fE, "frE": frE, "CE": CE, "rho": rho, "F": F}
    return result


def sigma_argument(f_sf, f_pr, f_pf):
    if f_pf <= 0:
        f_pf = 0.0001
    argument = (f_sf * f_pr) / f_pf
    return max(argument, 0.0)


def sigma_deg(f_sf, f_pr, f_pf):
    arg = sigma_argument(f_sf, f_pr, f_pf)
    sigma_rad = math.asin(math.sqrt(min(arg, 1.0)))
    return math.degrees(sigma_rad)


def compute_category_sigmas(factors_sf, factors_pf, factors_pr,
                             sigma_total_argument, is_summary, active_categories):
    raw_scores = {}
    for category in active_categories:
        f_pf = factors_pf[category]["F"]
        f_sf = factors_sf[category]["F"]
        f_pr = factors_pr[category]["F"]

        if is_summary and f_sf > 0:
            f_pr = min(f_pr, f_sf * 1.5)

        argument = sigma_argument(f_sf, f_pr, f_pf)
        bonus = 1.15 if category == "Social unit" else 1.0
        weighted_score = argument * SLOPE_WEIGHTS[category] * bonus
        raw_scores[category] = weighted_score

    total_score = sum(raw_scores.values())
    results = {}

    if total_score <= 0:
        for category in active_categories:
            results[category] = {"sigma": 0.0, "weight_share": 0.0}
        return results, 0.0

    for category in active_categories:
        share = raw_scores[category] / total_score
        scaled_argument = min(sigma_total_argument * share, 1.0)
        sigma = math.degrees(math.asin(math.sqrt(scaled_argument)))
        results[category] = {"sigma": sigma, "weight_share": share}

    return results, total_score


def calculate_energy(sigma):
    W_I = 2500.0
    W_EU = W_I - (W_I * sigma / 90.0)
    eta = (W_EU / W_I) * 100.0
    loss = W_I - W_EU
    return W_EU, eta, loss


# ============================================================
# 9. ADVANCED VISUALIZATIONS
# ============================================================

def build_sankey(analysis):
    role_labels = {"PF": "Positive factors", "SF": "Stress factors", "PR": "Proposals"}
    counts = Counter()
    for role, role_label in role_labels.items():
        for _, cat in analysis[role]["classified"]:
            counts[(role_label, CATEGORY_SHORT[cat])] += 1
    if not counts:
        return None
    unit_labels = [CATEGORY_SHORT[c] for c in CATEGORIES_MAP]
    labels = list(dict.fromkeys(list(role_labels.values()) + unit_labels))
    idx = {x: i for i, x in enumerate(labels)}
    sources, targets, values = [], [], []
    for (role_label, unit), count in counts.items():
        sources.append(idx[role_label]); targets.append(idx[unit]); values.append(count)
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, pad=18, thickness=20),
        link=dict(source=sources, target=targets, value=values)
    ))
    fig.update_layout(title="Sankey diagram: Role → Unit", height=480,
                      margin=dict(l=10, r=10, t=60, b=10))
    return fig


def build_radar(res_df):
    if res_df.empty:
        return None
    theta = res_df["Enota"].tolist()
    values = res_df["σ (°S)"].astype(float).tolist()
    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=theta + [theta[0]],
        fill="toself",
        name="Stress power"
    ))
    fig.update_layout(
        title="Radar profile: stress power by unit",
        polar=dict(radialaxis=dict(visible=True, range=[0, 90])),
        showlegend=False, height=500,
        margin=dict(l=40, r=40, t=70, b=20)
    )
    return fig


def build_cooccurrence_network(analysis):
    # Each respondent row is treated as one observation. Units appearing
    # anywhere across PF/SF/PR in that row form co-occurrence edges.
    role_order = ["PF", "SF", "PR"]
    rows = {role: analysis[role]["per_row"] for role in role_order}
    max_len = max((len(v) for v in rows.values()), default=0)
    edge_counts = Counter()
    node_counts = Counter()

    for i in range(max_len):
        units = set()
        for role in role_order:
            if i < len(rows[role]):
                units.update(c for c in rows[role][i] if c in CATEGORY_SHORT)
        short_units = sorted(CATEGORY_SHORT[c] for c in units)
        node_counts.update(short_units)
        for a_i in range(len(short_units)):
            for b_i in range(a_i + 1, len(short_units)):
                edge_counts[(short_units[a_i], short_units[b_i])] += 1

    if not edge_counts:
        return None

    nodes = sorted(node_counts)
    positions = {}
    n = len(nodes)
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / max(n, 1)
        positions[node] = (math.cos(angle), math.sin(angle))

    edge_x, edge_y = [], []
    for (a, b), weight in edge_counts.items():
        xa, ya = positions[a]; xb, yb = positions[b]
        edge_x += [xa, xb, None]; edge_y += [ya, yb, None]

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
                            line=dict(width=1.5), hoverinfo="none")
    node_trace = go.Scatter(
        x=[positions[n][0] for n in nodes],
        y=[positions[n][1] for n in nodes],
        mode="markers+text",
        text=nodes, textposition="middle center",
        marker=dict(size=[30 + 8 * math.sqrt(node_counts[n]) for n in nodes],
                    line=dict(width=1)),
        customdata=[node_counts[n] for n in nodes],
        hovertemplate="<b>%{text}</b><br>Rows containing unit: %{customdata}<extra></extra>"
    )
    fig = go.Figure([edge_trace, node_trace])
    fig.update_layout(
        title="Co-occurrence network: units appearing in the same responses",
        showlegend=False, height=560,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=60, b=10), plot_bgcolor="white"
    )
    return fig


# ============================================================
# 9. GLAVNA STREAMLIT APLIKACIJA (UI)
# ============================================================

def main():
    with st.sidebar:
        st.markdown("## ⚙️ Settings")

        if st.button("🔄 Reset session", use_container_width=True):
            reset_app()

        st.divider()
        st.markdown("### 🤖 AI classification (Google)")
        classification_mode = st.radio(
            "Classification mode",
            ["AI model (Gemini / Gemma)", "Dictionary (offline, no API call)"]
        )

        api_key = None
        model_name = None
        batch_size = 15

        if classification_mode.startswith("AI"):
            api_key = st.text_input(
                "Google AI API key", type="password",
                help="Brezplačen ključ dobiš na https://aistudio.google.com/apikey"
            )
            model_name = st.selectbox("Model", AVAILABLE_MODELS, index=0)
            batch_size = st.slider("Velikost paketa (vrstic na klic)", 5, 40, 15)

        st.divider()
        st.markdown("### 🧭 Scientific units to include")
        included_shorts = st.multiselect(
            "Included units",
            list(CATEGORY_SHORT.values()),
            default=list(CATEGORY_SHORT.values())
        )
        active_categories = [SHORT_TO_FULL[s] for s in included_shorts] or list(CATEGORIES_MAP.keys())

        st.divider()
        n_input = st.number_input("Number of respondents (N)", min_value=1, value=210)
        is_summary = st.checkbox("File contains a SUMMARY", value=True)

        st.divider()
        weighting_label = st.radio(
            "Within-unit weighting",
            ["Volume (frequency)", "Concentration (repeatability)"]
        )
        weighting_mode = "volume" if "Volumen" in weighting_label else "concentration"

        st.divider()
        chart_mode = st.radio("Distribution display", ["Bar chart", "Treemap (colored)", "Both"])

        st.divider()
        uploaded_file = st.file_uploader("📁 Upload data", type=["txt", "csv", "xlsx"])

    st.markdown("# 📊 Petrič Stress Analysis Pro")
    st.caption("Klasifikacija z Google Gemini/Gemma modeli · 5 znanstvenih enot (Social = social + partial social)")

    if not uploaded_file:
        st.info("📁 Upload a file to begin the analysis.", icon="ℹ️")
        return

    if classification_mode.startswith("AI"):
        if not api_key:
            st.warning("⚠️ Vnesite Google AI API key v stranski vrstici, da uporabite AI klasifikacijo.")
            return
        if model_name == AVAILABLE_MODELS[0]:
            st.warning("⚠️ Select a model in the sidebar.")
            return

    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".txt"):
            df = pd.read_csv(uploaded_file, sep="\t", engine="python", on_bad_lines="skip")
        else:
            df = pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"File read error: {e}")
        return

    target_cols = df.columns.tolist()

    with st.sidebar:
        st.markdown("### 🧩 Columns")
        col_pf = st.selectbox("Positive factors (PF)", target_cols, index=0)
        col_sf = st.selectbox("Stress factors (SF)", target_cols, index=min(1, len(target_cols) - 1))
        col_pr = st.selectbox("Proposals (PR)", target_cols, index=min(2, len(target_cols) - 1))

    # ---------------- KLASIFIKACIJA ----------------
    analysis = {}

    if classification_mode.startswith("AI"):
        client = get_client(api_key)
        for role, col, label in [
            ("PF", col_pf, "🔵 Classifying positive factors ..."),
            ("SF", col_sf, "🔴 Classifying stress factors ..."),
            ("PR", col_pr, "🟢 Classifying proposals ...")
        ]:
            cls, per_row = run_ai_classification(
                client, model_name, df, col, included_shorts, role,
                batch_size, label
            )
            analysis[role] = {"classified": cls, "per_row": per_row, "col_name": col}
    else:
        for role, col in [("PF", col_pf), ("SF", col_sf), ("PR", col_pr)]:
            cls, per_row = run_offline_classification(df, col, included_shorts)
            analysis[role] = {"classified": cls, "per_row": per_row, "col_name": col}

    # ---------------- GLOBALNI IZRAČUN ----------------
    f_pf_agg, _, _ = calculate_fo_real_aggregate(analysis["PF"]["classified"], n_input)
    f_sf_agg, _, _ = calculate_fo_real_aggregate(analysis["SF"]["classified"], n_input)
    f_pr_agg, _, _ = calculate_fo_real_aggregate(analysis["PR"]["classified"], n_input)

    if is_summary:
        f_pr_agg = min(f_pr_agg, f_sf_agg * 1.5)

    sigma_total = sigma_deg(f_sf_agg, f_pr_agg, f_pf_agg)
    W_EU, eta, loss = calculate_energy(sigma_total)

    st.markdown("## 🎯 Overall results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stress power", f"{sigma_total:.2f} °S", rate_sigma(sigma_total))
    m2.metric("Efficiency", f"{eta:.1f} %")
    m3.metric("Energy loss", f"{loss:.0f} Kcal")
    m4.metric("Sample (N)", n_input)
    st.progress(min(sigma_total / 90.0, 1.0))

    # ---------------- RAZČLENITEV PO ENOTAH ----------------
    st.divider()
    f_pf_cat = compute_category_factors(analysis["PF"]["classified"], n_input, active_categories, weighting_mode)
    f_sf_cat = compute_category_factors(analysis["SF"]["classified"], n_input, active_categories, weighting_mode)
    f_pr_cat = compute_category_factors(analysis["PR"]["classified"], n_input, active_categories, weighting_mode)

    sig_total_arg = min(sigma_argument(f_sf_agg, f_pr_agg, f_pf_agg), 1.0)
    cat_sigmas, _ = compute_category_sigmas(
        f_sf_cat, f_pf_cat, f_pr_cat, sig_total_arg, is_summary, active_categories
    )

    rows = []
    for cat, data in cat_sigmas.items():
        rows.append({
            "Enota": CATEGORY_SHORT[cat],
            "σ (°S)": round(data["sigma"], 2),
            "Share (%)": round(data["weight_share"] * 100, 1),
            "Rating": rate_sigma(data["sigma"])
        })
    res_df = pd.DataFrame(rows).sort_values(by="σ (°S)", ascending=False)

    st.markdown("### Stress power by scientific unit")
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.dataframe(res_df, use_container_width=True, hide_index=True)

    with col_right:
        if chart_mode in ("Bar chart", "Both"):
            st.plotly_chart(
                px.bar(res_df, x="Enota", y="σ (°S)", color="σ (°S)",
                       color_continuous_scale="Reds", height=300),
                use_container_width=True
            )
        if chart_mode in ("Treemap (colored)", "Both"):
            st.plotly_chart(
                px.treemap(
                    res_df, path=["Enota"], values="σ (°S)",
                    color="σ (°S)", color_continuous_scale="RdYlGn_r",
                    height=350
                ),
                use_container_width=True
            )

    # ---------------- TREEMAP: PF / SF / PR SKUPAJ ----------------
    st.markdown("### 🗺️ Treemap: all classified phrases by role and unit")
    tree_rows = []
    role_labels = {"PF": "Positive", "SF": "Stress", "PR": "Proposals"}
    for role, label in role_labels.items():
        freq = Counter(c for _, c in analysis[role]["classified"])
        for cat, count in freq.items():
            tree_rows.append({
                "Role": label,
                "Enota": CATEGORY_SHORT[cat],
                "Frequency": count
            })
    if tree_rows:
        tree_df = pd.DataFrame(tree_rows)
        st.plotly_chart(
            px.treemap(
                tree_df, path=["Role", "Enota"], values="Frequency",
                color="Frequency", color_continuous_scale="Turbo", height=450
            ),
            use_container_width=True
        )
    else:
        st.caption("No classified expressions are available for the treemap.")

    # ---------------- ADVANCED VISUALIZATIONS ----------------
    st.divider()
    st.markdown("## 🔬 Advanced structural visualizations")

    sankey_fig = build_sankey(analysis)
    if sankey_fig is not None:
        st.plotly_chart(sankey_fig, use_container_width=True)
        st.caption("Flow volume is the number of classified phrases from each role into each scientific unit.")

    radar_fig = build_radar(res_df)
    if radar_fig is not None:
        st.plotly_chart(radar_fig, use_container_width=True)
        st.caption("The radar profile shows the stress-power profile of the active scientific units.")

    network_fig = build_cooccurrence_network(analysis)
    if network_fig is not None:
        st.plotly_chart(network_fig, use_container_width=True)
        st.caption("Edges connect scientific units that occur together in the same respondent response. Thicker/stronger connections indicate more frequent co-occurrence.")

    # ---------------- QUALITATIVE REVIEW ----------------
    with st.expander("🔍 Classification details"):
        t1, t2, t3 = st.tabs(["🟢 Positive", "🔴 Stress", "🔵 Proposals"])
        for tab, role in zip([t1, t2, t3], ["PF", "SF", "PR"]):
            with tab:
                freq = Counter(c for _, c in analysis[role]["classified"])
                st.table(pd.DataFrame([
                    {"Enota": CATEGORY_SHORT.get(k, k), "Frequency": v}
                    for k, v in freq.items()
                ]))
                st.markdown("****Examples of classified phrases:****")
                sample = analysis[role]["classified"][:40]
                if sample:
                    st.dataframe(
                        pd.DataFrame(
                            [{"Phrase": w, "Enota": CATEGORY_SHORT[c]} for w, c in sample]
                        ),
                        use_container_width=True, hide_index=True
                    )


if __name__ == "__main__":
    main()

