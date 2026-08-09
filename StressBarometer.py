import streamlit as st
import pandas as pd
import re
import math
import json
import time
from collections import Counter, defaultdict
from typing import List, Literal, Optional

import plotly.express as px

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
        "Fizično/senzorno okolje: hrup, osvetlitev, temperatura, zrak, "
        "ergonomija, urejenost in estetika prostora, vonjave, barve."
    ),
    "Performance unit": (
        "Dejavniki, povezani z opravljanjem nalog: roki, obremenjenost, "
        "administrativni postopki, dostopnost informacij, usposabljanje, "
        "učinkovitost orodij/procesov, telesna aktivnost v vlogi razbremenitve."
    ),
    "Individual Psychological unit": (
        "Notranja subjektivna čustvena/psihična stanja posameznika: strah, "
        "tesnoba, samozavest, mir, občutki, osebni pomen, vrednote, "
        "notranja sprostitev, samopodoba, duševno počutje."
    ),
    "Social unit": (
        "Medosebni in organizacijski/statusni dejavniki: odnosi s sodelavci, "
        "nadrejenimi, družino, prijatelji; komunikacija, konflikti, mobing, "
        "timsko delo, organizacijska klima, hierarhija, PA TUDI status, "
        "pravičnost, priznanje, plačilo, varnost zaposlitve in ekonomski "
        "dejavniki (ta enota združuje 'social' in 'partial social' iz članka)."
    ),
    "Health biological unit": (
        "Fizično zdravje in biološki dejavniki: bolezen, utrujenost, spanje, "
        "higiena, prehrana, fiziološko stanje, izčrpanost."
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


def build_system_instruction(allowed_short_names, whole_set_mode=False):
    defs_text = "\n".join(
        f"- {CATEGORY_SHORT[full]}: {CATEGORY_DEFINITIONS[full]}"
        for full in CATEGORIES_MAP.keys()
        if CATEGORY_SHORT[full] in allowed_short_names
    )
    cohort_note = ""
    if whole_set_mode:
        cohort_note = """
Vsi vhodni podatki skupaj predstavljajo EN sam vzorec/kohorto (npr. javni
uslužbenci ali drug del družbe) - obravnavaj jih kot eno homogeno množico
mnenj, ne kot ločene posamezne primere. Kljub temu moraš vsako vrstico
obdelati posamično in ohraniti njeno oznako vloge (PF/SF/PR) in row_id, da
je mogoče rezultate nazaj združiti."""
    return f"""Si strokovnjak za klasifikacijo odgovorov v raziskavi o stresu
javnih uslužbencev (metodologija Petrič, 2025). Za vsako vrstico besedila
prepoznaj posamezne smiselne izraze/fraze, ki predstavljajo mnenje, stresor,
pozitiven dejavnik ali predlog (lahko jih je več v eni vrstici, ločenih z
vejicami, podpičji ali "in"). Vsak prepoznan izraz razvrsti v NATANKO ENO od
naslednjih znanstvenih enot:

{defs_text}

Če izraz ne sodi v nobeno od zgornjih enot ali je preveč splošen/nesmiseln,
mu dodeli kategorijo "None". Vrni izraze v izvirnem jeziku besedila (ne
prevajaj). Bodi izčrpen - zajemi vse smiselne izraze v vrstici, ne le
enega. Obdelaj VSE vrstice, ki so ti podane - nobene ne izpusti.
{cohort_note}"""


@st.cache_resource(show_spinner=False)
def get_client(api_key):
    return genai.Client(api_key=api_key)


def classify_batch_with_ai(client, model_name, rows, allowed_short_names,
                            row_class_model, batch_class_model, max_retries=3):
    """rows: list of (row_id, text). Vrne dict row_id -> [(phrase, category_full), ...]"""
    system_instruction = build_system_instruction(allowed_short_names)
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
                    if not phrase or cat_short == "None" or cat_short not in SHORT_TO_FULL:
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


def build_full_classification_model(allowed_short_names):
    """Shema za en sam klic, ki obdela PF+SF+PR skupaj (cel nabor kot ena množica)."""
    allowed = tuple(allowed_short_names) + ("None",)

    class ClassifiedItem(BaseModel):
        phrase: str
        category: Literal[allowed]

    class RowClassification(BaseModel):
        role: Literal["PF", "SF", "PR"]
        row_id: int
        items: List[ClassifiedItem]

    class FullClassification(BaseModel):
        rows: List[RowClassification]

    return FullClassification


def classify_everything_single_call(client, model_name, df, col_pf, col_sf, col_pr,
                                      allowed_short_names, max_output_tokens=32768,
                                      max_retries=1):
    """Obdela CELOTEN nabor podatkov (vse vrstice PF+SF+PR, npr. 200 respondentov)
    v ENEM API klicu, kot eno homogeno množico. Hitreje kot paketno procesiranje.

    Odporno na 400 INVALID_ARGUMENT: poskusi zaporedoma z manj zahtevnimi
    nastavitvami (brez thinking_config, brez strogega response_schema), da
    najde konfiguracijo, ki jo izbrani model dejansko podpira.
    """
    full_model = build_full_classification_model(allowed_short_names)
    system_instruction = build_system_instruction(allowed_short_names, whole_set_mode=True)

    lines = []
    for idx, v in df[col_pf].dropna().items():
        lines.append(f"[PF-{idx}] {v}")
    for idx, v in df[col_sf].dropna().items():
        lines.append(f"[SF-{idx}] {v}")
    for idx, v in df[col_pr].dropna().items():
        lines.append(f"[PR-{idx}] {v}")
    payload = "\n".join(lines)

    schema_json_hint = """
Odgovori IZKLJUČNO z veljavnim JSON objektom (brez ```json ograd, brez
dodatnega besedila) v natanko tej obliki:
{"rows": [{"role": "PF|SF|PR", "row_id": <int>, "items": [{"phrase": "...", "category": "..."}]}]}
"""

    def make_config(use_thinking, use_schema, tokens):
        kwargs = dict(
            system_instruction=system_instruction + (schema_json_hint if not use_schema else ""),
            temperature=0.1,
            max_output_tokens=tokens,
        )
        if use_schema:
            kwargs["response_mime_type"] = "application/json"
            kwargs["response_schema"] = full_model
        else:
            kwargs["response_mime_type"] = "application/json"
        cfg = types.GenerateContentConfig(**kwargs)
        if use_thinking and model_name.startswith("gemini"):
            try:
                cfg.thinking_config = types.ThinkingConfig(thinking_budget=0)
            except Exception:
                pass
        return cfg

    # Zaporedje poskusov od "najhitrejši/najstrožji" do "najbolj kompatibilen"
    attempt_plans = [
        {"use_thinking": True, "use_schema": True, "tokens": max_output_tokens},
        {"use_thinking": False, "use_schema": True, "tokens": max_output_tokens},
        {"use_thinking": False, "use_schema": False, "tokens": max_output_tokens},
        {"use_thinking": False, "use_schema": False, "tokens": min(max_output_tokens, 8192)},
    ]

    errors_log = []
    for plan in attempt_plans:
        for attempt in range(max_retries + 1):
            try:
                config = make_config(plan["use_thinking"], plan["use_schema"], plan["tokens"])
                response = client.models.generate_content(
                    model=model_name, contents=payload, config=config
                )
                raw = response.text
                if raw is None:
                    raise ValueError("Model ni vrnil besedila (morda prekinjen zaradi max_output_tokens).")
                raw = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
                data = json.loads(raw)

                buckets = {
                    "PF": {"classified": [], "per_row": defaultdict(list), "col_name": col_pf},
                    "SF": {"classified": [], "per_row": defaultdict(list), "col_name": col_sf},
                    "PR": {"classified": [], "per_row": defaultdict(list), "col_name": col_pr},
                }
                for row in data.get("rows", []):
                    role = row.get("role")
                    rid = row.get("row_id")
                    if role not in buckets:
                        continue
                    items = []
                    for item in row.get("items", []):
                        cat_short = item.get("category")
                        phrase = str(item.get("phrase", "")).strip()
                        if not phrase or cat_short == "None" or cat_short not in SHORT_TO_FULL:
                            continue
                        items.append((phrase.lower(), SHORT_TO_FULL[cat_short]))
                    buckets[role]["classified"].extend(items)
                    buckets[role]["per_row"][rid] = [c for _, c in items]

                for role in buckets:
                    buckets[role]["per_row"] = list(buckets[role]["per_row"].values())
                return buckets
            except Exception as e:
                errors_log.append(
                    f"[thinking={plan['use_thinking']}, schema={plan['use_schema']}, "
                    f"tokens={plan['tokens']}] {e}"
                )
                time.sleep(1.0)

    st.error(
        "En-klicna obdelava celotnega nabora ni uspela po vseh poskusih. "
        "Preklopi na 'Paketno procesiranje' v stranski vrstici, ali zmanjšaj "
        "'Max izhodnih tokenov'. Podrobnosti napak po poskusih:"
    )
    for line in errors_log:
        st.code(line)
    return None


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
            client, model_name, batch, allowed_short_names,
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
# 9. GLAVNA STREAMLIT APLIKACIJA (UI)
# ============================================================

def main():
    with st.sidebar:
        st.markdown("## ⚙️ Nastavitve")

        if st.button("🔄 Ponastavi sejo", use_container_width=True):
            reset_app()

        st.divider()
        st.markdown("### 🤖 AI klasifikacija (Google)")
        classification_mode = st.radio(
            "Način klasifikacije",
            ["AI model (Gemini / Gemma)", "Slovar (offline, brez API klica)"]
        )

        api_key = None
        model_name = None
        batch_size = 15
        processing_mode = "single_call"
        max_output_tokens = 32768

        if classification_mode.startswith("AI"):
            api_key = st.text_input(
                "Google AI API ključ", type="password",
                help="Brezplačen ključ dobiš na https://aistudio.google.com/apikey"
            )
            model_name = st.selectbox("Model", AVAILABLE_MODELS, index=0)

            processing_label = st.radio(
                "Način obdelave",
                [
                    "En sam klic (najhitreje - cel nabor kot ena množica)",
                    "Paketno procesiranje (bolj zanesljivo pri zelo velikih naborih)"
                ],
                help=(
                    "'En sam klic' pošlje vse vrstice PF+SF+PR (npr. vseh 200 "
                    "respondentov) v enem API klicu - model jih obravnava kot eno "
                    "homogeno množico (npr. javna uprava). Bistveno hitreje, a pri "
                    "zelo velikih datotekah lahko naleti na omejitev izhodnih "
                    "tokenov - v tem primeru preklopi na paketno obdelavo."
                )
            )
            processing_mode = "single_call" if processing_label.startswith("En sam") else "batched"

            max_output_tokens = 32768
            if processing_mode == "batched":
                batch_size = st.slider("Velikost paketa (vrstic na klic)", 5, 40, 15)
            else:
                max_output_tokens = st.select_slider(
                    "Max izhodnih tokenov (zmanjšaj, če javi napako 400)",
                    options=[4096, 8192, 16384, 32768, 65536],
                    value=32768
                )

        st.divider()
        st.markdown("### 🧭 Katere enote naj bodo zajete?")
        included_shorts = st.multiselect(
            "Vključene enote",
            list(CATEGORY_SHORT.values()),
            default=list(CATEGORY_SHORT.values())
        )
        active_categories = [SHORT_TO_FULL[s] for s in included_shorts] or list(CATEGORIES_MAP.keys())

        st.divider()
        n_input = st.number_input("Število respondentov (N)", min_value=1, value=210)
        is_summary = st.checkbox("Datoteka vsebuje POVZETEK", value=True)

        st.divider()
        weighting_label = st.radio(
            "Uteževanje znotraj enote",
            ["Volumen (frekvenca)", "Koncentracija (ponovljivost)"]
        )
        weighting_mode = "volume" if "Volumen" in weighting_label else "concentration"

        st.divider()
        chart_mode = st.radio("Prikaz porazdelitve", ["Stolpični graf", "Treemap (barvit)", "Oboje"])

        st.divider()
        uploaded_file = st.file_uploader("📁 Naložite podatke", type=["txt", "csv", "xlsx"])

    st.markdown("# 📊 Petrič Stress Analysis Pro")
    st.caption("Klasifikacija z Google Gemini/Gemma modeli · 5 znanstvenih enot (Social = social + partial social)")

    if not uploaded_file:
        st.info("📁 Naložite datoteko za začetek analize.", icon="ℹ️")
        return

    if classification_mode.startswith("AI"):
        if not api_key:
            st.warning("⚠️ Vnesite Google AI API ključ v stranski vrstici, da uporabite AI klasifikacijo.")
            return
        if model_name == AVAILABLE_MODELS[0]:
            st.warning("⚠️ Izberite model v stranski vrstici.")
            return

    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".txt"):
            df = pd.read_csv(uploaded_file, sep="\t", engine="python", on_bad_lines="skip")
        else:
            df = pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Napaka pri branju: {e}")
        return

    target_cols = df.columns.tolist()

    with st.sidebar:
        st.markdown("### 🧩 Stolpci")
        col_pf = st.selectbox("Pozitivni (PF)", target_cols, index=0)
        col_sf = st.selectbox("Stresni (SF)", target_cols, index=min(1, len(target_cols) - 1))
        col_pr = st.selectbox("Predlogi (PR)", target_cols, index=min(2, len(target_cols) - 1))

    # ---------------- KLASIFIKACIJA ----------------
    analysis = {}

    if classification_mode.startswith("AI"):
        client = get_client(api_key)

        if processing_mode == "single_call":
            n_rows_total = (
                df[col_pf].dropna().shape[0]
                + df[col_sf].dropna().shape[0]
                + df[col_pr].dropna().shape[0]
            )
            with st.spinner(
                f"🤖 Model obdeluje vseh {n_rows_total} vrstic (PF+SF+PR) "
                "v enem klicu, kot eno množico ..."
            ):
                buckets = classify_everything_single_call(
                    client, model_name, df, col_pf, col_sf, col_pr, included_shorts,
                    max_output_tokens=max_output_tokens
                )
            if buckets is None:
                return
            analysis = buckets
        else:
            for role, col, label in [
                ("PF", col_pf, "🔵 Klasificiram pozitivne dejavnike ..."),
                ("SF", col_sf, "🔴 Klasificiram stresne dejavnike ..."),
                ("PR", col_pr, "🟢 Klasificiram predloge ...")
            ]:
                cls, per_row = run_ai_classification(
                    client, model_name, df, col, included_shorts, batch_size, label
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

    st.markdown("## 🎯 Skupni rezultati")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stresna moč", f"{sigma_total:.2f} °S", rate_sigma(sigma_total))
    m2.metric("Učinkovitost", f"{eta:.1f} %")
    m3.metric("Izguba energije", f"{loss:.0f} Kcal")
    m4.metric("Vzorec (N)", n_input)
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
            "Delež (%)": round(data["weight_share"] * 100, 1),
            "Ocena": rate_sigma(data["sigma"])
        })
    res_df = pd.DataFrame(rows).sort_values(by="σ (°S)", ascending=False)

    st.markdown("### Porazdelitev po znanstvenih enotah")
    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.dataframe(res_df, use_container_width=True, hide_index=True)

    with col_right:
        if chart_mode in ("Stolpični graf", "Oboje"):
            st.plotly_chart(
                px.bar(res_df, x="Enota", y="σ (°S)", color="σ (°S)",
                       color_continuous_scale="Reds", height=300),
                use_container_width=True
            )
        if chart_mode in ("Treemap (barvit)", "Oboje"):
            st.plotly_chart(
                px.treemap(
                    res_df, path=["Enota"], values="σ (°S)",
                    color="σ (°S)", color_continuous_scale="RdYlGn_r",
                    height=350
                ),
                use_container_width=True
            )

    # ---------------- TREEMAP: PF / SF / PR SKUPAJ ----------------
    st.markdown("### 🗺️ Treemap: vse besedne zveze po vlogi in enoti")
    tree_rows = []
    role_labels = {"PF": "Pozitivni", "SF": "Stresni", "PR": "Predlogi"}
    for role, label in role_labels.items():
        freq = Counter(c for _, c in analysis[role]["classified"])
        for cat, count in freq.items():
            tree_rows.append({
                "Vloga": label,
                "Enota": CATEGORY_SHORT[cat],
                "Frekvenca": count
            })
    if tree_rows:
        tree_df = pd.DataFrame(tree_rows)
        st.plotly_chart(
            px.treemap(
                tree_df, path=["Vloga", "Enota"], values="Frekvenca",
                color="Frekvenca", color_continuous_scale="Turbo", height=450
            ),
            use_container_width=True
        )
    else:
        st.caption("Ni razvrščenih izrazov za prikaz treemap-a.")

    # ---------------- KVALITATIVNI PREGLED ----------------
    with st.expander("🔍 Podrobnosti klasifikacije besed/fraz"):
        t1, t2, t3 = st.tabs(["🟢 Pozitivni", "🔴 Stresni", "🔵 Predlogi"])
        for tab, role in zip([t1, t2, t3], ["PF", "SF", "PR"]):
            with tab:
                freq = Counter(c for _, c in analysis[role]["classified"])
                st.table(pd.DataFrame([
                    {"Enota": CATEGORY_SHORT.get(k, k), "Frekvenca": v}
                    for k, v in freq.items()
                ]))
                st.markdown("**Primeri razvrščenih fraz:**")
                sample = analysis[role]["classified"][:40]
                if sample:
                    st.dataframe(
                        pd.DataFrame(
                            [{"Fraza": w, "Enota": CATEGORY_SHORT[c]} for w, c in sample]
                        ),
                        use_container_width=True, hide_index=True
                    )


if __name__ == "__main__":
    main()

