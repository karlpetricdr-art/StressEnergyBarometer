import streamlit as st
import pandas as pd
import re
import math
from collections import Counter, defaultdict

# ============================================================
# 1. PONASTAVITEV APLIKACIJE
# ============================================================
def reset_app():
    """Popolnoma izbriše sejo in ponovno naloži aplikacijo."""
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# ============================================================
# 2. STOP-WORDS (MAŠILA)
# ============================================================
# Seznam besed, ki jih sistem ignorira. 
# Besede "talk", "family" in "friends" so odstranjene, da jih sistem klasificira.
SLO_STOPWORDS = {
    "se", "si", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "le", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "vsega", "vsemu", "vsem",
    "tisti", "tista", "tisto", "tistih", "tistem", "tistimi", "nekaj", "včasih", "npr", "itd", "itn",
    "ker", "ko", "kadar", "kam", "kjer", "kaj", "kdo", "kdaj", "zakaj", "kako", "vendar", "ampak",
    "toda", "torej", "zato", "saj", "namreč", "zlasti", "predvsem", "sploh", "šele", "kar", "naj",
    "ali", "gre", "marsikaj", "marsikdo", "nekdo", "nekateri", "nekatera", "nekatero",
    "pod", "med", "nad", "pred", "brez", "ob", "po", "skozi", "čez", "proti", "kljub", "zaradi",
    "namesto", "razen", "okoli", "okrog", "tem",
    "the", "and", "to", "of", "a", "is", "in", "it", "with", "some", "more", "being", "able",
    "use", "make", "nice", "your", "this", "that", "from", "for", "are", "was", "were"
}

# ============================================================
# 3. REVIDIRAN KLASIFIKACIJSKI MODEL (Petrič, 2025)
# ============================================================
# Razvrščanje v 5 znanstvenih enot (Socialna in Parcialno-socialna sta združeni).
# Vsaka beseda se dodeli PRVI ujemajoči se kategoriji.
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem", "prostor", "pisarn", "ergonom",
        "oprem", "tišin", "zrak", "prah", "gneč", "tehni", "akcij", "poškodb", "varna", "objekt",
        "sodobn", "naprav", "urejenost", "etiket", "izolac", "barv", "rastlin", "vonjav",
        "stol", "miz", "prezrač", "notranj", "location", "environment", "lighting", "toplota",
        "hlad", "umazano", "onesnaž", "arhitekt", "opremljenost", "hrupn", "svetloba", "tišina",
        "classical", "music", "flower", "klasič", "glasb", "rož", "cvet", "flowers"
    ],
    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "čas", "administra", "birokra",
        "obrazc", "poročil", "sestank", "postopk", "navodil", "veščin", "hitenj",
        "naglic", "stisk", "preobremen", "neizkušn", "učinkovit",
        "biro", "togi", "rutin", "nujne", "izobraž", "usposab", "optimiz", "proces",
        "poenostav", "inovac", "rešitev", "urnik", "ure", "izvajanj", "regula", "hrm",
        "direktiv", "ukaluplj", "iskanj", "gradiv", "polic", "katalog", "orientac",
        "podatkov", "fond", "isposoj", "job", "balance", "goal", "cilj", "študij",
        "literature", "izvodi", "raziskav", "iskanje", "tasks", "program",
        "training", "exercise", "activities", "šport", "rekreac", "tek", "joga", "plavanj", "kolo"
    ],
    "Individual Psychological unit": [
        "strah", "tesnob", "optimiz", "pozitiv", "samozav", "čustv", "stres", "frustr",
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb", "napetos", "psih", "travm",
        "osebno", "samopodob", "nasil", "negativ", "dušev", "žalost", "ogroženost",
        "nelagod", "zadovolj", "psihi", "nemir", "choice", "life", "memory",
        "spomin", "art", "umetnos", "irrational", "uncertain", "uncertainty", "peace",
        "feeling", "hope", "values", "vrednot", "ponižanj", "identitet", "dopust",
        "izlet", "potovan", "journey", "sprošč", "relax", "medit", "dihan", "pripadnost",
        "narav", "spomini", "praznina", "osebnost", "samokontrol", "vera", "mirnost"
    ],
    "Social unit (merged)": [
        # Interpersonalni odnosi, vodenje in komunikacija
        "odnos", "mobing", "organizac", "sestank", "šikan", "sodelav", "šef", "vodstv", "nadrejen", "družin",
        "prijatel", "komunik", "prepir", "zahrbt", "vzvišen", "nesram", "aroganc",
        "egoiz", "podpor", "konflikt", "intrig", "neiskren", "rival", "polit",
        "hierarh", "timsko", "druženj", "domače", "kader", "sodelov", "sovrašt",
        "grožn", "informac", "profesional", "uporabnik", "osebj", "človek", "friend",
        "family", "talk", "prijatelj", "družin", "pogovor", "pomoč", "ekipa", "prijaznost",
        "partnership", "spouse", "sodelovanje", "zaupan", "vodenj", "klima", "vzdušje",
        "ignora", "nerazum", "posluš", "sektor", "direktor", "vodja", "pripadnost", "rivalstvo",
        "economic", "level", "law", "alcohol", "weapon", "zakon", "orož", "standard", "družb", "friends",
        # Finančni in statusni dejavniki (Prej parcial-social)
        "plač", "dohod", "denar", "finanč", "nagrad", "status", "priznan", "revšč",
        "standar", "nepravič", "nestimul", "krivic", "dostojen", "zaposlit", "služb",
        "karier", "napredov", "varnost", "staž", "benefic", "ekonom", "proračun",
        "pokojnin", "sredstv", "zamudn", "opomin", "kazn", "plačev", "plačilo", "money",
        "salary", "financial", "budget", "stability", "sredstva", "znesek"
    ],
    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "spanj", "utrujen", "izčrpan", "higien",
        "čistoč", "sleep", "rest", "dihanje", "poškodb", "izčrpanost", "utrujenost",
        "zdravje", "bolečina", "virus", "infekcij", "higiena", "prehran", "diet",
        "biološ", "fiziolo", "telo", "utrujena", "spanja", "telesno", "exhaustion"
    ]
}

# Lestvica ocenjevanja moči stresa (Tabela 6 v članku)
RATING_SCALE = [
    (15.04, "Zelo nizka"),
    (30.04, "Nizka"),
    (45.04, "Srednja"),
    (60.04, "Višja"),
    (75.04, "Visoka"),
    (90.01, "Zelo visoka"),
]

def rate_sigma(sigma):
    """Vrne tekstovno oceno na podlagi stopinj stresa."""
    for threshold, label in RATING_SCALE:
        if sigma <= threshold:
            return label
    return "Zelo visoka"

# ============================================================
# 4. POMOŽNE FUNKCIJE ZA OBDELAVO BESEDILA
# ============================================================

def clean_and_tokenize(text):
    """Odstrani ločila, pretvori v male črke in izloči mašila."""
    if not isinstance(text, str):
        return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]

def classify_word_single(word):
    """Besedo dodeli natanko eni kategoriji (prvi ujemajoči se)."""
    for cat, kw_list in CATEGORIES_MAP.items():
        if any(koren in word for koren in kw_list):
            return cat
    return None

def analyze_column(df, col):
    """Klasificira vse besede v stolpcu in pripravi frekvence."""
    classified = []
    per_row_categories = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        row_cats = []
        for kw in kws:
            cat = classify_word_single(kw)
            if cat:
                classified.append((kw, cat))
                row_cats.append(cat)
        per_row_categories.append(row_cats)
    return classified, per_row_categories

# ============================================================
# 5. IZRAČUN REALNEGA FAKTORJA Fo (Po Petričevi metodi)
# ============================================================

def calculate_fo_real_aggregate(classified, n_override):
    """Izračuna agregatni Fo faktor za celotno stresno moč."""
    all_words = [w for w, _ in classified]
    fo = len(all_words)
    fr = len(set(all_words))
    if fr == 0 or n_override == 0:
        return 0.0001, fo, fr
    rho_o = fo / n_override
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr

def compute_category_factors(classified, n_override, weighting_mode="volume"):
    """Izračuna specifične faktorje za vsako od 5 enot."""
    words_by_cat = defaultdict(list)
    for w, c in classified:
        words_by_cat[c].append(w)

    result = {}
    for cat in CATEGORIES_MAP.keys():
        words = words_by_cat.get(cat, [])
        fE = len(words)
        frE = len(set(words))
        # CE: uteževanje glede na volumen ali koncentracijo
        if weighting_mode == "concentration":
            CE = fE / frE if frE > 0 else 0.0001
        else:
            CE = 1.0
        rho = fE / n_override if n_override else 0.0
        F = (CE * rho) / 10.0
        result[cat] = {"fE": fE, "frE": frE, "CE": CE, "rho": rho, "F": F}
    return result

def sigma_deg(f_sf, f_pr, f_pf):
    """Glavna formula: arcsin(sqrt((F_SF * F_PR) / F_PF))."""
    if f_pf <= 0: f_pf = 0.0001
    argument = max((f_sf * f_pr) / f_pf, 0.0)
    sigma_rad = math.asin(min(math.sqrt(argument), 1.0))
    return math.degrees(sigma_rad)

def sigma_argument(f_sf, f_pr, f_pf):
    """Izračuna kvadrat sinusa (argument za normalizacijo)."""
    if f_pf <= 0: f_pf = 0.0001
    return max((f_sf * f_pr) / f_pf, 0.0)

def compute_category_sigmas(factors_sf, factors_pf, factors_pr, sigma_total_argument, is_summary):
    """Nelinearna kvadraturna normalizacija pod-enot na skupno moč."""
    raw_arguments = {}
    for cat in CATEGORIES_MAP.keys():
        f_pf_cat = factors_pf[cat]["F"]
        f_sf_cat = factors_sf[cat]["F"]
        f_pr_cat = factors_pr[cat]["F"]
        if is_summary and f_sf_cat > 0:
            f_pr_cat = min(f_pr_cat, f_sf_cat * 1.5)
        raw_arguments[cat] = sigma_argument(f_sf_cat, f_pr_cat, f_pf_cat)

    S = sum(raw_arguments.values())
    k = (sigma_total_argument / S) if S > 0 else 0.0
    results = {}
    for cat, arg in raw_arguments.items():
        scaled_arg = min(arg * k, 1.0)
        sigma = math.degrees(math.asin(math.sqrt(scaled_arg)))
        results[cat] = {
            "sigma": sigma,
            "scaled_argument": scaled_arg,
            "weight_share": (arg / S) if S > 0 else 0.0
        }
    return results, S, k

# ============================================================
# 6. STREAMLIT UPORABNIŠKI VMESNIK
# ============================================================

def main():
    st.set_page_config(page_title="Petrič Stress Analysis Pro", page_icon="📊", layout="wide")

    # --- STRANSKI MENI ---
    with st.sidebar:
        st.header("⚙️ Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()
        st.subheader("📊 Parametri raziskave")
        n_input = st.number_input("Dejansko število respondentov (N):", min_value=1, value=210)
        is_summary = st.checkbox("Ali naložena datoteka vsebuje POVZETEK?", value=True)
        st.divider()
        st.subheader("🧮 Metoda uteževanja")
        weighting_label = st.radio(
            "Način izračuna teže enot:",
            options=["Volumen (frekvenca)", "Koncentracija (ponovljivost)"]
        )
        weighting_mode = "volume" if "Volumen" in weighting_label else "concentration"

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown(f"Znanstvena kalibracija za **N = {n_input}** respondentov. Socialni enoti sta združeni.")

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])

    if not uploaded_file:
        st.info("Prosim, naložite datoteko za začetek analize.", icon="ℹ️")
        return

    sep = '\t' if uploaded_file.name.endswith('.txt') else ','
    try:
        df = pd.read_csv(uploaded_file, sep=sep, engine='python', on_bad_lines='skip')
    except Exception as e:
        st.error(f"Napaka pri branju: {e}")
        return

    st.success(f"Naloženo: {len(df)} vrstic.", icon="✅")
    target_cols = df.columns.tolist()

    st.sidebar.divider()
    col_pf = st.sidebar.selectbox("Pozitivni (PF):", target_cols, index=0)
    col_sf = st.sidebar.selectbox("Stresni (SF):", target_cols, index=min(1, len(target_cols)-1))
    col_pr = st.sidebar.selectbox("Predlogi (PR):", target_cols, index=min(2, len(target_cols)-1))
    role_cols = {"PF": col_pf, "SF": col_sf, "PR": col_pr}

    # Analiza
    analysis = {}
    for role, col in role_cols.items():
        classified, per_row_categories = analyze_column(df, col)
        analysis[role] = {"col": col, "classified": classified, "per_row": per_row_categories}

    # 1. Kvalitativna analiza
    st.header("🔍 Kvalitativna analiza po sklopih")
    freq_tables = {}
    for role, col in role_cols.items():
        with st.expander(f"Podrobnosti za: {col} ({role})", expanded=False):
            all_units = [unit for sublist in analysis[role]["per_row"] for unit in sublist]
            freq_df = pd.DataFrame(Counter(all_units).items(), columns=['Enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
            freq_tables[role] = freq_df
            st.table(freq_df)

    # 2. Globalni izračun
    st.divider()
    st.header("📐 Izračun celokupne stresne moči")
    f_pf_agg, _, _ = calculate_fo_real_aggregate(analysis["PF"]["classified"], n_input)
    f_sf_agg, _, _ = calculate_fo_real_aggregate(analysis["SF"]["classified"], n_input)
    f_pr_agg, _, _ = calculate_fo_real_aggregate(analysis["PR"]["classified"], n_input)

    if is_summary: f_pr_agg = min(f_pr_agg, f_sf_agg * 1.5)
    sigma_total = sigma_deg(f_sf_agg, f_pr_agg, f_pf_agg)

    with st.container(border=True):
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.metric(label="STRESNA MOČ", value=f"{sigma_total:.2f} °S")
            st.info(f"Ocena: {rate_sigma(sigma_total)}")
        with c2:
            st.write("**Faktorji Fo:**")
            st.markdown(f"- PF: {f_pf_agg:.4f} | SF: {f_sf_agg:.4f} | PR: {f_pr_agg:.4f}")
            st.progress(min(sigma_total / 90, 1.0))

    # 3. Energijska učinkovitost
    st.subheader("⚡ Energijska učinkovitost po Petriču")
    W_I = 2500.0
    W_EU = W_I - (W_I * sigma_total / 90.0)
    eta = (W_EU / W_I) * 100
    ec1, ec2, ec3 = st.columns(3)
    ec1.metric("Efektivna poraba", f"{W_EU:.0f} Kcal")
    ec2.metric("Učinkovitost (η)", f"{eta:.2f} %")
    ec3.metric("Izguba energije", f"{100 - eta:.2f} %")

    # 4. Razčlenitev po enotah
    st.divider()
    st.header("🧩 Stresna moč po znanstvenih enotah")
    factors_pf = compute_category_factors(analysis["PF"]["classified"], n_input, weighting_mode)
    factors_sf = compute_category_factors(analysis["SF"]["classified"], n_input, weighting_mode)
    factors_pr = compute_category_factors(analysis["PR"]["classified"], n_input, weighting_mode)
    
    sig_total_arg = min(sigma_argument(f_sf_agg, f_pr_agg, f_pf_agg), 1.0)
    cat_sigmas, _, _ = compute_category_sigmas(factors_sf, factors_pf, factors_pr, sig_total_arg, is_summary)

    rows = []
    for cat, cs in cat_sigmas.items():
        rows.append({
            "Enota": cat,
            "σ (°S)": round(cs["sigma"], 2),
            "Delež (%)": round(cs["weight_share"]*100, 1),
            "Ocena": rate_sigma(cs["sigma"])
        })
    
    res_df = pd.DataFrame(rows).sort_values(by="σ (°S)", ascending=False)
    st.dataframe(res_df, use_container_width=True, hide_index=True)
    st.bar_chart(res_df.set_index("Enota")[["σ (°S)"]], color="#E1571C")

if __name__ == "__main__":
    main()


