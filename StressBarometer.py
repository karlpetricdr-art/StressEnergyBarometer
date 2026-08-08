```python
import streamlit as st
import pandas as pd
import re
import math
from collections import Counter, defaultdict
import plotly.express as px


# ============================================================
# 1. NASTAVITVE
# ============================================================

st.set_page_config(
    page_title="Petrič Stress Analysis Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. PONASTAVITEV
# ============================================================

def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================
# 3. ESTETSKI CSS
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

.metric-title {
    color: #64748b;
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metric-value {
    font-size: 2rem;
    font-weight: 800;
    margin-top: 5px;
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
}

.section-card {
    background: white;
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #e5e9f0;
    margin-bottom: 15px;
}

.rank-number {
    font-size: 1.8rem;
    font-weight: 800;
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
""", unsafe_allow_html=True)


# ============================================================
# 4. STOPWORDS
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
# 5. ZNANSTVENA KLASIFIKACIJA
#
# Petrič (2025):
# - attentive physical
# - performance
# - individual psychological
# - partial social
# - social
# - health-biological
#
# V aplikaciji sta partial social + social združena v SOCIAL UNIT,
# ker je to trenutna uporabniška logika sistema.
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

    # ========================================================
    # SOCIAL UNIT
    #
    # NAMERNO NAJVIŠJI STRUKTURNI NAGIB
    #
    # Vključuje social + partial-social področja.
    # ========================================================

    "Social unit": [

        # interpersonalni odnosi
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

        # organizacijski/socialni odnosi
        "organizac", "organizaciji", "organizacijo",
        "sestank", "meeting", "meetings", "team", "teamwork",
        "management", "leader", "leadership", "manager",

        # partial-social / status / pravičnost
        "plač", "dohod", "denar", "finanč", "nagrad", "status",
        "priznan", "revšč", "standar", "nepravič", "nestimul",
        "krivic", "dostojen", "zaposlit", "služb", "karier",
        "napredov", "varnost", "staž", "benefic", "ekonom",
        "proračun", "pokojnin", "sredstv", "zamudn", "opomin",
        "kazn", "plačev", "plačilo", "money", "salary",
        "financial", "budget", "stability", "znesek",

        # širši družbeni kontekst
        "družb", "law", "zakon", "orož", "weapon", "alcohol",
        "economic", "level", "standard",

        # neposredni socialni stresorji
        "mobbing", "harassment", "bullying", "conflict",
        "overcrowding", "crowding", "injustice", "punishment",
        "reward", "recognition", "support", "trust"
    ],

    "Health biological unit": [

        "zdrav", "bolniš", "bolezen", "spanj", "utrujen",
        "izčrpan", "higien", "čistoč", "sleep", "rest",
        "dihanje", "izčrpanost", "utrujenost", "zdravje",
        "bolečina", "virus", "infekcij", "higiena", "prehran",
        "diet", "biološ", "fiziolo", "telo", "utrujena",
        "spanja", "telesno", "exhaustion"
    ]
}


# ============================================================
# 6. STRUKTURNI NAGIBI
#
# Osnovna znanstvena logika:
# večja gostota + raznolikost + kompleksnost = večji nagib.
#
# Social unit dobi najvišji STRUKTURNI KOEFICIENT.
#
# To ni nadomestilo za empirične podatke, ampak kalibracijski
# prior, ki upošteva sistemsko/medosebno propagacijo socialnih
# stresorjev, opisano v članku.
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


# ============================================================
# 7. RATING SCALE
# ============================================================

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
# 8. TOKENIZACIJA
# ============================================================

def clean_and_tokenize(text):

    if not isinstance(text, str):
        return []

    text = text.lower()

    text = re.sub(r"[^\w\s]", " ", text)

    words = text.split()

    return [
        w for w in words
        if w not in SLO_STOPWORDS
        and len(w) > 2
    ]


# ============================================================
# 9. KLASIFIKACIJA BESEDE
# ============================================================

def classify_word_single(word):

    # Social unit ima prednost pred bolj splošnimi kategorijami.
    # To je pomembno pri besedah kot:
    # sestanek, vodstvo, organizacija, sodelavec itd.

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


# ============================================================
# 10. ANALIZA STOLPCA
# ============================================================

def analyze_column(df, col):

    classified = []

    per_row_categories = []

    unclassified_words = []

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

    return (
        classified,
        per_row_categories,
        unclassified_words
    )


# ============================================================
# 11. AGREGATNI Fo
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


# ============================================================
# 12. KATEGORIJSKI FAKTORJI
# ============================================================

def compute_category_factors(
    classified,
    n_override,
    weighting_mode="volume"
):

    words_by_cat = defaultdict(list)

    for word, category in classified:

        words_by_cat[category].append(word)

    result = {}

    for category in CATEGORIES_MAP.keys():

        words = words_by_cat.get(category, [])

        fE = len(words)

        frE = len(set(words))

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

        F = (CE * rho) / 10.0

        result[category] = {
            "fE": fE,
            "frE": frE,
            "CE": CE,
            "rho": rho,
            "F": F
        }

    return result


# ============================================================
# 13. OSNOVNI SIGMA ARGUMENT
# ============================================================

def sigma_argument(f_sf, f_pr, f_pf):

    if f_pf <= 0:

        f_pf = 0.0001

    argument = (
        f_sf * f_pr
    ) / f_pf

    return max(argument, 0.0)


def sigma_deg(f_sf, f_pr, f_pf):

    argument = sigma_argument(
        f_sf,
        f_pr,
        f_pf
    )

    argument = min(argument, 1.0)

    sigma_rad = math.asin(
        math.sqrt(argument)
    )

    return math.degrees(sigma_rad)


# ============================================================
# 14. KATEGORIJSKI NAGIB
#
# Tukaj je glavna izboljšava.
#
# Najprej se izračuna osnovni Petričev argument.
# Nato se upošteva strukturni koeficient.
#
# Social unit ima največji nagib.
# ============================================================

def compute_category_sigmas(
    factors_sf,
    factors_pf,
    factors_pr,
    sigma_total_argument,
    is_summary
):

    raw_scores = {}

    raw_arguments = {}

    for category in CATEGORIES_MAP.keys():

        f_pf = factors_pf[category]["F"]

        f_sf = factors_sf[category]["F"]

        f_pr = factors_pr[category]["F"]

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

        structural_weight = SLOPE_WEIGHTS[
            category
        ]

        weighted_score = (
            argument *
            structural_weight
        )

        raw_arguments[category] = argument

        raw_scores[category] = weighted_score

    total_score = sum(
        raw_scores.values()
    )

    results = {}

    if total_score <= 0:

        for category in CATEGORIES_MAP.keys():

            results[category] = {
                "sigma": 0.0,
                "slope_index": 0.0,
                "weight_share": 0.0,
                "raw_argument": 0.0,
                "structural_weight": SLOPE_WEIGHTS[
                    category
                ]
            }

        return results, 0.0

    for category in CATEGORIES_MAP.keys():

        weighted_score = raw_scores[category]

        share = (
            weighted_score /
            total_score
        )

        # Porazdelitev skupnega sigma argumenta.
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

            "slope_index":
                weighted_score,

            "weight_share":
                share,

            "raw_argument":
                raw_arguments[category],

            "structural_weight":
                SLOPE_WEIGHTS[category]
        }

    return results, total_score


# ============================================================
# 15. ENERGIJA
# ============================================================

def calculate_energy(sigma):

    W_I = 2500.0

    W_EU = (
        W_I -
        (W_I * sigma / 90.0)
    )

    eta = (
        W_EU / W_I
    ) * 100.0

    loss = W_I - W_EU

    return W_EU, eta, loss


# ============================================================
# 16. BARVA OCENE
# ============================================================

def rating_class(sigma):

    if sigma <= 30:

        return "stress-low"

    if sigma <= 60:

        return "stress-medium"

    return "stress-high"


# ============================================================
# 17. HAUPTANWENDUNG
# ============================================================

def main():

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    with st.sidebar:

        st.markdown(
            "## ⚙️ Nastavitve"
        )

        if st.button(
            "🔄 Ponastavi aplikacijo",
            use_container_width=True
        ):

            reset_app()

        st.divider()

        st.markdown(
            "### 📊 Raziskovalni parametri"
        )

        n_input = st.number_input(
            "Število respondentov (N)",
            min_value=1,
            value=210,
            step=1
        )

        is_summary = st.checkbox(
            "Datoteka vsebuje POVZETEK",
            value=True
        )

        st.divider()

        st.markdown(
            "### 🧮 Uteževanje"
        )

        weighting_label = st.radio(
            "Način uteževanja",
            [
                "Volumen (frekvenca)",
                "Koncentracija (ponovljivost)"
            ]
        )

        weighting_mode = (
            "volume"
            if "Volumen" in weighting_label
            else "concentration"
        )

        st.divider()

        uploaded_file = st.file_uploader(
            "📁 Naložite podatke",
            type=[
                "txt",
                "csv",
                "xlsx"
            ]
        )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.markdown(
        "# 📊 Petrič Stress Analysis Pro"
    )

    st.markdown(
        """
        **Psihosocialni barometer za klasifikacijo stresnih,
        pozitivnih in intervencijskih dejavnikov.**
        """
    )

    st.caption(
        f"Znanstvena kalibracija • N = {n_input} • "
        "Petričev model gostote, kompleksnosti in nagiba"
    )

    # --------------------------------------------------------
    # UPLOAD
    # --------------------------------------------------------

    if not uploaded_file:

        st.info(
            "📁 Za začetek naložite datoteko "
            "TXT, CSV ali XLSX.",
            icon="ℹ️"
        )

        return

    # --------------------------------------------------------
    # READ FILE
    # --------------------------------------------------------

    try:

        filename = uploaded_file.name.lower()

        if filename.endswith(".xlsx"):

            df = pd.read_excel(
                uploaded_file
            )

        elif filename.endswith(".txt"):

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
            f"Napaka pri branju datoteke: {e}"
        )

        return

    if df.empty:

        st.warning(
            "Datoteka ne vsebuje podatkov."
        )

        return

    # --------------------------------------------------------
    # DATA INFO
    # --------------------------------------------------------

    st.success(
        f"✅ Uspešno naloženih {len(df)} vrstic."
    )

    target_cols = df.columns.tolist()

    if len(target_cols) == 0:

        st.error(
            "Datoteka nima uporabnih stolpcev."
        )

        return

    # --------------------------------------------------------
    # COLUMN SELECTION
    # --------------------------------------------------------

    with st.sidebar:

        st.markdown(
            "### 🧩 Vrste podatkov"
        )

        col_pf = st.selectbox(
            "🟢 Pozitivni faktorji (PF)",
            target_cols,
            index=0
        )

        col_sf = st.selectbox(
            "🔴 Stresni faktorji (SF)",
            target_cols,
            index=min(
                1,
                len(target_cols) - 1
            )
        )

        col_pr = st.selectbox(
            "🔵 Predlogi (PR)",
            target_cols,
            index=min(
                2,
                len(target_cols) - 1
            )
        )

    role_cols = {
        "PF": col_pf,
        "SF": col_sf,
        "PR": col_pr
    }

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    analysis = {}

    for role, col in role_cols.items():

        classified, per_row, unclassified = (
            analyze_column(
                df,
                col
            )
        )

        analysis[role] = {

            "col": col,

            "classified":
                classified,

            "per_row":
                per_row,

            "unclassified":
                unclassified
        }

    # ========================================================
    # 18. GLOBALNI Fo
    # ========================================================

    f_pf_agg, pf_fo, pf_fr = (
        calculate_fo_real_aggregate(
            analysis["PF"]["classified"],
            n_input
        )
    )

    f_sf_agg, sf_fo, sf_fr = (
        calculate_fo_real_aggregate(
            analysis["SF"]["classified"],
            n_input
        )
    )

    f_pr_agg, pr_fo, pr_fr = (
        calculate_fo_real_aggregate(
            analysis["PR"]["classified"],
            n_input
        )
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

    # ========================================================
    # 19. ENERGY
    # ========================================================

    W_EU, eta, loss = (
        calculate_energy(
            sigma_total
        )
    )

    # ========================================================
    # 20. HERO METRICS
    # ========================================================

    st.markdown(
        "## 🎯 Osrednji rezultat"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    Stresna moč
                </div>
                <div class="metric-value">
                    {sigma_total:.2f} °S
                </div>
                <div class="metric-description">
                    {rate_sigma(sigma_total)}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    Učinkovitost
                </div>
                <div class="metric-value">
                    {eta:.1f} %
                </div>
                <div class="metric-description">
                    Energijska učinkovitost
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    Izguba energije
                </div>
                <div class="metric-value">
                    {loss:.0f}
                </div>
                <div class="metric-description">
                    ocenjenih Kcal
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    Respondenti
                </div>
                <div class="metric-value">
                    {n_input}
                </div>
                <div class="metric-description">
                    analizirani vzorec
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.progress(
        min(
            sigma_total / 90.0,
            1.0
        )
    )

    # ========================================================
    # 21. Fo
    # ========================================================

    with st.expander(
        "📐 Podrobnosti Petričevih faktorjev Fo"
    ):

        fo_df = pd.DataFrame({

            "Vrsta": [
                "PF – pozitivni",
                "SF – stresni",
                "PR – predlogi"
            ],

            "Fo": [
                f_pf_agg,
                f_sf_agg,
                f_pr_agg
            ],

            "Frekvenca": [
                pf_fo,
                sf_fo,
                pr_fo
            ],

            "Različne enote": [
                pf_fr,
                sf_fr,
                pr_fr
            ]
        })

        st.dataframe(
            fo_df,
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # 22. KATEGORIJSKI FAKTORJI
    # ========================================================

    factors_pf = compute_category_factors(
        analysis["PF"]["classified"],
        n_input,
        weighting_mode
    )

    factors_sf = compute_category_factors(
        analysis["SF"]["classified"],
        n_input,
        weighting_mode
    )

    factors_pr = compute_category_factors(
        analysis["PR"]["classified"],
        n_input,
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

    cat_sigmas, total_slope = (
        compute_category_sigmas(
            factors_sf,
            factors_pf,
            factors_pr,
            sig_total_arg,
            is_summary
        )
    )

    # ========================================================
    # 23. REZULTATI PO ENOTAH
    # ========================================================

    st.divider()

    st.markdown(
        "## 🧩 Stresna moč po znanstvenih enotah"
    )

    rows = []

    for category, data in cat_sigmas.items():

        rows.append({

            "Enota":
                CATEGORY_SHORT[category],

            "Polno ime":
                category,

            "σ (°S)":
                round(
                    data["sigma"],
                    2
                ),

            "Delež (%)":
                round(
                    data["weight_share"] * 100,
                    1
                ),

            "Nagib":
                round(
                    data["slope_index"],
                    5
                ),

            "Koeficient":
                data["structural_weight"],

            "Ocena":
                rate_sigma(
                    data["sigma"]
                )
        })

    res_df = pd.DataFrame(
        rows
    ).sort_values(
        by="Nagib",
        ascending=False
    ).reset_index(
        drop=True
    )

    res_df.insert(
        0,
        "Rang",
        range(
            1,
            len(res_df) + 1
        )
    )

    # ========================================================
    # 24. SOCIAL UNIT – HERO CARD
    # ========================================================

    social = cat_sigmas[
        "Social unit"
    ]

    st.markdown(
        f"""
        <div class="social-card">
            <div style="
                font-size:0.85rem;
                color:#9a3412;
                font-weight:700;
                text-transform:uppercase;
                letter-spacing:1px;
            ">
                🔶 Najmočnejši strukturni nagib
            </div>

            <div style="
                font-size:2.2rem;
                font-weight:850;
                margin-top:6px;
            ">
                Social unit
            </div>

            <div style="
                font-size:1.25rem;
                margin-top:5px;
            ">
                σ = <b>{social["sigma"]:.2f} °S</b>
                &nbsp; | &nbsp;
                delež = <b>{social["weight_share"]*100:.1f}%</b>
            </div>

            <div style="
                margin-top:8px;
                color:#7c2d12;
            ">
                Strukturni koeficient:
                <b>{social["structural_weight"]:.2f}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("")

    # ========================================================
    # 25. TABELA
    # ========================================================

    st.dataframe(
        res_df,
        use_container_width=True,
        hide_index=True,
        column_config={

            "σ (°S)": st.column_config.NumberColumn(
                "Stresna moč °S",
                format="%.2f"
            ),

            "Delež (%)": st.column_config.NumberColumn(
                "Delež",
                format="%.1f %%"
            ),

            "Nagib": st.column_config.NumberColumn(
                "Strukturni nagib",
                format="%.5f"
            ),

            "Koeficient": st.column_config.NumberColumn(
                "Strukturni koeficient",
                format="%.2f"
            )
        }
    )

    # ========================================================
    # 26. GRAF NAGIBA
    # ========================================================

    st.markdown(
        "### 📈 Primerjava strukturnega nagiba"
    )

    chart_df = res_df.copy()

    fig = px.bar(
        chart_df,
        x="Enota",
        y="Nagib",
        text="Nagib",
        title=(
            "Strukturni nagib stresnih enot"
        )
    )

    fig.update_traces(
        texttemplate="%{text:.4f}",
        textposition="outside"
    )

    fig.update_layout(
        height=430,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=30
        ),
        xaxis_title="",
        yaxis_title="Strukturni nagib",
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ========================================================
    # 27. GRAF STRESNE MOČI
    # ========================================================

    st.markdown(
        "### 🔥 Stresna moč po enotah"
    )

    fig2 = px.bar(
        res_df,
        x="Enota",
        y="σ (°S)",
        text="σ (°S)",
        title="Stresna moč po znanstvenih enotah"
    )

    fig2.update_traces(
        texttemplate="%{text:.2f}°S",
        textposition="outside"
    )

    fig2.update_layout(
        height=430,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=30
        ),
        xaxis_title="",
        yaxis_title="Stresna moč °S",
        showlegend=False
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # ========================================================
    # 28. KVALITATIVNA ANALIZA
    # ========================================================

    st.divider()

    st.markdown(
        "## 🔍 Kvalitativna klasifikacija"
    )

    tabs = st.tabs([
        "🟢 PF",
        "🔴 SF",
        "🔵 PR"
    ])

    for tab, role in zip(
        tabs,
        ["PF", "SF", "PR"]
    ):

        with tab:

            freq_counter = Counter(
                category
                for _, category
                in analysis[role]["classified"]
            )

            freq_rows = []

            for category, count in (
                freq_counter.most_common()
            ):

                freq_rows.append({

                    "Enota":
                        CATEGORY_SHORT.get(
                            category,
                            category
                        ),

                    "Frekvenca":
                        count
                })

            if freq_rows:

                freq_df = pd.DataFrame(
                    freq_rows
                )

                st.dataframe(
                    freq_df,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "Za to področje ni bilo klasificiranih izrazov."
                )

    # ========================================================
    # 29. NEKLASIFICIRANE BESEDE
    # ========================================================

    with st.expander(
        "🧠 Pregled neklasificiranih izrazov"
    ):

        all_unclassified = []

        for role in [
            "PF",
            "SF",
            "PR"
        ]:

            all_unclassified.extend(
                analysis[role]["unclassified"]
            )

        counter_unclassified = Counter(
            all_unclassified
        )

        if counter_unclassified:

            unclassified_df = pd.DataFrame(
                counter_unclassified.most_common(50),
                columns=[
                    "Izraz",
                    "Frekvenca"
                ]
            )

            st.dataframe(
                unclassified_df,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "Ti izrazi niso bili samodejno povezani "
                "z nobeno znanstveno enoto. To je uporabno "
                "za nadaljnje izboljševanje klasifikacijskega slovarja."
            )

        else:

            st.success(
                "Vsi relevantni izrazi so bili klasificirani."
            )

    # ========================================================
    # 30. INTERPRETACIJA
    # ========================================================

    st.divider()

    st.markdown(
        "## 🧭 Interpretacija rezultata"
    )

    top_category = res_df.iloc[0]

    st.markdown(
        f"""
        **Najmočnejši strukturni nagib:**  
        ### {top_category["Enota"]}

        Izračun kaže, da ima ta enota najvišji kombinirani
        strukturni indeks, ki upošteva frekvenco oziroma
        gostoto klasificiranih mnenj, njihovo raznolikost
        ter strukturni koeficient enote.

        Pri tem je **Social unit** kalibrirana kot najmočnejša
        sistemska enota, ker socialni odnosi, konflikti,
        komunikacija, vodenje, organizacijska klima,
        pripadnost, pravičnost in statusni dejavniki lahko
        vplivajo tudi na druge stresne domene.
        """
    )

    st.info(
        """
        Znanstvena opomba: strukturni koeficient ni neposredna
        empirična meritev iz posameznega vzorca, temveč kalibracijski
        element modela. Empirični del rezultata še vedno določajo
        dejanska gostota, frekvenca, raznolikost in kompleksnost
        odgovorov.
        """
    )

    # ========================================================
    # 31. METODOLOŠKA OPOMBA
    # ========================================================

    with st.expander(
        "📚 Metodološka osnova"
    ):

        st.markdown(
            """
            **Petričev model**

            Analiza uporablja tri osnovne tipe informacij:

            **SF** – negativni stresni dejavniki  
            **PF** – pozitivni dejavniki  
            **PR** – predlogi za zmanjšanje negativnih dejavnikov.

            Kategorijski rezultat temelji na razmerju med
            gostoto, raznolikostjo in kompleksnostjo dejavnikov.

            Model uporablja tudi nelinearno transformacijo
            z arcsin/sqrt pristopom, da se rezultat izrazi
            v stopinjah stresne moči.

            Za interpretacijo posameznih enot je dodatno uporabljen
            strukturni nagib. Socialna enota ima najvišji koeficient,
            vendar končni rezultat še vedno temelji na dejanskih
            podatkih iz analiziranega vzorca.
            """
        )


# ============================================================
# 32. ZAGON
# ============================================================

if __name__ == "__main__":
    main()
```


