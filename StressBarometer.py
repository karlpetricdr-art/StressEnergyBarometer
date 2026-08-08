import streamlit as st
import pandas as pd
import re
import math
from collections import Counter, defaultdict
import plotly.express as px

st.set_page_config(
    page_title="Petrič Stress Analysis Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# RESET
# ============================================================

def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================
# ESTETIKA
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
</style>
""", unsafe_allow_html=True)


# ============================================================
# STOPWORDS
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
    "tem", "the", "and", "to", "of", "a", "is", "it", "with", "some",
    "more", "being", "able", "use", "make", "nice", "your", "this",
    "that", "from", "for", "are", "was", "were"
}


# ============================================================
# ZNANSTVENA KLASIFIKACIJA
# ============================================================

CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem",
        "prostor", "pisarn", "ergonom", "oprem", "tišin", "zrak",
        "prah", "gneč", "tehni", "poškodb", "varna", "objekt",
        "sodobn", "naprav", "urejenost", "etiket", "izolac",
        "barv", "rastlin", "vonjav", "stol", "miz", "prezrač",
        "notranj", "environment", "lighting", "toplota", "hlad",
        "umazano", "onesnaž", "arhitekt", "opremljenost",
        "hrupn", "svetloba", "tišina", "glasb", "rož", "cvet"
    ],
    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "čas",
        "administra", "birokra", "obrazc", "poročil", "postopk",
        "navodil", "veščin", "hitenj", "naglic", "stisk",
        "preobremen", "neizkušn", "učinkovit", "biro", "togi",
        "rutin", "nujne", "izobraž", "usposab", "proces",
        "poenostav", "inovac", "rešitev", "urnik", "ure",
        "izvajanj", "regula", "direktiv", "iskanj", "gradiv",
        "podatkov", "nalog", "job", "goal", "cilj", "študij",
        "raziskav", "iskanje", "tasks", "program", "training",
        "exercise", "aktiv", "šport", "rekreac", "tek", "joga",
        "plavanj", "kolo"
    ],
    "Individual Psychological unit": [
        "strah", "tesnob", "samozav", "čustv", "stres", "frustr",
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb",
        "napetos", "psih", "travm", "osebno", "samopodob",
        "nasil", "negativ", "dušev", "žalost", "ogroženost",
        "nelagod", "zadovolj", "nemir", "choice", "life",
        "memory", "spomin", "art", "umetnos", "irrational",
        "uncertain", "uncertainty", "peace", "feeling", "hope",
        "values", "vrednot", "ponižanj", "identitet", "dopust",
        "izlet", "potovan", "sprošč", "relax", "medit", "dihan",
        "narav", "spomini", "praznina", "osebnost", "samokontrol"
    ],
    "Social unit": [
        "odnos", "odnosih", "odnosov", "mobing", "šikan", "sodelav",
        "sodelovanje", "sodelov", "šef", "vodstv", "nadrejen",
        "družin", "prijatel", "komunik", "pogovor", "prepir",
        "zahrbt", "vzvišen", "nesram", "aroganc", "egoiz", "podpor",
        "konflikt", "intrig", "neiskren", "rival", "polit", "hierarh",
        "timsko", "druženj", "domače", "kader", "sovrašt", "grožn",
        "profesional", "uporabnik", "osebj", "človek", "friend",
        "family", "talk", "partnership", "spouse", "zaupan",
        "vodenj", "klima", "vzdušje", "ignor", "nerazum", "posluš",
        "sektor", "direktor", "vodja", "pripadnost", "rivalstvo",
        "friends", "organizac", "organizaciji", "organizacijo",
        "sestank", "meeting", "meetings", "team", "teamwork",
        "management", "leader", "leadership", "manager",
        "plač", "dohod", "denar", "finanč", "nagrad", "status",
        "priznan", "revšč", "standar", "nepravič", "nestimul",
        "krivic", "dostojen", "zaposlit", "služb", "karier",
        "napredov", "varnost", "staž", "benefic", "ekonom",
        "proračun", "pokojnin", "sredstv", "zamudn", "opomin",
        "kazn", "plačev", "plačilo", "money", "salary", "financial",
        "budget", "stability", "znesek", "družb", "zakon", "law",
        "economic", "level", "standard", "mobbing", "harassment",
        "bullying", "conflict", "overcrowding", "crowding",
        "injustice", "punishment", "reward", "recognition",
        "support", "trust"
    ],
    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "spanj", "utrujen", "izčrpan",
        "higien", "čistoč", "sleep", "rest", "dihanje", "izčrpanost",
        "utrujenost", "zdravje", "bolečina", "virus", "infekcij",
        "higiena", "prehran", "diet", "biološ", "fiziolo", "telo",
        "telesno", "exhaustion"
    ]
}


# Social unit je namerno najmočnejša strukturna enota.
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
# POMOŽNE FUNKCIJE
# ============================================================

def rate_sigma(sigma):
    if sigma <= 15:
        return "Zelo nizka"
    if sigma <= 30:
        return "Nizka"
    if sigma <= 45:
        return "Srednja"
    if sigma <= 60:
        return "Višja"
    if sigma <= 75:
        return "Visoka"
    return "Zelo visoka"


def clean_and_tokenize(text):
    if not isinstance(text, str):
        return []

    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()

    return [
        word for word in words
        if word not in SLO_STOPWORDS and len(word) > 2
    ]


def classify_word_single(word):
    # Social unit ima prednost, da organizacijski in
    # medosebni pojmi ne končajo v splošni kategoriji.
    priority_order = [
        "Social unit",
        "Performance unit",
        "Individual Psychological unit",
        "Health biological unit",
        "Attentive (physical) unit"
    ]

    for category in priority_order:
        for root in CATEGORIES_MAP[category]:
            if root in word:
                return category

    return None


def analyze_column(df, column):
    classified = []
    per_row_categories = []
    unclassified_words = []

    for value in df[column].dropna():
        words = clean_and_tokenize(value)
        row_categories = []

        for word in words:
            category = classify_word_single(word)

            if category:
                classified.append((word, category))
                row_categories.append(category)
            else:
                unclassified_words.append(word)

        per_row_categories.append(row_categories)

    return classified, per_row_categories, unclassified_words


def calculate_fo_real_aggregate(classified, n):
    words = [word for word, _ in classified]
    fo = len(words)
    fr = len(set(words))

    if fr == 0 or n <= 0:
        return 0.0001, fo, fr

    rho = fo / n
    complexity = fo / fr
    fo_real = (complexity * rho) / 10.0

    return fo_real, fo, fr


def compute_category_factors(classified, n, weighting_mode="volume"):
    words_by_category = defaultdict(list)

    for word, category in classified:
        words_by_category[category].append(word)

    result = {}

    for category in CATEGORIES_MAP:
        words = words_by_category.get(category, [])

        f_e = len(words)
        fr_e = len(set(words))

        if weighting_mode == "concentration":
            complexity = f_e / fr_e if fr_e else 0.0001
        else:
            complexity = 1.0

        density = f_e / n if n else 0.0
        factor = (complexity * density) / 10.0

        result[category] = {
            "fE": f_e,
            "frE": fr_e,
            "CE": complexity,
            "rho": density,
            "F": factor
        }

    return result


def sigma_argument(f_sf, f_pr, f_pf):
    denominator = max(f_pf, 0.0001)
    return max((f_sf * max(f_pr, 0.0001)) / denominator, 0.0)


def sigma_deg(f_sf, f_pr, f_pf):
    argument = min(sigma_argument(f_sf, f_pr, f_pf), 1.0)
    return math.degrees(math.asin(math.sqrt(argument)))


def compute_category_sigmas(
    factors_sf,
    factors_pf,
    factors_pr,
    sigma_total_argument,
    is_summary
):
    raw_scores = {}
    raw_arguments = {}

    for category in CATEGORIES_MAP:
        f_sf = factors_sf[category]["F"]
        f_pf = factors_pf[category]["F"]
        f_pr = factors_pr[category]["F"]

        if is_summary and f_sf > 0:
            f_pr = min(f_pr, f_sf * 1.5)

        argument = sigma_argument(f_sf, f_pr, f_pf)
        structural_weight = SLOPE_WEIGHTS[category]
        weighted_score = argument * structural_weight

        raw_arguments[category] = argument
        raw_scores[category] = weighted_score

    total_score = sum(raw_scores.values())
    results = {}

    if total_score <= 0:
        for category in CATEGORIES_MAP:
            results[category] = {
                "sigma": 0.0,
                "slope_index": 0.0,
                "weight_share": 0.0,
                "raw_argument": 0.0,
                "structural_weight": SLOPE_WEIGHTS[category]
            }
        return results, 0.0

    for category in CATEGORIES_MAP:
        score = raw_scores[category]
        share = score / total_score
        scaled_argument = min(sigma_total_argument * share, 1.0)

        sigma = math.degrees(
            math.asin(math.sqrt(scaled_argument))
        )

        results[category] = {
            "sigma": sigma,
            "slope_index": score,
            "weight_share": share,
            "raw_argument": raw_arguments[category],
            "structural_weight": SLOPE_WEIGHTS[category]
        }

    return results, total_score


def calculate_energy(sigma):
    W_I = 2500.0
    W_EU = W_I - (W_I * sigma / 90.0)
    efficiency = (W_EU / W_I) * 100.0
    loss = W_I - W_EU

    return W_EU, efficiency, loss


# ============================================================
# GLAVNA APLIKACIJA
# ============================================================

def main():

    with st.sidebar:
        st.markdown("## ⚙️ Nastavitve")

        if st.button(
            "🔄 Ponastavi aplikacijo",
            use_container_width=True
        ):
            reset_app()

        st.divider()

        st.markdown("### 📊 Raziskovalni parametri")

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

        st.markdown("### 🧮 Uteževanje")

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
            type=["txt", "csv", "xlsx"]
        )

    st.markdown("# 📊 Petrič Stress Analysis Pro")
    st.markdown(
        "**Psihosocialni barometer za klasifikacijo stresnih, "
        "pozitivnih in intervencijskih dejavnikov.**"
    )
    st.caption(
        f"Petričev model gostote, kompleksnosti in strukturnega "
        f"nagiba • N = {n_input}"
    )

    if not uploaded_file:
        st.info(
            "📁 Za začetek naložite datoteko TXT, CSV ali XLSX.",
            icon="ℹ️"
        )
        return

    try:
        filename = uploaded_file.name.lower()

        if filename.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)

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

    except Exception as exc:
        st.error(f"Napaka pri branju datoteke: {exc}")
        return

    if df.empty:
        st.warning("Datoteka ne vsebuje podatkov.")
        return

    st.success(
        f"✅ Uspešno naloženih {len(df)} vrstic."
    )

    target_cols = df.columns.tolist()

    if not target_cols:
        st.error("Datoteka nima uporabnih stolpcev.")
        return

    with st.sidebar:
        st.markdown("### 🧩 Vrste podatkov")

        col_pf = st.selectbox(
            "🟢 Pozitivni faktorji (PF)",
            target_cols,
            index=0
        )

        col_sf = st.selectbox(
            "🔴 Stresni faktorji (SF)",
            target_cols,
            index=min(1, len(target_cols) - 1)
        )

        col_pr = st.selectbox(
            "🔵 Predlogi (PR)",
            target_cols,
            index=min(2, len(target_cols) - 1)
        )

    role_cols = {
        "PF": col_pf,
        "SF": col_sf,
        "PR": col_pr
    }

    analysis = {}

    for role, column in role_cols.items():
        classified, per_row, unclassified = analyze_column(
            df,
            column
        )

        analysis[role] = {
            "col": column,
            "classified": classified,
            "per_row": per_row,
            "unclassified": unclassified
        }

    # --------------------------------------------------------
    # GLOBALNI FAKTORJI
    # --------------------------------------------------------

    f_pf, pf_fo, pf_fr = calculate_fo_real_aggregate(
        analysis["PF"]["classified"],
        n_input
    )

    f_sf, sf_fo, sf_fr = calculate_fo_real_aggregate(
        analysis["SF"]["classified"],
        n_input
    )

    f_pr, pr_fo, pr_fr = calculate_fo_real_aggregate(
        analysis["PR"]["classified"],
        n_input
    )

    if is_summary:
        f_pr = min(f_pr, f_sf * 1.5)

    sigma_total = sigma_deg(
        f_sf,
        f_pr,
        f_pf
    )

    W_EU, efficiency, loss = calculate_energy(
        sigma_total
    )

    # --------------------------------------------------------
    # HERO
    # --------------------------------------------------------

    st.markdown("## 🎯 Osrednji rezultat")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Stresna moč</div>
                <div class="metric-value">{sigma_total:.2f} °S</div>
                <div class="metric-description">{rate_sigma(sigma_total)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Učinkovitost</div>
                <div class="metric-value">{efficiency:.1f} %</div>
                <div class="metric-description">energijska učinkovitost</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Izguba energije</div>
                <div class="metric-value">{loss:.0f}</div>
                <div class="metric-description">ocenjenih energijskih enot</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">Respondenti</div>
                <div class="metric-value">{n_input}</div>
                <div class="metric-description">analizirani vzorec</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.progress(min(sigma_total / 90.0, 1.0))

    # --------------------------------------------------------
    # Fo
    # --------------------------------------------------------

    with st.expander("📐 Podrobnosti Petričevih faktorjev Fo"):
        fo_df = pd.DataFrame({
            "Vrsta": [
                "PF – pozitivni",
                "SF – stresni",
                "PR – predlogi"
            ],
            "Fo": [
                f_pf,
                f_sf,
                f_pr
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

    # --------------------------------------------------------
    # KATEGORIJE
    # --------------------------------------------------------

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

    sigma_total_argument = min(
        sigma_argument(
            f_sf,
            f_pr,
            f_pf
        ),
        1.0
    )

    category_results, total_slope = compute_category_sigmas(
        factors_sf,
        factors_pf,
        factors_pr,
        sigma_total_argument,
        is_summary
    )

    # --------------------------------------------------------
    # TABELA REZULTATOV
    # --------------------------------------------------------

    st.divider()
    st.markdown("## 🧩 Stresna moč po znanstvenih enotah")

    rows = []

    for category, result in category_results.items():
        rows.append({
            "Enota": CATEGORY_SHORT[category],
            "Polno ime": category,
            "σ (°S)": round(result["sigma"], 2),
            "Delež (%)": round(
                result["weight_share"] * 100,
                1
            ),
            "Nagib": round(
                result["slope_index"],
                5
            ),
            "Koeficient": result["structural_weight"],
            "Ocena": rate_sigma(result["sigma"])
        })

    result_df = (
        pd.DataFrame(rows)
        .sort_values(
            "Nagib",
            ascending=False
        )
        .reset_index(drop=True)
    )

    result_df.insert(
        0,
        "Rang",
        range(1, len(result_df) + 1)
    )

    # --------------------------------------------------------
    # SOCIAL UNIT
    # --------------------------------------------------------

    social = category_results["Social unit"]

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
                delež = <b>{social["weight_share"] * 100:.1f}%</b>
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

    st.dataframe(
        result_df,
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

    # --------------------------------------------------------
    # GRAF NAGIBA
    # --------------------------------------------------------

    st.markdown("### 📈 Primerjava strukturnega nagiba")

    slope_df = result_df.copy()

    fig_slope = px.bar(
        slope_df,
        x="Enota",
        y="Nagib",
        text="Nagib",
        title="Strukturni nagib stresnih enot"
    )

    fig_slope.update_traces(
        texttemplate="%{text:.4f}",
        textposition="outside"
    )

    fig_slope.update_layout(
        height=430,
        margin=dict(l=20, r=20, t=60, b=30),
        xaxis_title="",
        yaxis_title="Strukturni nagib",
        showlegend=False
    )

    st.plotly_chart(
        fig_slope,
        use_container_width=True
    )

    # --------------------------------------------------------
    # GRAF STRESNE MOČI
    # --------------------------------------------------------

    st.markdown("### 🔥 Stresna moč po enotah")

    fig_sigma = px.bar(
        result_df,
        x="Enota",
        y="σ (°S)",
        text="σ (°S)",
        title="Stresna moč po znanstvenih enotah"
    )

    fig_sigma.update_traces(
        texttemplate="%{text:.2f}°S",
        textposition="outside"
    )

    fig_sigma.update_layout(
        height=430,
        margin=dict(l=20, r=20, t=60, b=30),
        xaxis_title="",
        yaxis_title="Stresna moč °S",
        showlegend=False
    )

    st.plotly_chart(
        fig_sigma,
        use_container_width=True
    )

    # --------------------------------------------------------
    # KVALITATIVNA KLASIFIKACIJA
    # --------------------------------------------------------

    st.divider()
    st.markdown("## 🔍 Kvalitativna klasifikacija")

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
            counter = Counter(
                category
                for _, category
                in analysis[role]["classified"]
            )

            frequency_rows = []

            for category, count in counter.most_common():
                frequency_rows.append({
                    "Enota": CATEGORY_SHORT.get(
                        category,
                        category
                    ),
                    "Polno ime": category,
                    "Frekvenca": count
                })

            if frequency_rows:
                frequency_df = pd.DataFrame(
                    frequency_rows
                )

                st.dataframe(
                    frequency_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info(
                    "Za to področje ni bilo klasificiranih izrazov."
                )

    # --------------------------------------------------------
    # NEKLASIFICIRANI IZRAZI
    # --------------------------------------------------------

    with st.expander(
        "🧠 Pregled neklasificiranih izrazov"
    ):
        all_unclassified = []

        for role in ["PF", "SF", "PR"]:
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
                "Neklasificirani izrazi so uporabni za nadaljnje "
                "izboljševanje znanstvenega klasifikacijskega slovarja."
            )
        else:
            st.success(
                "Vsi relevantni izrazi so bili klasificirani."
            )

    # --------------------------------------------------------
    # INTERPRETACIJA
    # --------------------------------------------------------

    st.divider()
    st.markdown("## 🧭 Interpretacija rezultata")

    top_category = result_df.iloc[0]

    st.markdown(
        f"""
**Najmočnejši strukturni nagib:**  
### {top_category["Enota"]}

Model združuje gostoto oziroma frekvenco dejavnikov,
njihovo raznolikost/kompleksnost ter strukturni koeficient
posamezne znanstvene enote.

**Social unit** ima v modelu najvišji strukturni koeficient,
zato predstavlja najmočnejši potencialni sistemski nagib.
To je skladno s konceptualnim izhodiščem, da lahko socialni
in organizacijski stresorji vplivajo tudi na psihološke,
delovne in zdravstvene posledice.
"""
    )

    st.info(
        "Strukturni koeficient je kalibracijski element modela; "
        "empirični del rezultata izhaja iz dejanske frekvence, "
        "gostote in raznolikosti analiziranih odgovorov."
    )

    # --------------------------------------------------------
    # METODOLOŠKA OSNOVA
    # --------------------------------------------------------

    with st.expander("📚 Metodološka osnova"):
        st.markdown(
            """
**Petričev model**

SF = negativni stresni dejavniki  
PF = pozitivni dejavniki  
PR = predlogi za zmanjšanje negativnih dejavnikov.

Kategorijska analiza uporablja šest znanstveno opredeljenih
področij:

1. Attentive (physical) unit
2. Performance unit
3. Individual Psychological unit
4. Social unit
5. Health biological unit

Social unit je v tej aplikacijski različici posebej poudarjena
z najvišjim strukturnim koeficientom, ker predstavlja področje
medosebnih, organizacijskih, statusnih in socialnih odnosov.
"""
        )


if __name__ == "__main__":
    main()


