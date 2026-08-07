# ============================================================
# DEL 1/3
# ============================================================

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

    "se", "oh", "na", "potem", "in", "ter", "bi",
    "da", "pa", "že", "tudi", "iz", "za", "še",
    "samo", "tako", "kot", "sem", "smo", "ste",
    "so", "je", "bil", "biti", "ali", "v", "pri",
    "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd",
    "the", "and", "to", "of", "a", "is", "it"

}



# ============================================================
# 3. KLASIFIKACIJSKI MODEL
# ============================================================

CATEGORIES_MAP = {


    "Attentive (physical) unit": [

        "hrup",
        "noise",
        "svetloba",
        "light",
        "vročina",
        "mraz",
        "cold",
        "weather",
        "vreme",
        "prostori",
        "office",
        "pisarna",
        "ergonomija",
        "equipment",
        "oprema",
        "tišina",
        "silence",
        "zrak"

    ],



    "Performance unit": [

        "roki",
        "deadline",
        "obremenitev",
        "workload",
        "naloge",
        "tasks",
        "čas",
        "time",
        "administration",
        "birokracija",
        "birokrat",
        "informacije",
        "information",
        "skills",
        "znanje",
        "delovni čas",
        "urgency",
        "hitenje",
        "naglica",
        "stiska",
        "preobremenjenost",
        "neizkušenost",
        "administrativni"

    ],



    "Individual Psychological unit": [

        "strah",
        "fear",
        "anxiety",
        "tesnoba",
        "optimism",
        "pozitivno",
        "self-confidence",
        "samozavest",
        "emotions",
        "čustva",
        "stres",
        "stress",
        "frustracija",
        "frustration",
        "mir",
        "peace",
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
# 4. ČIŠČENJE IN TOKENIZACIJA
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



# ============================================================
# 5. KLASIFIKACIJA BESED
# ============================================================

def classify_keywords(keywords):

    found_categories = []


    for word in keywords:


        for category, keyword_list in CATEGORIES_MAP.items():


            if any(

                keyword.lower() in word

                for keyword in keyword_list

            ):

                found_categories.append(category)



    return found_categories



# ============================================================
# 6. IZRAČUN Fo
# ============================================================

def calculate_fo_real(df, col, n_o):


    detected = []


    for row in df[col].dropna():


        words = clean_and_tokenize(row)


        for word in words:


            for category, keywords in CATEGORIES_MAP.items():


                if any(

                    word.startswith(
                        k.lower()[:5]
                    )

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
# DEL 2/3
# ============================================================


# ============================================================
# 7. ANALIZA POSAMEZNIH STRESNIH DEJAVNIKOV
# ============================================================

def analyze_category_factors(df, col):

    category_results = {}


    for category, keywords in CATEGORIES_MAP.items():


        detected = []


        for text in df[col].dropna():


            tokens = clean_and_tokenize(text)


            for token in tokens:


                for key in keywords:


                    if token.startswith(
                        key.lower()[:5]
                    ):

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
# 8. STRESNA MOČ POSAMEZNIH KATEGORIJ (°S)
# ============================================================

def calculate_category_sigma(df, col, n_o):


    results = []



    for category, keywords in CATEGORIES_MAP.items():


        detected = []



        for row in df[col].dropna():


            words = clean_and_tokenize(row)



            for word in words:


                if any(

                    word.startswith(
                        k.lower()[:5]
                    )

                    for k in keywords

                ):

                    detected.append(word)



        fo = len(detected)

        fr = len(set(detected))



        if fr == 0 or n_o == 0:


            Fo = 0.0001


        else:


            rho_o = fo / n_o

            c_o = fo / fr


            Fo = (

                c_o *

                rho_o

            ) / 10



        # Petrič model:
        # stresna moč = arcsin(sqrt(Fo))

        sigma = math.degrees(

            math.asin(

                min(

                    math.sqrt(Fo),

                    1.0

                )

            )

        )



        results.append(

            {

                "Kategorija": category,

                "Fo faktor": round(

                    Fo,

                    5

                ),

                "Število zaznav": fo,

                "Različni pojmi": fr,

                "Stresna moč °S": round(

                    sigma,

                    2

                )

            }

        )



    return pd.DataFrame(results)




# ============================================================
# 9. CELOKUPNA STRESNA MOČ
# ============================================================

def calculate_total_sigma(category_sigma_df):


    values = category_sigma_df[

        "Stresna moč °S"

    ].tolist()



    if len(values) == 0:

        return 0



    # agregacija šestih hierarhičnih enot

    normalized = sum(

        v ** 2

        for v in values

    )



    total_sigma = math.sqrt(

        normalized

    )



    return round(

        min(

            total_sigma,

            90

        ),

        2

    )




# ============================================================
# 10. INTERPRETACIJA STRESA
# ============================================================

def interpret_sigma(value):


    if value <= 15:

        return "Zelo nizka stresna moč"



    elif value <= 30:

        return "Nizka stresna moč"



    elif value <= 45:

        return "Srednja stresna moč"



    elif value <= 60:

        return "Povišana stresna moč"



    else:

        return "Visoka stresna moč"




# ============================================================
# 11. PRIPRAVA BARVNEGA PRIKAZA
# ============================================================

def sigma_level_color(value):


    if value <= 15:

        return "🟢"



    elif value <= 30:

        return "🟡"



    elif value <= 45:

        return "🟠"



    else:

        return "🔴"
		
# ============================================================
# DEL 3/3
# ============================================================


# ============================================================
# 12. STREAMLIT APLIKACIJA
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


        st.header(
            "⚙️ Nastavitve"
        )


        if st.button(

            "🔄 Ponastavi aplikacijo",

            use_container_width=True

        ):

            reset_app()



        st.divider()



        uploaded_file = st.file_uploader(

            "Naložite .txt ali .csv datoteko",

            type=[

                "txt",

                "csv"

            ]

        )




    # --------------------------------------------------------
    # NASLOV
    # --------------------------------------------------------

    st.title(

        "📊 Psihosocialni barometer – Petričeva metoda"

    )


    st.markdown(

        """
        Sistem klasificira stresne dejavnike v šest
        hierarhičnih kategorij in izračuna:

        - posamezne stresne moči kategorij (°S)
        - celokupno stresno moč sistema (°S)
        - najpomembnejše stresne dejavnike
        """

    )



    if uploaded_file:



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

            f"Analiziranih respondentov: {n_o}",

            icon="✅"

        )



        target_cols = df.columns.tolist()



        if len(target_cols) < 3:


            st.error(

                "Potrebni so najmanj 3 stolpci."

            )

            return



        results = {}

        fo_real_factors = {}




        # ----------------------------------------------------
        # 1. KLASIFIKACIJA
        # ----------------------------------------------------

        st.header(

            "🔍 Klasifikacija stresnih kategorij"

        )



        for col in target_cols[:3]:


            with st.expander(

                f"Podrobnosti: {col}",

                expanded=True

            ):



                df[f"keywords_{col}"] = (

                    df[col]

                    .apply(

                        clean_and_tokenize

                    )

                )



                df[f"units_{col}"] = (

                    df[f"keywords_{col}"]

                    .apply(

                        classify_keywords

                    )

                )



                all_units = [

                    x

                    for sub in df[f"units_{col}"]

                    for x in sub

                ]



                counts = Counter(

                    all_units

                )



                freq_df = pd.DataFrame(

                    counts.items(),

                    columns=[

                        "Kategorija",

                        "Frekvenca"

                    ]

                )



                freq_df = freq_df.sort_values(

                    "Frekvenca",

                    ascending=False

                )



                st.dataframe(

                    freq_df,

                    use_container_width=True

                )



                fo, pojavitve, pojmi = calculate_fo_real(

                    df,

                    col,

                    n_o

                )



                fo_real_factors[col] = {

                    "Fo": fo,

                    "pojavitve": pojavitve,

                    "pojmi": pojmi

                }



                results[col] = freq_df





        # ----------------------------------------------------
        # 2. STRESNA MOČ KATEGORIJ
        # ----------------------------------------------------

        st.divider()



        st.header(

            "🔥 Stresna moč posameznih kategorij"

        )



        category_results = {}



        for col in target_cols[:3]:


            st.subheader(

                f"📌 {col}"

            )


            sigma_df = calculate_category_sigma(

                df,

                col,

                n_o

            )


            category_results[col] = sigma_df



            st.dataframe(

                sigma_df,

                use_container_width=True

            )



            st.bar_chart(

                sigma_df.set_index(

                    "Kategorija"

                )[

                    "Stresna moč °S"

                ]

            )





        # ----------------------------------------------------
        # 3. CELOTNA STRESNA MOČ
        # ----------------------------------------------------

        st.divider()



        st.header(

            "📐 Celokupna stresna moč sistema"

        )



        # združitev treh glavnih analiznih sklopov

        main_sigma = calculate_category_sigma(

            df,

            target_cols[1],

            n_o

        )



        total_sigma = calculate_total_sigma(

            main_sigma

        )



        c1, c2 = st.columns(

            [1,1.5]

        )



        with c1:


            st.metric(

                "CELOKUPNA STRESNA MOČ",

                f"{total_sigma:.2f} °S"

            )



            st.info(

                interpret_sigma(

                    total_sigma

                )

            )



            if 30 <= total_sigma <= 39:


                st.success(

                    "Rezultat je v pričakovanem območju 30–39 °S 🎯"

                )



        with c2:


            st.write(

                "### Hierarhični stresni profil"

            )


            for _, row in main_sigma.iterrows():


                st.write(

                    f"{sigma_level_color(row['Stresna moč °S'])} "
                    f"{row['Kategorija']}: "
                    f"**{row['Stresna moč °S']} °S**"

                )





        # ----------------------------------------------------
        # 4. POSAMEZNI STRESORJI
        # ----------------------------------------------------

        st.divider()



        st.header(

            "🧠 Najpogostejši posamezni stresni dejavniki"

        )



        for col in target_cols[:3]:


            st.subheader(

                col

            )


            factors = analyze_category_factors(

                df,

                col

            )



            for category, factor_df in factors.items():


                with st.expander(

                    category

                ):


                    if len(factor_df) > 0:


                        st.dataframe(

                            factor_df.head(10),

                            use_container_width=True

                        )


                        st.bar_chart(

                            factor_df.head(10)

                            .set_index(

                                "Stresni dejavnik"

                            )[

                                "Frekvenca"

                            ]

                        )


                    else:


                        st.info(

                            "Ni zaznanih dejavnikov."

                        )



        # ----------------------------------------------------
        # 5. KATEGORIJSKI GRAFI
        # ----------------------------------------------------

        st.divider()



        st.header(

            "📈 Primerjava stresnih kategorij"

        )



        compare_df = calculate_category_sigma(

            df,

            target_cols[1],

            n_o

        )



        st.bar_chart(

            compare_df.set_index(

                "Kategorija"

            )[

                "Stresna moč °S"

            ]

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



