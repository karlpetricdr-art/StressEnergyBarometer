import streamlit as st
import pandas as pd
import re
import math
from collections import Counter


# --- 1. OSNOVNE NASTAVITVE IN SLOGI ---

st.set_page_config(
    page_title="Stress Analysis Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #f7f9fc;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1 {
        color: #19324d;
        font-weight: 700;
    }

    h2, h3 {
        color: #264f73;
    }

    .app-subtitle {
        color: #5c6b73;
        font-size: 1.05rem;
        margin-top: -0.7rem;
        margin-bottom: 1.5rem;
    }

    .info-card {
        padding: 1rem 1.2rem;
        border-radius: 12px;
        background-color: #ffffff;
        border: 1px solid #e1e8ef;
        box-shadow: 0 2px 8px rgba(30, 55, 80, 0.05);
        margin-bottom: 1rem;
    }

    .metric-card {
        padding: 1.2rem;
        border-radius: 14px;
        background: linear-gradient(135deg, #eaf4ff, #ffffff);
        border: 1px solid #cfe3f5;
        text-align: center;
        box-shadow: 0 3px 10px rgba(30, 70, 100, 0.08);
    }

    .metric-title {
        color: #557085;
        font-size: 0.9rem;
        margin-bottom: 0.3rem;
    }

    .metric-value {
        color: #1d557d;
        font-size: 2rem;
        font-weight: 700;
    }

    .footer-note {
        text-align: center;
        color: #7b8790;
        font-size: 0.85rem;
        margin-top: 2rem;
    }

    [data-testid="stSidebar"] {
        background-color: #eef4f8;
    }

    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# --- 2. FUNKCIJA ZA RESET ---

def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# --- 3. DEFINICIJA STOP-WORDS ---

SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi",
    "iz", "za", "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je",
    "bil", "biti", "ali", "bila", "v", "pri", "o", "z", "s", "k", "h", "vse",
    "vsi", "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of",
    "a", "is", "it"
}


# --- 4. KLASIFIKACIJSKI MODEL ---

CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "lightning", "vročina", "mraz",
        "cold", "weather", "vreme", "prostori", "office", "pisarna",
        "ergonomija", "equipment", "oprema", "tišina", "silence", "zrak"
    ],
    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload", "naloge", "tasks",
        "čas", "time", "administration", "birokracija", "birokrat",
        "informacije", "information", "skills", "znanje", "delovni čas",
        "urgency", "hitenje", "naglica", "stiska", "preobremenjenost",
        "neizkušenost", "administrativni"
    ],
    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism", "pozitivno",
        "self-confidence", "samozavest", "emotions", "čustva", "stres",
        "stress", "frustracija", "frustration", "peace", "mir", "negotovost",
        "nervoza", "panika", "nemoč", "skrb", "napetost"
    ],
    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance", "nagrada", "reward",
        "status", "recognition", "priznanje", "poverty", "revščina", "standard",
        "inequality", "nepravičnost", "nestimulativen", "krivica", "dostojen",
        "plačilo", "finančna"
    ],
    "Social unit": [
        "odnosi", "relationships", "mobing", "mobbing", "bullying", "harassment",
        "sodelavci", "colleagues", "šef", "boss", "družina", "family",
        "prijatelji", "friends", "komunikacija", "communication", "prepir",
        "zahrbtnost", "vzvišenost", "nesramnost", "aroganca", "egoizem",
        "podpora"
    ],
    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport", "sports", "exercise",
        "prehrana", "diet", "spanje", "sleep", "utrujenost", "tiredness",
        "joga", "yoga", "meditacija", "meditation", "izčrpanost", "dihanje",
        "sproščanje", "počitek", "dopust"
    ]
}


# --- 5. POMOŽNE FUNKCIJE ---

def clean_and_tokenize(text):
    """Pretvori besedilo v seznam ključnih besed."""
    if not isinstance(text, str):
        return []

    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()

    return [
        word for word in words
        if word not in SLO_STOPWORDS and len(word) > 2
    ]


def classify_keywords(keywords):
    """Ključne besede razvrsti v klasifikacijske enote."""
    found_categories = []

    for word in keywords:
        for category, keyword_list in CATEGORIES_MAP.items():
            if any(keyword.lower() in word for keyword in keyword_list):
                found_categories.append(category)

    return found_categories


def calculate_fo_real(df, column, n_o):
    """Izračuna realni faktor F_o."""
    all_keywords_in_category = []

    for row in df[column].dropna():
        keywords = clean_and_tokenize(row)

        for keyword in keywords:
            for keyword_list in CATEGORIES_MAP.values():
                if any(
                    keyword.startswith(item.lower()[:5])
                    for item in keyword_list
                ):
                    all_keywords_in_category.append(keyword)
                    break

    fo = len(all_keywords_in_category)
    fr = len(set(all_keywords_in_category))

    if fr == 0 or n_o == 0:
        return 0.0001, fo, fr

    rho_o = fo / n_o
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10

    return fo_real, fo, fr


def read_uploaded_file(uploaded_file):
    """Prebere TXT ali CSV datoteko z osnovnim preverjanjem kodiranja."""
    separator = "\t" if uploaded_file.name.lower().endswith(".txt") else ","

    try:
        return pd.read_csv(
            uploaded_file,
            sep=separator,
            encoding="utf-8"
        )
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(
            uploaded_file,
            sep=separator,
            encoding="latin-1"
        )


def create_metric_card(title, value):
    return f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """


# --- 6. GLAVNA APLIKACIJA ---

def main():

    # Glava aplikacije
    st.title("📊 Klasifikacija stresnih dejavnikov")
    st.markdown(
        '<div class="app-subtitle">'
        "Analiza odgovorov respondentov po Petričevi



