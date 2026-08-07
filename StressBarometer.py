import streamlit as st
import pandas as pd
import re
import math
from collections import Counter


# ============================================================
# 1. DEFINICIJA STOP-WORDS (MAŠIL)
# ============================================================

SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa",
    "že", "tudi", "iz", "za", "še", "samo", "tako", "kot",
    "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bila", "v", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd",
    "the", "and", "to", "of", "a", "is", "in", "it"
}


# ============================================================
# 2. KLASIFIKACIJSKI MODEL PO ČLANKU (PETRIČ, 2025)
# ============================================================

CATEGORIES_MAP = {

    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "lightning",
        "vročina", "mraz", "cold", "weather", "vreme",
        "prostori", "office", "pisarna", "ergonomija",
        "equipment", "oprema", "tišina", "silence"
    ],

    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload",
        "naloge", "tasks", "čas", "time", "administration",
        "birokracija", "informacije", "information",
        "skills", "znanje", "delovni čas", "urgency"
    ],

    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism",
        "pozitivno", "self-confidence", "samozavest",
        "emotions", "čustva", "stres", "stress",
        "frustracija", "frustration", "peace", "mir"
    ],

    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance",
        "nagrada", "reward", "status", "recognition",
        "priznanje", "poverty", "revščina", "standard",
        "inequality", "nepravičnost"
    ],

    "Social unit": [
        "odnosi", "relationships", "mobing", "mobbing",
        "bullying", "harassment", "sodelavci", "colleagues",
        "šef", "boss", "družina", "family", "prijatelji",
        "friends", "komunikacija", "communication", "prepir"
    ],

    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport",
        "sports", "exercise", "prehrana", "diet", "spanje",
        "sleep", "utrujenost", "tiredness", "joga", "yoga",
        "meditacija", "meditation"
    ]
}


# ============================================================
# 3. POMOŽNE FUNKCIJE ZA OBDELAVO BESEDILA
# ============================================================

def clean_and_tokenize(text):
    """
    Očisti besedilo, odstrani mašila in vrne ključne besede.
    """

    if not isinstance(text, str):
        return []

    text = text.lower()

    text = re.sub(
        r"[^\w\s]",
        " ",
        text
    )

    words = text.split()

    keywords = [
        w
        for w in words
        if w not in SLO_STOPWORDS
        and len(w) > 2
    ]

    return keywords


def classify_keywords(keywords):
    """
    Razvrsti ključne besede v 6 kategorij
    po Petričevi metodi.
    """

    found_categories = []

    for word in keywords:

        for cat, kw_list in CATEGORIES_MAP.items():

            if any(
                kw in word
                for kw in kw_list
            ):

                found_categories.append(cat)

    return found_categories


# ============================================================
# 4. POMOČ PRI DOLOČANJU TIPOV STOLPCEV
# ============================================================

def identify_column_type(column_name):

    name = str(column_name).lower()

    # stresni dejavniki
    if (
        "stres" in name
        or "stress" in name
    ):
        return "SF"

    # pozitivni dejavniki
    if (
        "pozitiv" in name
        or "positive" in name
    ):
        return "PF"

    # predlogi
    if (
        "predlog" in name
        or "proposal" in name
        or "redukc" in name
        or "reduc" in name
    ):
        return "PR"

    return None


# ============================================================
# 5. IZRAČUN REALNEGA FAKTORJA PO ČLANKU
# ============================================================

def calculate_real_factor(
    total_frequency,
    diverse_frequency,
    number_of_respondents
):
    """
    F_o = C_o * rho_o / (C_t * rho_t)

    C_o = total_frequency / diverse_frequency

    rho_o = total_frequency / number_of_respondents

    C_t = 1
    rho_t = 10
    """

    if (
        total_frequency <= 0
        or diverse_frequency <= 0
        or number_of_respondents <= 0
    ):
        return 0.0

    complexity = (
        total_frequency
        / diverse_frequency
    )

    density = (
        total_frequency
        / number_of_respondents
    )

    theoretical_complexity = 1.0
    theoretical_density = 10.0

    factor = (
        complexity * density
        /
        (
            theoretical_complexity
            * theoretical_density
        )
    )

    return factor


# ============================================================
# 6. IZRAČUN STRESNE MOČI
# ============================================================

def calculate_stress_power(
    F_SF,
    F_PF,
    F_PR
):
    """
    Petričeva formula:

    σSF = arcsin(
        sqrt(
            (F_SF * F_PR) / F_PF
        )
    )

    Rezultat je v stopinjah.
    """

    if F_PF <= 0:
        return None

    ratio = (
        F_SF * F_PR
    ) / F_PF

    # Numerična zaščita
    ratio = max(
        0.0,
        min(1.0, ratio)
    )

    sigma_radians = math.asin(
        math.sqrt(ratio)
    )

    sigma_degrees = math.degrees(
        sigma_radians
    )

    return sigma_degrees


# ============================================================
# 7. GLAVNA STREAMLIT APLIKACIJA
# ============================================================

def main():

    st.set_page_config(
        page_title="Stress Analysis Pro",
        layout="wide"
    )

    st.title(
        "📊 Klasifikacija stresnih dejavnikov "
        "po Petričevi metodi"
    )

    st.markdown(
        """
        Sistem analizira odgovore respondentov, odstrani mašila,
        izlušči ključne besede in jih klasificira v
        **6 znanstvenih kategorij**.

        Na osnovi celotnih frekvenc SF, PF in PR se dodatno
        izračuna **celokupna stresna moč σSF v stresnih stopinjah °S**.
        """
    )

    # ========================================================
    # RESET
    # ========================================================

    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0

    if st.sidebar.button(
        "🔄 RESET ANALIZE",
        use_container_width=True
    ):

        st.session_state.reset_counter += 1

        for key in list(st.session_state.keys()):

            if key != "reset_counter":
                del st.session_state[key]

        st.rerun()

    # ========================================================
    # NALAGANJE PODATKOV
    # ========================================================

    uploaded_file = st.sidebar.file_uploader(
        "Naložite .txt ali .csv datoteko",
        type=["txt", "csv"],
        key=f"uploader_{st.session_state.reset_counter}"
    )

    if uploaded_file is None:

        st.info(
            "Prosim, naložite datoteko na levi strani, "
            "da pričnemo z analizo."
        )

        return

    # ========================================================
    # BRANJE DATOTEKE
    # ========================================================

    try:

        if uploaded_file.name.lower().endswith(".txt"):

            try:

                df = pd.read_csv(
                    uploaded_file,
                    sep="\t"
                )

            except Exception:

                uploaded_file.seek(0)

                df = pd.read_csv(
                    uploaded_file,
                    sep=None,
                    engine="python"
                )

        else:

            df = pd.read_csv(
                uploaded_file
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

    st.success(
        f"Uspešno naloženo: {len(df)} vrstic."
    )

    # ========================================================
    # PREGLED SUROVIH PODATKOV
    # ========================================================

    with st.expander(
        "👁️ Pregled surovih podatkov"
    ):

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

    # ========================================================
    # STOLPCI
    # ========================================================

    target_cols = df.columns.tolist()

    results = {}

    # ========================================================
    # ANALIZA VSEH STOLPCEV
    # ========================================================

    for col in target_cols:

        st.subheader(
            f"🔍 Analiza: {col}"
        )

        # -----------------------------------------------
        # 1. ČIŠČENJE
        # -----------------------------------------------

        keyword_col = f"keywords_{col}"

        df[keyword_col] = df[col].apply(
            clean_and_tokenize
        )

        # -----------------------------------------------
        # 2. KLASIFIKACIJA
        # -----------------------------------------------

        units_col = f"units_{col}"

        df[units_col] = df[keyword_col].apply(
            classify_keywords
        )

        # -----------------------------------------------
        # 3. FREKVENCE
        # -----------------------------------------------

        all_units = [
            unit
            for sublist in df[units_col].tolist()
            for unit in sublist
        ]

        unit_counts = Counter(
            all_units
        )

        freq_df = pd.DataFrame(
            unit_counts.items(),
            columns=[
                "Klasifikacijska enota",
                "Frekvenca"
            ]
        )

        if not freq_df.empty:

            freq_df = freq_df.sort_values(
                by="Frekvenca",
                ascending=False
            )

        # -----------------------------------------------
        # PRIKAZ
        # -----------------------------------------------

        c1, c2 = st.columns([2, 1])

        with c1:

            st.write(
                "Klasificirani podatki po vrsticah:"
            )

            st.dataframe(
                df[
                    [
                        col,
                        keyword_col,
                        units_col
                    ]
                ].head(10),
                use_container_width=True
            )

        with c2:

            st.write(
                "Tabela frekvenc enot:"
            )

            if not freq_df.empty:

                st.table(
                    freq_df
                )

            else:

                st.info(
                    "Ni zaznanih klasifikacij."
                )

        results[col] = freq_df

    # ========================================================
    # CELOKUPNI FREKVENČNI PREGLED
    # ========================================================

    st.divider()

    st.header(
        "📈 Skupni frekvenčni pregled"
    )

    final_tabs = st.tabs(
        target_cols
    )

    for i, tab in enumerate(final_tabs):

        with tab:

            col_name = target_cols[i]

            if not results[col_name].empty:

                st.bar_chart(
                    results[col_name].set_index(
                        "Klasifikacijska enota"
                    )
                )

            else:

                st.info(
                    "Ni podatkov za graf."
                )

    # ========================================================
    # IZRAČUN STRESNE MOČI
    # ========================================================

    st.divider()

    st.header(
        "🔥 CELOKUPNA STRESNA MOČ"
    )

    st.markdown(
        """
        Izračun temelji na rezultatih klasifikacije in uporablja
        Petričevo enačbo stresne moči:

        **σSF = arcsin √((FSF × FPR) / FPF)**
        """
    )

    # ========================================================
    # PREPOZNAVANJE SF / PF / PR STOLPCEV
    # ========================================================

    sf_column = None
    pf_column = None
    pr_column = None

    for col in target_cols:

        column_type = identify_column_type(
            col
        )

        if column_type == "SF":
            sf_column = col

        elif column_type == "PF":
            pf_column = col

        elif column_type == "PR":
            pr_column = col

    # ========================================================
    # FUNKCIJA ZA IZVLEK FREKVENC
    # ========================================================

    def get_frequency_data(column):

        if column is None:
            return 0, 0

        freq = results.get(
            column,
            pd.DataFrame()
        )

        if freq.empty:
            return 0, 0

        total = int(
            freq["Frekvenca"].sum()
        )

        diverse = int(
            len(freq)
        )

        return total, diverse

    total_sf, diverse_sf = get_frequency_data(
        sf_column
    )

    total_pf, diverse_pf = get_frequency_data(
        pf_column
    )

    total_pr, diverse_pr = get_frequency_data(
        pr_column
    )

    number_of_respondents = len(df)

    # ========================================================
    # REALNI FAKTORJI
    # ========================================================

    F_SF = calculate_real_factor(
        total_sf,
        diverse_sf,
        number_of_respondents
    )

    F_PF = calculate_real_factor(
        total_pf,
        diverse_pf,
        number_of_respondents
    )

    F_PR = calculate_real_factor(
        total_pr,
        diverse_pr,
        number_of_respondents
    )

    sigma = calculate_stress_power(
        F_SF,
        F_PF,
        F_PR
    )

    # ========================================================
    # REZULTATI
    # ========================================================

    r1, r2, r3, r4 = st.columns(4)

    with r1:

        st.metric(
            "SF – stresni dejavniki",
            total_sf
        )

    with r2:

        st.metric(
            "PF – pozitivni dejavniki",
            total_pf
        )

    with r3:

        st.metric(
            "PR – predlogi",
            total_pr
        )

    with r4:

        if sigma is not None:

            st.metric(
                "σSF",
                f"{sigma:.2f} °S"
            )

        else:

            st.metric(
                "σSF",
                "Ni mogoče"
            )

    # ========================================================
    # STRESNA MOČ
    # ========================================================

    if sigma is not None:

        st.subheader(
            f"🌡️ Celokupna stresna moč: "
            f"{sigma:.2f} °S"
        )

        # vizualna lestvica 0–50
        st.progress(
            min(
                sigma / 50.0,
                1.0
            )
        )

        if sigma < 30:

            st.warning(
                f"⚠️ σ = {sigma:.2f} °S — "
                "rezultat je pod pričakovanim območjem 30–39 °S."
            )

        elif sigma <= 39:

            st.success(
                f"✅ σ = {sigma:.2f} °S — "
                "rezultat je v pričakovanem območju 30–39 °S."
            )

        else:

            st.warning(
                f"⚠️ σ = {sigma:.2f} °S — "
                "rezultat je nad pričakovanim območjem 30–39 °S."
            )

    else:

        st.error(
            """
            Stresne moči ni mogoče izračunati.
            Potrebni so stolpci za SF, PF in PR.
            """
        )

    # ========================================================
    # GRAF SF / PF / PR
    # ========================================================

    st.subheader(
        "📊 Primerjava SF, PF in PR"
    )

    comparison_df = pd.DataFrame(
        {
            "Faktor": [
                "SF – stresni dejavniki",
                "PF – pozitivni dejavniki",
                "PR – predlogi"
            ],
            "Frekvenca": [
                total_sf,
                total_pf,
                total_pr
            ]
        }
    )

    st.bar_chart(
        comparison_df.set_index(
            "Faktor"
        )
    )

    # ========================================================
    # PODROBNOSTI IZRAČUNA
    # ========================================================

    with st.expander(
        "🧮 Podrobnosti izračuna stresne moči"
    ):

        st.write(
            f"Število respondentov: "
            f"**{number_of_respondents}**"
        )

        st.markdown(
            "### SF"
        )

        st.write(
            f"Skupna frekvenca SF: "
            f"**{total_sf}**"
        )

        st.write(
            f"Različne SF kategorije: "
            f"**{diverse_sf}**"
        )

        st.write(
            f"FSF = **{F_SF:.4f}**"
        )

        st.markdown(
            "### PF"
        )

        st.write(
            f"Skupna frekvenca PF: "
            f"**{total_pf}**"
        )

        st.write(
            f"Različne PF kategorije: "
            f"**{diverse_pf}**"
        )

        st.write(
            f"FPF = **{F_PF:.4f}**"
        )

        st.markdown(
            "### PR"
        )

        st.write(
            f"Skupna frekvenca PR: "
            f"**{total_pr}**"
        )

        st.write(
            f"Različne PR kategorije: "
            f"**{diverse_pr}**"
        )

        st.write(
            f"FPR = **{F_PR:.4f}**"
        )

        st.markdown("---")

        st.latex(
            r"""
            \sigma_{SF}
            =
            \arcsin
            \sqrt{
            \frac{
            F_{SF}\cdot F_{PR}
            }{
            F_{PF}
            }}
            """
        )

        if sigma is not None:

            st.write(
                f"**σSF = {sigma:.4f} °S**"
            )


# ============================================================
# ZAGON
# ============================================================

if __name__ == "__main__":
    main()



