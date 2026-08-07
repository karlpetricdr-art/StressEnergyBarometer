import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# ============================================================
# 1. RESET FUNKCIJA
# ============================================================

def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================
# 2. STOP WORDS
# ============================================================

SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že",
    "tudi", "iz", "za", "še", "samo", "tako", "kot", "sem", "smo",
    "ste", "so", "je", "bil", "biti", "ali", "v", "pri", "o",
    "z", "s", "k", "h", "vse", "vsi", "tisti", "nekaj",
    "včasih", "npr", "itd", "the", "and", "to", "of", "a",
    "is", "in", "it"
}


# ============================================================
# 3. KLASIFIKACIJSKI MODEL
# ============================================================

CATEGORIES_MAP = {

    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "vročina",
        "mraz", "cold", "weather", "vreme",
        "prostori", "office", "pisarna",
        "ergonomija", "equipment", "oprema",
        "tišina", "silence", "zrak"
    ],

    "Performance unit": [
        "roki", "deadline", "obremenitev",
        "workload", "naloge", "tasks",
        "čas", "time", "administration",
        "birokracija", "birokrat",
        "informacije", "information",
        "skills", "znanje",
        "delovni čas", "urgency",
        "hitenje", "naglica",
        "stiska", "preobremenjenost",
        "neizkušenost",
        "administrativni"
    ],

    "Individual Psychological unit": [
        "strah", "fear", "anxiety",
        "tesnoba", "optimism",
        "pozitivno",
        "self-confidence",
        "samozavest",
        "emotions", "čustva",
        "stres", "stress",
        "frustracija",
        "frustration",
        "mir", "peace",
        "negotovost",
        "nervoza",
        "panika",
        "nemoč",
        "skrb",
        "napetost"
    ],

    "Partial social unit": [
        "plača",
        "salary",
        "denar",
        "money",
        "finance",
        "nagrada",
        "reward",
        "status",
        "recognition",
        "priznanje",
        "poverty",
        "revščina",
        "standard",
        "inequality",
        "nepravičnost",
        "krivica",
        "dostojen",
        "plačilo",
        "finančna"
    ],

    "Social unit": [
        "odnosi",
        "relationships",
        "mobing",
        "mobbing",
        "bullying",
        "harassment",
        "sodelavci",
        "colleagues",
        "šef",
        "boss",
        "družina",
        "family",
        "prijatelji",
        "friends",
        "komunikacija",
        "communication",
        "prepir",
        "zahrbtnost",
        "vzvišenost",
        "nesramnost",
        "aroganca",
        "egoizem",
        "podpora"
    ],

    "Health biological unit": [
        "zdravje",
        "health",
        "bolezen",
        "illness",
        "šport",
        "sports",
        "exercise",
        "prehrana",
        "diet",
        "spanje",
        "sleep",
        "utrujenost",
        "tiredness",
        "joga",
        "yoga",
        "meditacija",
        "meditation",
        "izčrpanost",
        "dihanje",
        "sproščanje",
        "počitek",
        "dopust"
    ]
}


# ============================================================
# 4. POMOŽNE FUNKCIJE
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

    return [
        w for w in words
        if w not in SLO_STOPWORDS
        and len(w) > 2
    ]



def classify_keywords(keywords):

    found_categories = []

    for word in keywords:

        for category, keywords_list in CATEGORIES_MAP.items():

            if any(
                keyword.lower() in word
                for keyword in keywords_list
            ):
                found_categories.append(category)

    return found_categories



def calculate_fo_real(df, col, n_o):

    detected = []

    for row in df[col].dropna():

        words = clean_and_tokenize(row)

        for word in words:

            for category, keywords in CATEGORIES_MAP.items():

                if any(
                    word.startswith(k.lower()[:5])
                    for k in keywords
                ):
                    detected.append(word)
                    break


    fo = len(detected)

    fr = len(set(detected))


    if fr == 0 or n_o == 0:
        return 0.0001, fo, fr


    rho_o = fo / n_o

    c_o = fo / fr

    fo_real = (c_o * rho_o) / 10


    return fo_real, fo, fr



# ============================================================
# 5. ANALIZA POSAMEZNIH STRESNIH DEJAVNIKOV
# ============================================================

def analyze_category_factors(df, col):

    category_results = {}

    for category, keywords in CATEGORIES_MAP.items():

        detected = []

        for text in df[col].dropna():

            tokens = clean_and_tokenize(text)

            for token in tokens:

                for key in keywords:

                    if token.startswith(key.lower()[:5]):

                        detected.append(token)
                        break


        if detected:

            counter = Counter(detected)

            factor_df = pd.DataFrame(
                counter.items(),
                columns=[
                    "Stresni dejavnik",
                    "Frekvenca"
                ]
            )


            factor_df["Delež (%)"] = (
                factor_df["Frekvenca"]
                /
                factor_df["Frekvenca"].sum()
                *
                100
            ).round(2)


            factor_df = factor_df.sort_values(
                "Frekvenca",
                ascending=False
            )


        else:

            factor_df = pd.DataFrame(
                columns=[
                    "Stresni dejavnik",
                    "Frekvenca",
                    "Delež (%)"
                ]
            )


        category_results[category] = factor_df


    return category_results
	
	# ============================================================
# 6. STREAMLIT APLIKACIJA
# ============================================================

def main():

    st.set_page_config(
        page_title="Stress Analysis Pro",
        page_icon="📊",
        layout="wide"
    )


    # --------------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------------

    with st.sidebar:

        st.header("⚙️ Nastavitve")

        if st.button(
            "🔄 Ponastavi aplikacijo",
            use_container_width=True
        ):
            reset_app()

        st.divider()

        uploaded_file = st.file_uploader(
            "Naložite .txt ali .csv datoteko",
            type=["txt", "csv"]
        )


    # --------------------------------------------------------
    # NASLOV
    # --------------------------------------------------------

    st.title(
        "📊 Klasifikacija stresnih dejavnikov po Petričevi metodi"
    )


    st.markdown(
        """
        Sistem analizira odgovore respondentov,
        odstrani mašila in razvrsti stresne dejavnike
        v **6 hierarhičnih kategorij**.

        Izračun stresne moči temelji na
        **3. nivoju Petričeve metode**.
        """
    )


    if uploaded_file:


        # ----------------------------------------------------
        # BRANJE PODATKOV
        # ----------------------------------------------------

        try:

            if uploaded_file.name.endswith(".txt"):

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
                f"Napaka pri branju datoteke: {e}"
            )

            return



        n_o = len(df)


        st.success(
            f"Datoteka uspešno naložena. "
            f"Analiziranih respondentov: {n_o}",
            icon="✅"
        )


        target_cols = df.columns.tolist()


        if len(target_cols) < 3:

            st.error(
                "Datoteka mora vsebovati najmanj 3 stolpce."
            )

            return



        results = {}

        fo_real_factors = {}



        # ----------------------------------------------------
        # 1. KLASIFIKACIJA PO SKLOPIH
        # ----------------------------------------------------

        st.header(
            "🔍 Kvalitativna analiza po sklopih"
        )


        for col in target_cols[:3]:


            with st.expander(
                f"Podrobnosti: {col}",
                expanded=True
            ):


                df[f"keywords_{col}"] = (
                    df[col]
                    .apply(clean_and_tokenize)
                )


                df[f"units_{col}"] = (
                    df[f"keywords_{col}"]
                    .apply(classify_keywords)
                )


                all_units = [
                    item
                    for sublist in df[f"units_{col}"]
                    for item in sublist
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


                freq_df = freq_df.sort_values(
                    "Frekvenca",
                    ascending=False
                )


                c1, c2 = st.columns(
                    [2,1]
                )


                with c1:

                    st.dataframe(
                        df[
                            [
                                col,
                                f"units_{col}"
                            ]
                        ].head(10),
                        use_container_width=True
                    )


                with c2:

                    st.table(
                        freq_df
                    )



                fo_real, fo, fr = calculate_fo_real(
                    df,
                    col,
                    n_o
                )


                fo_real_factors[col] = {

                    "val": fo_real,
                    "fo": fo,
                    "fr": fr

                }


                results[col] = freq_df



        # ----------------------------------------------------
        # 2. POSAMEZNI STRESNI DEJAVNIKI
        # ----------------------------------------------------

        st.divider()

        st.header(
            "🧠 Analiza posameznih stresnih dejavnikov"
        )


        factor_results = {}


        for col in target_cols[:3]:


            st.subheader(
                f"📌 {col}"
            )


            factor_results[col] = (
                analyze_category_factors(
                    df,
                    col
                )
            )


            for category, factor_df in factor_results[col].items():


                with st.expander(
                    f"🔹 {category}"
                ):


                    if len(factor_df) > 0:


                        a, b = st.columns(
                            [2,1]
                        )


                        with a:

                            st.dataframe(
                                factor_df.head(15),
                                use_container_width=True
                            )


                        with b:


                            st.metric(
                                "Število zaznanih pojavov",
                                int(
                                    factor_df["Frekvenca"].sum()
                                )
                            )


                            st.metric(
                                "Najmočnejši dejavnik",
                                factor_df.iloc[0]["Stresni dejavnik"]
                            )


                        st.bar_chart(
                            factor_df
                            .head(10)
                            .set_index(
                                "Stresni dejavnik"
                            )["Frekvenca"]
                        )


                    else:

                        st.info(
                            "Ni zaznanih dejavnikov."
                        )



        # ----------------------------------------------------
        # 3. STRESNA MOČ
        # ----------------------------------------------------

        st.divider()

        st.header(
            "📐 Izračun celokupne stresne moči"
        )


        f_pf = fo_real_factors[
            target_cols[0]
        ]["val"]


        f_sf = fo_real_factors[
            target_cols[1]
        ]["val"]


        f_pr = fo_real_factors[
            target_cols[2]
        ]["val"]



        try:

            argument = math.sqrt(
                (
                    f_sf * f_pr
                )
                /
                f_pf
            )


            sigma_rad = math.asin(
                min(
                    argument,
                    1.0
                )
            )


            sigma_deg = math.degrees(
                sigma_rad
            )



            with st.container(
                border=True
            ):


                c1, c2 = st.columns(
                    [1,1.5]
                )


                with c1:


                    st.metric(
                        "CELOKUPNA STRESNA MOČ",
                        f"{sigma_deg:.2f} °S"
                    )


                    if sigma_deg <= 15:

                        st.info(
                            "Zelo nizka"
                        )

                    elif sigma_deg <= 30:

                        st.info(
                            "Nizka"
                        )

                    elif sigma_deg <= 45:

                        st.warning(
                            "Srednja"
                        )

                    else:

                        st.error(
                            "Visoka"
                        )



                    if 30 <= sigma_deg <= 39:

                        st.success(
                            "Rezultat je v znanstveno pričakovanem območju 🎯"
                        )



                with c2:


                    st.markdown(
                        f"""
                        **Realni faktorji**

                        - FₒSF: **{f_sf:.4f}**
                        - FₒPF: **{f_pf:.4f}**
                        - FₒPR: **{f_pr:.4f}**

                        """
                    )


                    st.progress(
                        min(
                            sigma_deg/90,
                            1.0
                        )
                    )


        except Exception as e:

            st.error(
                f"Napaka pri izračunu: {e}"
            )



        # ----------------------------------------------------
        # 4. GRAFI
        # ----------------------------------------------------

        st.divider()

        st.header(
            "📈 Frekvenčna porazdelitev kategorij"
        )


        tabs = st.tabs(
            [
                f"📊 {target_cols[0]}",
                f"📊 {target_cols[1]}",
                f"📊 {target_cols[2]}"
            ]
        )


        for i, tab in enumerate(tabs):

            with tab:

                st.bar_chart(
                    results[target_cols[i]]
                    .set_index(
                        "Klasifikacijska enota"
                    )
                )



    else:

        st.info(
            "Naložite datoteko za začetek analize.",
            icon="ℹ️"
        )



# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()



