import streamlit as st
import pandas as pd
import re
import math
from collections import Counter, defaultdict
import plotly.express as px

# ============================================================
# 1. NASTAVITVE STRANI
# ============================================================

st.set_page_config(
    page_title="Petrič Stress Analysis Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. FUNKCIJA ZA PONASTAVITEV
# ============================================================

def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ============================================================
# 3. ESTETSKI CSS (UI IZBOLJŠAVE)
# ============================================================

st.markdown("""
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
        color: #1e293b;
    }
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #e5e9f0;
        box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        min-height: 145px;
        text-align: center;
    }
    .metric-title {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 5px;
        color: #1e293b;
    }
    .metric-description {
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 5px;
    }
    .social-card {
        background: linear-gradient(135deg, #fff7ed, #ffffff);
        border: 2px solid #f97316;
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 6px 20px rgba(249,115,22,0.12);
        margin-bottom: 20px;
    }
    .stress-high { color: #dc2626; font-weight: 800; }
    .stress-medium { color: #ea580c; font-weight: 700; }
    .stress-low { color: #16a34a; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 4. STOP-WORDS (MAŠILA)
# ============================================================

SLO_STOPWORDS = {
    # Osnovni vezniki, delci in pomožni glagoli
    "se", "si", "oh", "na", "potem", "in", "ter", "bi", "da", "pa",
    "že", "tudi", "iz", "za", "še", "samo", "le", "tako", "kot",
    "sem", "smo", "ste", "so", "je", "bil", "biti", "ali", "v",
    "pri", "o", "z", "s", "k", "h", "vse", "vsi", "vsega", "vsemu",
    "vsem", "tisti", "tista", "tisto", "tistih", "tistem", "tistimi",
    "nekaj", "včasih", "npr", "itd", "itn", "ker", "ko", "kadar",
    "kam", "kjer", "kaj", "kdo", "kdaj", "zakaj", "kako", "vendar",
    "ampak", "toda", "torej", "zato", "saj", "namreč", "zlasti",
    "predvsem", "sploh", "šele", "kar", "naj", "gre", "ali",
    "pod", "med", "nad", "pred", "brez", "ob", "po", "skozi", "čez",
    "proti", "kljub", "zaradi", "namesto", "razen", "okoli", "okrog",
    "tem",

    # DODATEK PO ŽELJI UPORABNIKA:
    "več", 

    # Angleški strukturni izrazi
    "the", "and", "to", "of", "a", "is", "it", "with", "some",
    "more", "being", "able", "use", "make", "nice", "your", "this",
    "that", "from", "for", "are", "was", "were", "been", "has", "have"
}
# ============================================================
# 5. ZNANSTVENA KLASIFIKACIJA (Petrič, 2025)
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
        # "okolje" je po želji uporabnika odstranjeno od tukaj in prestavljeno v Social unit
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
        "training", "exercise", "activities",
        # DODATEK PO KONTEKSTU:
        "dela", "delo"
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
        # Kontekstualni dodatki uporabnika:
        "delovnem", "mestu", "dobr", "obveznost", "okolje",
        
        # Interpersonalni in organizacijski odnosi
        "odnos", "odnosih", "odnosov", "mobing", "šikan",
        "sodelav", "sodelovanje", "sodelov", "šef", "vodstv",
        "nadrejen", "družin", "prijatel", "komunik", "pogovor",
        "prepir", "zahrbt", "vzvišen", "nesram", "aroganc",
        "egoiz", "podpor", "konflikt", "intrig", "neiskren",
        "rival", "polit", "hierarh", "timsko", "druženj",
        "domače", "kader", "sovrašt", "grožn", "profesional",
        "uporabnik", "osebj", "človek", "friend", "family",
        "talk", "prijatelj", "partnership", "spouse",
        "zaupan", "vodenj", "klima", "vzdušje", "ignor",
        "nerazum", "posluš", "sektor", "direktor", "vodja",
        "pripadnost", "rivalstvo", "friends",
        "organizac", "organizaciji", "sestank", "meeting",
        "team", "teamwork", "management", "leadership",
        
        # Statusni in finančni dejavniki
        "plač", "dohod", "denar", "finanč", "nagrad", "status",
        "priznan", "revšč", "standar", "nepravič", "nestimul",
        "krivic", "dostojen", "zaposlit", "služb", "karier",
        "napredov", "varnost", "staž", "benefic", "ekonom",
        "proračun", "pokojnin", "sredstv", "zamudn", "opomin",
        "kazn", "plačev", "plačilo", "money", "salary",
        "financial", "budget", "stability", "znesek",
        "družb", "law", "zakon", "orož", "weapon", "alcohol",
        "economic", "level", "standard"
    ],

    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "spanj", "utrujen",
        "izčrpan", "higien", "čistoč", "sleep", "rest",
        "dihanje", "izčrpanost", "utrujenost", "zdravje",
        "bolečina", "virus", "infekcij", "higiena", "prehran",
        "diet", "biološ", "fiziolo", "telo", "utrujena",
        "spanja", "telesno", "exhaustion", "šport", "rekreac",
        "tek", "joga", "aktiv", "plavanj", "kolo", "vrtnar", "hobi"
    ]
}

# ============================================================
# 6. MATEMATIČNI PARAMETRI IN LESTVICE
# ============================================================

SLOPE_WEIGHTS = {
    "Attentive (physical) unit": 0.85,
    "Performance unit": 1.05,
    "Individual Psychological unit": 1.00,
    "Social unit": 1.30,
    "Health biological unit": 0.90
}

CATEGORY_SHORT = {
    "Attentive (physical) unit": "Attentive",
    "Performance unit": "Performance",
    "Individual Psychological unit": "Psychological",
    "Social unit": "Social",
    "Health biological unit": "Health"
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
        if sigma <= threshold: return label
    return "Zelo visoka"

# ============================================================
# 7. POMOŽNE FUNKCIJE ZA OBDELAVO
# ============================================================

def clean_and_tokenize(text):
    if not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]

def classify_word_single(word):
    # PRIORITETNI VRSTNI RED: Socialna enota ima prednost, 
    # da pravilno ujame "dobr" ali "okolje".
    priority_order = [
        "Social unit",
        "Performance unit",
        "Individual Psychological unit",
        "Health biological unit",
        "Attentive (physical) unit"
    ]
    for cat in priority_order:
        kw_list = CATEGORIES_MAP[cat]
        if any(koren in word for koren in kw_list):
            return cat
    return None

def analyze_column(df, col):
    classified, per_row_categories, unclassified_words = [], [], []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        row_cats = []
        for kw in kws:
            cat = classify_word_single(kw)
            if cat:
                classified.append((kw, cat))
                row_cats.append(cat)
            else:
                unclassified_words.append(kw)
        per_row_categories.append(row_cats)
    return classified, per_row_categories, unclassified_words
# ============================================================
# 11. MATEMATIČNA LOGIKA (PETRIČEVA METODA)
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

def compute_category_factors(classified, n_override, weighting_mode="volume"):
    words_by_cat = defaultdict(list)
    for word, category in classified:
        words_by_cat[category].append(word)
    result = {}
    for category in CATEGORIES_MAP.keys():
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
    if f_pf <= 0: f_pf = 0.0001
    argument = (f_sf * f_pr) / f_pf
    return max(argument, 0.0)

def sigma_deg(f_sf, f_pr, f_pf):
    arg = sigma_argument(f_sf, f_pr, f_pf)
    sigma_rad = math.asin(math.sqrt(min(arg, 1.0)))
    return math.degrees(sigma_rad)

def compute_category_sigmas(factors_sf, factors_pf, factors_pr, sigma_total_argument, is_summary):
    raw_scores = {}
    raw_arguments = {}
    for category in CATEGORIES_MAP.keys():
        f_pf = factors_pf[category]["F"]
        f_sf = factors_sf[category]["F"]
        f_pr = factors_pr[category]["F"]
        if is_summary and f_sf > 0:
            f_pr = min(f_pr, f_sf * 1.5)
        argument = sigma_argument(f_sf, f_pr, f_pf)
        weighted_score = argument * SLOPE_WEIGHTS[category]
        raw_arguments[category] = argument
        raw_scores[category] = weighted_score

    total_score = sum(raw_scores.values())
    results = {}
    if total_score <= 0:
        for category in CATEGORIES_MAP.keys():
            results[category] = {"sigma": 0.0, "slope_index": 0.0, "weight_share": 0.0}
        return results, 0.0

    for category in CATEGORIES_MAP.keys():
        share = raw_scores[category] / total_score
        scaled_argument = min(sigma_total_argument * share, 1.0)
        sigma = math.degrees(math.asin(math.sqrt(scaled_argument)))
        results[category] = {
            "sigma": sigma,
            "slope_index": raw_scores[category],
            "weight_share": share
        }
    return results, total_score

def calculate_energy(sigma):
    W_I = 2500.0
    W_EU = W_I - (W_I * sigma / 90.0)
    eta = (W_EU / W_I) * 100.0
    loss = W_I - W_EU
    return W_EU, eta, loss

# ============================================================
# 12. GLAVNA STREAMLIT APLIKACIJA (UI)
# ============================================================

def main():
    with st.sidebar:
        st.markdown("## ⚙️ Nastavitve")
        if st.button("🔄 Ponastavi sejo", use_container_width=True): reset_app()
        st.divider()
        n_input = st.number_input("Število respondentov (N)", min_value=1, value=210)
        is_summary = st.checkbox("Datoteka vsebuje POVZETEK", value=True)
        st.divider()
        weighting_label = st.radio("Uteževanje", ["Volumen (frekvenca)", "Koncentracija (ponovljivost)"])
        weighting_mode = "volume" if "Volumen" in weighting_label else "concentration"
        st.divider()
        uploaded_file = st.file_uploader("📁 Naložite podatke", type=["txt", "csv", "xlsx"])

    st.markdown("# 📊 Petrič Stress Analysis Pro")

    if not uploaded_file:
        st.info("📁 Naložite datoteko za začetek analize.", icon="ℹ️")
        return

    try:
        if uploaded_file.name.endswith(".xlsx"): df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".txt"): df = pd.read_csv(uploaded_file, sep="\t", engine="python", on_bad_lines="skip")
        else: df = pd.read_csv(uploaded_file, engine="python", on_bad_lines="skip")
    except Exception as e:
        st.error(f"Napaka pri branju: {e}"); return

    target_cols = df.columns.tolist()
    with st.sidebar:
        st.markdown("### 🧩 Stolpci")
        col_pf = st.selectbox("Pozitivni (PF)", target_cols, index=0)
        col_sf = st.selectbox("Stresni (SF)", target_cols, index=min(1, len(target_cols)-1))
        col_pr = st.selectbox("Predlogi (PR)", target_cols, index=min(2, len(target_cols)-1))

    # ANALIZA
    analysis = {}
    for role, col in [("PF", col_pf), ("SF", col_sf), ("PR", col_pr)]:
        cls, per_row, uncls = analyze_column(df, col)
        analysis[role] = {"classified": cls, "per_row": per_row, "unclassified": uncls, "col_name": col}

    # GLOBALNI IZRAČUN
    f_pf_agg, _, _ = calculate_fo_real_aggregate(analysis["PF"]["classified"], n_input)
    f_sf_agg, _, _ = calculate_fo_real_aggregate(analysis["SF"]["classified"], n_input)
    f_pr_agg, _, _ = calculate_fo_real_aggregate(analysis["PR"]["classified"], n_input)
    if is_summary: f_pr_agg = min(f_pr_agg, f_sf_agg * 1.5)
    sigma_total = sigma_deg(f_sf_agg, f_pr_agg, f_pf_agg)
    W_EU, eta, loss = calculate_energy(sigma_total)

    # GLAVNE METRIKE
    st.markdown("### 🎯 Skupna stresna moč")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Stresna moč", f"{sigma_total:.2f} °S", rate_sigma(sigma_total))
    m2.metric("Učinkovitost", f"{eta:.1f} %")
    m3.metric("Izguba energije", f"{loss:.0f} Kcal")
    m4.metric("Vzorec (N)", n_input)
    st.progress(min(sigma_total / 90.0, 1.0))

    # RAZČLENITEV PO ENOTAH
    st.divider()
    st.markdown("### 🧩 Razčlenitev po znanstvenih enotah")
    
    f_pf_cat = compute_category_factors(analysis["PF"]["classified"], n_input, weighting_mode)
    f_sf_cat = compute_category_factors(analysis["SF"]["classified"], n_input, weighting_mode)
    f_pr_cat = compute_category_factors(analysis["PR"]["classified"], n_input, weighting_mode)
    
    sig_total_arg = min(sigma_argument(f_sf_agg, f_pr_agg, f_pf_agg), 1.0)
    cat_sigmas, _ = compute_category_sigmas(f_sf_cat, f_pf_cat, f_pr_cat, sig_total_arg, is_summary)

    rows = []
    for cat, data in cat_sigmas.items():
        rows.append({
            "Enota": CATEGORY_SHORT[cat], 
            "σ (°S)": round(data["sigma"], 2), 
            "Delež (%)": round(data["weight_share"]*100, 1), 
            "Koeficient": SLOPE_WEIGHTS[cat],
            "Ocena": rate_sigma(data["sigma"])
        })
    
    res_df = pd.DataFrame(rows).sort_values(by="σ (°S)", ascending=False)
    
    # KOMPAKTEN VPOGLED NAMESTO VELIKE KARTICE
    top_cat = res_df.iloc[0]
    st.info(f"**Ključni vpogled:** Največji vpliv na skupni stres ima **{top_cat['Enota']}** ({top_cat['σ (°S)']} °S), kar predstavlja {top_cat['Delež (%)']}% celotne stresne obremenitve.")

    # TABELA IN GRAF
    c_tab, c_graph = st.columns([1, 1])
    with c_tab:
        st.dataframe(res_df, use_container_width=True, hide_index=True)
    with c_graph:
        st.plotly_chart(px.bar(res_df, x="Enota", y="σ (°S)", color="σ (°S)", color_continuous_scale="OrRd", height=300), use_container_width=True)

    # KVALITATIVNI PREGLED
    with st.expander("🔍 Podrobnosti klasifikacije"):
        t1, t2, t3 = st.tabs(["🟢 Pozitivni", "🔴 Stresni", "🔵 Predlogi"])
        for tab, role in zip([t1, t2, t3], ["PF", "SF", "PR"]):
            with tab:
                freq = Counter(c for _, c in analysis[role]["classified"])
                st.table(pd.DataFrame([{"Enota": CATEGORY_SHORT[k], "Frekvenca": v} for k, v in freq.items()]))

if __name__ == "__main__":
    main()


