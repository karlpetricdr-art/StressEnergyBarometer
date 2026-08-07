import streamlit as st
import pandas as pd
import re
import math
from collections import Counter
import plotly.express as px


# ============================================================
# 1. NASTAVITVE STRANI
# ============================================================

st.set_page_config(
    page_title="Stress Analysis Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. FUNKCIJA ZA RESET
# ============================================================

def reset_app():

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()


# ============================================================
# 3. STOP-WORDS
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
# 4. RAZŠIRJEN KLASIFIKACIJSKI MODEL
# ============================================================

CATEGORIES_MAP = {

    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "lightning",
        "vročina", "mraz", "cold", "weather", "vreme",
        "prostori", "office", "pisarna", "ergonomija",
        "equipment", "oprema", "tišina", "silence", "zrak"
    ],

    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload",
        "naloge", "tasks", "čas", "time", "administration",
        "birokracija", "birokrat", "informacije", "information",
        "skills", "znanje", "delovni čas", "urgency",
        "hitenje", "naglica", "stiska", "preobremenjenost",
        "neizkušenost", "administrativni"
    ],

    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism",
        "pozitivno", "self-confidence", "samozavest",
        "emotions", "čustva", "stres", "stress",
        "frustracija", "frustration", "peace", "mir",
        "negotovost", "nervoza", "panika", "nemoč",
        "skrb", "napetost"
    ],

    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance",
        "nagrada", "reward", "status", "recognition",
        "priznanje", "poverty", "revščina", "standard",
        "inequality", "nepravičnost", "nestimulativen",
        "krivica", "dostojen", "plačilo", "finančna"
    ],

    "Social unit": [
        "odnosi", "relationships", "mobing", "mobbing",
        "bullying", "harassment", "sodelavci", "colleagues",
        "šef", "boss", "družina", "family", "prijatelji",
        "friends", "komunikacija", "communication", "prepir",
        "zahrbtnost", "vzvišenost", "nesramnost",
        "aroganca", "egoizem", "podpora"
    ],

    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport",
        "sports", "exercise", "prehrana", "diet", "spanje",
        "sleep", "utrujenost", "tiredness", "joga", "yoga",
        "meditacija", "meditation", "izčrpanost", "dihanje",
        "sproščanje", "počitek", "dopust"
    ]
}


# ============================================================
# 5. POMOŽNE FUNKCIJE
# ============================================================

def clean_and_tokenize(text):

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
# 6. IZRAČUN REALNEGA FAKTORJA
# ============================================================

def calculate_fo_real(
    df,
    col,
    n_o
):

    all_keywords_in_cat = []

    for row in df[col].dropna():

        kws = clean_and_tokenize(row)

        for kw in kws:

            for cat, kw_list in CATEGORIES_MAP.items():

                if any(
                    kw.startswith(
                        k.lower()[:5]
                    )
                    for k in kw_list
                ):

                    all_keywords_in_cat.append(kw)

                    break

    fo = len(
        all_keywords_in_cat
    )

    fr = len(
        set(all_keywords_in_cat)
    )

    if fr == 0 or n_o == 0:

        return 0.0001, fo, fr

    rho_o = fo / n_o

    c_o = fo / fr

    fo_real = (
        c_o * rho_o
    ) / 10

    return (
        fo_real,
        fo,
        fr
    )


# ============================================================
# 7. TOP KLJUČNE BESEDE
# ============================================================

def get_top_keywords(
    df,
    col,
    top_n=15
):

    counter = Counter()

    for value in df[col].dropna():

        keywords = clean_and_tokenize(
            value
        )

        counter.update(
            keywords
        )

    return counter.most_common(
        top_n
    )


# ============================================================
# 8. TOP KLASIFIKACIJSKI DEJAVNIKI
# ============================================================

def get_category_dataframe(
    freq_df
):

    if freq_df.empty:
        return pd.DataFrame(
            columns=[
                "Klasifikacijska enota",
                "Frekvenca"
            ]
        )

    return freq_df.sort_values(
        "Frekvenca",
        ascending=True
    )


# ============================================================
# 9. GLAVNA APLIKACIJA
# ============================================================

def main():

    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    st.sidebar.markdown(
        "## ⚙️ Nadzorna plošča"
    )

    st.sidebar.button(
        "🔄 Ponastavi aplikacijo",
        on_click=reset_app,
        use_container_width=True
    )

    st.sidebar.markdown("---")

    uploaded_file = st.sidebar.file_uploader(
        "📂 Naložite podatke",
        type=[
            "txt",
            "csv"
        ]
    )

    # --------------------------------------------------------
    # NASLOV
    # --------------------------------------------------------

    st.markdown(
        """
        <div style="
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            background: linear-gradient(
                90deg,
                #f1f5f9,
                #e2e8f0
            );
        ">
            <h1 style="margin-bottom:5px;">
                📊 Stress Analysis Pro
            </h1>
            <p style="
                font-size:18px;
                margin-top:0;
            ">
                Petričeva klasifikacija stresnih dejavnikov
                in izračun celokupne stresne moči
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        Sistem analizira odgovore respondentov, odstrani
        jezikovna mašila, izlušči ključne besede in jih
        klasificira v **6 znanstvenih kategorij**.
        """
    )

    if uploaded_file is None:

        st.info(
            "👈 Naložite .txt ali .csv datoteko "
            "v levi stranski vrstici."
        )

        return

    # ========================================================
    # BRANJE DATOTEKE
    # ========================================================

    try:

        if uploaded_file.name.lower().endswith(".txt"):

            df = pd.read_csv(
                uploaded_file,
                sep="\t"
            )

        else:

            df = pd.read_csv(
                uploaded_file
            )

    except Exception as e:

        st.error(
            f"❌ Napaka pri branju datoteke: {e}"
        )

        return

    if df.empty:

        st.warning(
            "Datoteka ne vsebuje podatkov."
        )

        return

    n_o = len(df)

    st.success(
        f"✅ Uspešno naloženih respondentov: **{n_o}**"
    )

    # ========================================================
    # OSNOVNI PODATKI
    # ========================================================

    with st.expander(
        "👁️ Pregled vhodnih podatkov"
    ):

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

    target_cols = df.columns.tolist()

    if len(target_cols) < 3:

        st.error(
            """
            Za izračun stresne moči potrebujemo najmanj
            tri stolpce:

            1. Pozitivni dejavniki (PF)
            2. Stresni dejavniki (SF)
            3. Predlogi (PR)
            """
        )

        return

    # ========================================================
    # ANALIZA
    # ========================================================

    results = {}

    fo_real_factors = {}

    keyword_results = {}

    # ========================================================
    # ANALIZA PRVIH TREH STOLPCEV
    # ========================================================

    for col in target_cols[:3]:

        st.divider()

        st.subheader(
            f"🔍 {col}"
        )

        # ----------------------------------------------------
        # KLJUČNE BESEDE
        # ----------------------------------------------------

        keyword_col = (
            f"keywords_{col}"
        )

        units_col = (
            f"units_{col}"
        )

        df[keyword_col] = df[col].apply(
            clean_and_tokenize
        )

        df[units_col] = df[keyword_col].apply(
            classify_keywords
        )

        # ----------------------------------------------------
        # FREKVENCE KATEGORIJ
        # ----------------------------------------------------

        all_units = [
            unit
            for sublist
            in df[units_col].tolist()
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

        results[col] = freq_df

        # ----------------------------------------------------
        # REALNI FAKTOR
        # ----------------------------------------------------

        fo_real, fo_val, fr_val = (
            calculate_fo_real(
                df,
                col,
                n_o
            )
        )

        fo_real_factors[col] = {
            "val": fo_real,
            "fo": fo_val,
            "fr": fr_val
        }

        # ----------------------------------------------------
        # TOP BESEDE
        # ----------------------------------------------------

        keyword_results[col] = (
            get_top_keywords(
                df,
                col,
                15
            )
        )

        # ====================================================
        # METRIKE
        # ====================================================

        m1, m2, m3 = st.columns(3)

        with m1:

            st.metric(
                "🔢 Število zaznanih izrazov",
                fo_val
            )

        with m2:

            st.metric(
                "🧩 Različni izrazi",
                fr_val
            )

        with m3:

            st.metric(
                "Fₒ real",
                f"{fo_real:.4f}"
            )

        # ====================================================
        # TABELA + GRAF
        # ====================================================

        left, right = st.columns(
            [1, 1]
        )

        with left:

            st.write(
                "**Klasifikacija po respondentih**"
            )

            st.dataframe(
                df[
                    [
                        col,
                        units_col
                    ]
                ].head(10),
                use_container_width=True,
                height=300
            )

        with right:

            st.write(
                "**Porazdelitev klasifikacijskih enot**"
            )

            if not freq_df.empty:

                plot_df = (
                    get_category_dataframe(
                        freq_df
                    )
                )

                fig = px.bar(
                    plot_df,
                    x="Frekvenca",
                    y="Klasifikacijska enota",
                    orientation="h",
                    text="Frekvenca",
                    title=""
                )

                fig.update_layout(
                    height=320,
                    margin=dict(
                        l=10,
                        r=10,
                        t=20,
                        b=20
                    ),
                    xaxis_title="Frekvenca",
                    yaxis_title=""
                )

                fig.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

            else:

                st.info(
                    "Ni zaznanih kategorij."
                )

    # ========================================================
    # CELOKUPNA STRESNA MOČ
    # ========================================================

    st.divider()

    st.header(
        "🔥 Celokupna stresna moč"
    )

    # --------------------------------------------------------
    # FAKTORJI
    # --------------------------------------------------------

    f_pf = fo_real_factors[
        target_cols[0]
    ]["val"]

    f_sf = fo_real_factors[
        target_cols[1]
    ]["val"]

    f_pr = fo_real_factors[
        target_cols[2]
    ]["val"]

    # --------------------------------------------------------
    # IZRAČUN
    # --------------------------------------------------------

    try:

        if f_pf <= 0:

            raise ValueError(
                "Pozitivni faktor FₒPF je enak 0."
            )

        argument = math.sqrt(
            (
                f_sf * f_pr
            ) / f_pf
        )

        argument = min(
            max(argument, 0),
            1
        )

        sigma_rad = math.asin(
            argument
        )

        sigma_deg = math.degrees(
            sigma_rad
        )

    except Exception as e:

        st.error(
            f"❌ Napaka pri izračunu: {e}"
        )

        return

    # ========================================================
    # GLAVNI REZULTAT
    # ========================================================

    result_col1, result_col2 = st.columns(
        [1, 2]
    )

    with result_col1:

        st.metric(
            "🌡️ STRESNA MOČ σSF",
            f"{sigma_deg:.2f} °S"
        )

    with result_col2:

        # vizualna lestvica
        st.markdown(
            "**Vizualna lestvica stresne moči**"
        )

        progress_value = min(
            sigma_deg / 90,
            1.0
        )

        st.progress(
            progress_value
        )

        if 30 <= sigma_deg <= 39:

            st.success(
                "✅ Rezultat je znotraj "
                "pričakovanega območja 30–39 °S."
            )

        elif sigma_deg < 30:

            st.warning(
                "⚠️ Rezultat je pod "
                "pričakovanim območjem 30–39 °S."
            )

        else:

            st.warning(
                "⚠️ Rezultat je nad "
                "pričakovanim območjem 30–39 °S."
            )

    # ========================================================
    # FAKTORJI F
    # ========================================================

    st.subheader(
        "🧮 Realni faktorji"
    )

    f1, f2, f3 = st.columns(3)

    with f1:

        st.metric(
            "FₒPF",
            f"{f_pf:.4f}"
        )

        st.caption(
            f"mnenj: "
            f"{fo_real_factors[target_cols[0]]['fo']}"
        )

    with f2:

        st.metric(
            "FₒSF",
            f"{f_sf:.4f}"
        )

        st.caption(
            f"mnenj: "
            f"{fo_real_factors[target_cols[1]]['fo']}"
        )

    with f3:

        st.metric(
            "FₒPR",
            f"{f_pr:.4f}"
        )

        st.caption(
            f"mnenj: "
            f"{fo_real_factors[target_cols[2]]['fo']}"
        )

    # ========================================================
    # GRAF FAKTORJEV
    # ========================================================

    factor_df = pd.DataFrame(
        {
            "Faktor": [
                "FₒPF",
                "FₒSF",
                "FₒPR"
            ],
            "Vrednost": [
                f_pf,
                f_sf,
                f_pr
            ]
        }
    )

    fig_factor = px.bar(
        factor_df,
        x="Faktor",
        y="Vrednost",
        text="Vrednost",
        title="Primerjava realnih faktorjev"
    )

    fig_factor.update_traces(
        texttemplate="%{text:.4f}",
        textposition="outside"
    )

    fig_factor.update_layout(
        height=350,
        yaxis_title="Fₒ",
        xaxis_title=""
    )

    st.plotly_chart(
        fig_factor,
        use_container_width=True
    )

    # ========================================================
    # PRIMERJAVA FREKVENC SF / PF / PR
    # ========================================================

    st.divider()

    st.header(
        "📊 SF – PF – PR"
    )

    comparison_df = pd.DataFrame(
        {
            "Vrsta": [
                "PF – pozitivni dejavniki",
                "SF – stresni dejavniki",
                "PR – predlogi"
            ],
            "Frekvenca": [
                fo_real_factors[
                    target_cols[0]
                ]["fo"],

                fo_real_factors[
                    target_cols[1]
                ]["fo"],

                fo_real_factors[
                    target_cols[2]
                ]["fo"]
            ]
        }
    )

    fig_comparison = px.bar(
        comparison_df,
        x="Vrsta",
        y="Frekvenca",
        text="Frekvenca",
        title="Celotna frekvenčna primerjava"
    )

    fig_comparison.update_traces(
        textposition="outside"
    )

    fig_comparison.update_layout(
        height=400,
        xaxis_title="",
        yaxis_title="Frekvenca"
    )

    st.plotly_chart(
        fig_comparison,
        use_container_width=True
    )

    # ========================================================
    # KLJUČNE BESEDE
    # ========================================================

    st.divider()

    st.header(
        "🔑 Najpogostejši vsebinski izrazi"
    )

    keyword_tabs = st.tabs(
        target_cols[:3]
    )

    for i, tab in enumerate(
        keyword_tabs
    ):

        col_name = target_cols[i]

        with tab:

            top_words = keyword_results[
                col_name
            ]

            if not top_words:

                st.info(
                    "Ni dovolj podatkov."
                )

                continue

            word_df = pd.DataFrame(
                top_words,
                columns=[
                    "Izraz",
                    "Frekvenca"
                ]
            )

            left, right = st.columns(
                [1, 2]
            )

            with left:

                st.dataframe(
                    word_df,
                    use_container_width=True,
                    hide_index=True
                )

            with right:

                fig_words = px.bar(
                    word_df.sort_values(
                        "Frekvenca"
                    ),
                    x="Frekvenca",
                    y="Izraz",
                    orientation="h",
                    text="Frekvenca",
                    title=f"Top izrazi – {col_name}"
                )

                fig_words.update_layout(
                    height=450,
                    margin=dict(
                        l=10,
                        r=20,
                        t=50,
                        b=20
                    ),
                    xaxis_title="Frekvenca",
                    yaxis_title=""
                )

                fig_words.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    fig_words,
                    use_container_width=True
                )

    # ========================================================
    # VIZUALIZACIJA PREDLOGOV
    # ========================================================

    st.divider()

    st.header(
        "💡 Vizualizacija predlogov"
    )

    proposal_col = target_cols[2]

    proposal_counter = Counter()

    for value in df[
        proposal_col
    ].dropna():

        keywords = clean_and_tokenize(
            value
        )

        proposal_counter.update(
            keywords
        )

    proposal_words = proposal_counter.most_common(
        20
    )

    if proposal_words:

        proposal_df = pd.DataFrame(
            proposal_words,
            columns=[
                "Izraz",
                "Frekvenca"
            ]
        )

        fig_proposals = px.bar(
            proposal_df.sort_values(
                "Frekvenca"
            ),
            x="Frekvenca",
            y="Izraz",
            orientation="h",
            text="Frekvenca",
            title="Najpogostejši izrazi v predlogih"
        )

        fig_proposals.update_layout(
            height=550,
            xaxis_title="Frekvenca",
            yaxis_title=""
        )

        fig_proposals.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            fig_proposals,
            use_container_width=True
        )

        st.caption(
            """
            Graf prikazuje najpogostejše vsebinske izraze
            v stolpcu predlogov. Gre za vizualni pregled
            vsebine predlogov in ne za dodatno spreminjanje
            izračuna stresne moči.
            """
        )

    else:

        st.info(
            "V predlogih ni bilo dovolj prepoznavnih izrazov."
        )

    # ========================================================
    # MATEMATIČNA FORMULA
    # ========================================================

    with st.expander(
        "🧮 Prikaži matematični izračun"
    ):

        st.markdown(
            """
            ### Petričeva enačba tretjega nivoja
            """
        )

        st.latex(
            r"""
            \sigma_{SF}
            =
            \arcsin
            \sqrt{
            \frac{
            F_{oSF}\cdot F_{oPR}
            }{
            F_{oPF}
            }}
            """
        )

        st.write(
            f"FₒSF = **{f_sf:.6f}**"
        )

        st.write(
            f"FₒPF = **{f_pf:.6f}**"
        )

        st.write(
            f"FₒPR = **{f_pr:.6f}**"
        )

        st.markdown("---")

        st.write(
            f"### σSF = {sigma_deg:.4f} °S"
        )


# ============================================================
# ZAGON
# ============================================================

if __name__ == "__main__":
    main()



