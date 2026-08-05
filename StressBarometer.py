# ============================================================
# PSIHOSOCIALNI BAROMETER v2.0
# Karl Petrič, 2025/2026
#
# Namen:
# Večnivojska AI analiza psihosocialnih dejavnikov
#
# DEL 1/3
# ============================================================


import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import json
import time
import math
import re


# ============================================================
# 1. STREAMLIT NASTAVITVE
# ============================================================

st.set_page_config(
    page_title="Psihosocialni Barometer v2.0",
    layout="wide"
)


st.title(
    "📊 Psihosocialni Barometer v2.0 "
    "(Večfaktorska AI analiza stresa)"
)


st.markdown(
"""
### Model Petrič (2025/2026)

Aplikacija omogoča:

✅ več stresorjev iz enega odgovora  
✅ pozitivne zaščitne faktorje  
✅ predloge izboljšav  
✅ AI strukturirano analizo JSON  
✅ agregacijo rezultatov več respondentov  

Primer:

> "Delo me obremenjuje, nimam časa,
> vendar me družina podpira in šport mi pomaga."

AI identificira:

**Stresorji**
- delovna obremenitev
- pomanjkanje časa

**Pozitivni dejavniki**
- družinska podpora
- šport

**Predlogi**
- boljša organizacija časa
"""
)


# ============================================================
# 2. SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Nastavitve")


    api_key = st.text_input(
        "Gemini API ključ:",
        type="password"
    )


    st.info(
        "API ključ ustvarite v Google AI Studio."
    )


    st.divider()


    model_name = st.selectbox(
    "AI model:",
    [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite"
    ]
)


    st.write(
        "Avtor modela:"
    )

    st.write(
        "Karl Petrič"
    )



# ============================================================
# 3. GEMINI KONFIGURACIJA
# ============================================================

def initialize_gemini(api_key, model_name):

    if not api_key:
        return None

    try:

        genai.configure(
            api_key=api_key
        )

        model = genai.GenerativeModel(
            model_name=model_name
        )

        return model


    except Exception as e:

        st.error(
            f"Napaka Gemini povezave: {e}"
        )

        return None




# ============================================================
# 4. NALAGANJE PODATKOV
# ============================================================

def load_dataset(uploaded_file):

    """
    Uvoz:
    XLSX
    CSV
    TXT
    """


    if uploaded_file is None:
        return None


    filename = uploaded_file.name.lower()


    try:

        if filename.endswith(".xlsx"):

            df = pd.read_excel(
                uploaded_file
            )


        elif filename.endswith(".csv"):

            df = pd.read_csv(
                uploaded_file
            )


        elif filename.endswith(".txt"):

            text = uploaded_file.read().decode(
                "utf-8"
            )


            df = pd.DataFrame(
                {
                    "Odgovor":
                    text.splitlines()
                }
            )


        else:

            st.error(
                "Nepodprt format datoteke."
            )

            return None


        return df


    except Exception as e:

        st.error(
            f"Napaka pri uvozu: {e}"
        )

        return None





# ============================================================
# 5. PRIPRAVA PODATKOV
# ============================================================

def prepare_dataframe(df):


    if df is None:
        return None


    if len(df.columns) == 0:

        st.error(
            "Datoteka nima stolpcev."
        )

        return None



    # prvi stolpec postane odgovor

    if "Odgovor" not in df.columns:

        df = df.rename(
            columns={
                df.columns[0]:
                "Odgovor"
            }
        )


    df["Odgovor"] = (
        df["Odgovor"]
        .fillna("")
        .astype(str)
        .str.strip()
    )


    # odstranimo prazne odgovore

    df = df[
        df["Odgovor"].str.len() > 5
    ]


    df = df.reset_index(
        drop=True
    )


    return df





# ============================================================
# 6. JSON POMOŽNE FUNKCIJE
# ============================================================

def clean_json_response(text):


    if not text:

        return "{}"


    text = text.strip()


    # odstrani markdown oznake

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )


    text = re.sub(
        r"```",
        "",
        text
    )


    # poišči JSON objekt


    start = text.find("{")

    end = text.rfind("}")


    if start >= 0 and end >= 0:

        text = text[start:end+1]


    return text.strip()





def empty_analysis():

    return {

        "stresorji": [],

        "pozitivni_dejavniki": [],

        "predlogi": []

    }





# ============================================================
# 7. NALAGANJE DATASETA
# ============================================================

uploaded_file = st.file_uploader(
    "📂 Naložite odgovore respondentov",
    type=[
        "xlsx",
        "csv",
        "txt"
    ]
)



if uploaded_file:


    df = load_dataset(
        uploaded_file
    )


    df = prepare_dataframe(
        df
    )


    if df is not None:


        st.success(
            f"Naloženih odgovorov: {len(df)}"
        )


        st.dataframe(
            df.head(10),
            use_container_width=True
        )


        st.session_state["dataset"] = df



# ============================================================
# KONEC DELA 1/3
# ============================================================

# ============================================================
# DEL 2/3
# VEČFAKTORSKA AI ANALIZA
# ============================================================



# ============================================================
# 8. GEMINI PROMPT
# ============================================================

def build_analysis_prompt(answer):


    prompt = f"""

Analiziraj odgovor respondenta po modelu:

Psihosocialni Barometer Petrič (2025/2026)


En odgovor lahko vsebuje VEČ dejavnikov.


Identificiraj:


1. STRESORJE

Kaj povzroča psihosocialno obremenitev.


2. POZITIVNE DEJAVNIKE

Kaj zmanjšuje stres ali povečuje odpornost.


3. PREDLOGE

Kaj bi lahko izboljšalo stanje.



Ocena intenzivnosti:


0 = ni prisotno

1 = zelo nizko

2 = nizko

3 = srednje

4 = visoko

5 = zelo visoko



Vrni IZKLJUČNO JSON:


{{
"stresorji":[
    {{
    "faktor":"",
    "intenzivnost":0
    }}
],

"pozitivni_dejavniki":[
    {{
    "faktor":"",
    "intenzivnost":0
    }}
],

"predlogi":[
    {{
    "faktor":"",
    "ucinek":0
    }}
]

}}



Odgovor respondenta:


"{answer}"


"""


    return prompt





# ============================================================
# 9. ANALIZA ENEGA ODGOVORA
# ============================================================

def analyze_single_response(model, answer):


    default = empty_analysis()


    if model is None:

        return default



    try:


        response = model.generate_content(

            build_analysis_prompt(
                answer
            )

        )


        raw = response.text


        clean = clean_json_response(
            raw
        )


        data = json.loads(
            clean
        )


        # zaščita strukture

        if not isinstance(
            data,
            dict
        ):

            return default



        for key in [

            "stresorji",

            "pozitivni_dejavniki",

            "predlogi"

        ]:

            if key not in data:

                data[key] = []



        return data



    except Exception as e:


        st.warning(
            f"AI analiza neuspešna: {e}"
        )


        return default






# ============================================================
# 10. ANALIZA CELOTNEGA DATASETA
# ============================================================

def run_multifactor_analysis(
        df,
        model):


    results = []


    progress = st.progress(
        0
    )


    total = len(df)


    for index, row in df.iterrows():


        answer = row["Odgovor"]



        result = analyze_single_response(
            model,
            answer
        )


        results.append(
            result
        )


        progress.progress(
            int(
                ((index+1)/total)*100
            )
        )


        # zaščita API omejitev

        if (index+1) % 20 == 0:

            time.sleep(2)



    return results





# ============================================================
# 11. POMOŽNA FUNKCIJA ZA ŠTEVILA
# ============================================================

def safe_number(value):


    try:

        return int(value)


    except:

        return 0






# ============================================================
# 12. AGREGACIJA FAKTORJEV
# ============================================================

def aggregate_factors(results):


    aggregation = {


        "SF_count":0,

        "PF_count":0,

        "PR_count":0,


        "SF_weight":0,

        "PF_weight":0,

        "PR_weight":0,


        "SF_list":[],

        "PF_list":[],

        "PR_list":[]

    }



    for item in results:



        # -----------------------------
        # STRESORJI
        # -----------------------------

        for sf in item.get(
            "stresorji",
            []
        ):


            value = safe_number(

                sf.get(
                    "intenzivnost",
                    0
                )

            )


            name = sf.get(

                "faktor",
                "neznan"

            ).strip()



            if name:


                aggregation["SF_count"] += 1

                aggregation["SF_weight"] += value


                aggregation["SF_list"].append(

                    (
                        name,
                        value
                    )

                )





        # -----------------------------
        # POZITIVNI DEJAVNIKI
        # -----------------------------

        for pf in item.get(
            "pozitivni_dejavniki",
            []
        ):


            value = safe_number(

                pf.get(
                    "intenzivnost",
                    0
                )

            )


            name = pf.get(

                "faktor",
                "neznan"

            ).strip()



            if name:


                aggregation["PF_count"] += 1

                aggregation["PF_weight"] += value


                aggregation["PF_list"].append(

                    (
                        name,
                        value
                    )

                )





        # -----------------------------
        # PREDLOGI
        # -----------------------------

        for pr in item.get(
            "predlogi",
            []
        ):


            value = safe_number(

                pr.get(
                    "ucinek",
                    0
                )

            )


            name = pr.get(

                "faktor",
                "neznan"

            ).strip()



            if name:


                aggregation["PR_count"] += 1

                aggregation["PR_weight"] += value


                aggregation["PR_list"].append(

                    (
                        name,
                        value
                    )

                )




    return aggregation






# ============================================================
# 13. ZDRUŽEVANJE ENAKIH FAKTORJEV
# ============================================================

def merge_factors(items):


    merged = {}


    for name, value in items:


        if name not in merged:

            merged[name] = 0


        merged[name] += value



    return list(

        merged.items()

    )






# ============================================================
# 14. PRETVORBA V DATAFRAME
# ============================================================

def factors_to_dataframe(
        aggregated):


    rows = []



    categories = [

        (
            "Stresorji",
            "SF_list"
        ),

        (
            "Pozitivni",
            "PF_list"
        ),

        (
            "Predlogi",
            "PR_list"
        )

    ]



    for category, key in categories:


        merged = merge_factors(

            aggregated[key]

        )



        for name, value in merged:


            rows.append(

                {

                "Kategorija":
                    category,

                "Faktor":
                    name,

                "Moč":
                    value

                }

            )



    return pd.DataFrame(
        rows
    )





# ============================================================
# KONEC DELA 2/3
# ============================================================

# ============================================================
# DEL 3/3
# MATEMATIČNI MODEL + REZULTATI
# ============================================================



# ============================================================
# 15. MODEL STRESNE MOČI
# ============================================================

def calculate_stress_power(data):


    SF = data.get(
        "SF_weight",
        0
    )


    PF = data.get(
        "PF_weight",
        0
    )


    PR = data.get(
        "PR_weight",
        0
    )



    # zaščita

    denominator = PF + 1



    stress_ratio = (

        SF /

        denominator

    )



    recovery_factor = (

        1 +

        PR / 10

    )



    adjusted = (

        stress_ratio /

        recovery_factor

    )



    sigma = (

        math.log(
            adjusted + 1
        )

        /

        math.log(10)

    ) * 50



    sigma = max(

        0,

        min(

            50,

            sigma

        )

    )



    return sigma





# ============================================================
# 16. ENERGETSKI MODEL
# ============================================================

def calculate_energy(
        sigma):


    W_I = 2500


    loss = (

        W_I *

        sigma /

        50

    )


    useful = (

        W_I -

        loss

    )


    efficiency = (

        useful /

        W_I

    ) * 100



    return (

        W_I,

        loss,

        useful,

        efficiency

    )






# ============================================================
# 17. TOP FAKTORJI
# ============================================================

def top_factors(
        df,
        category):


    if df.empty:

        return pd.DataFrame()



    result = (

        df[

            df["Kategorija"]

            ==

            category

        ]

        .groupby(
            "Faktor",
            as_index=False
        )

        ["Moč"]

        .sum()

        .sort_values(

            "Moč",

            ascending=False

        )

        .head(10)

    )


    return result






# ============================================================
# 18. GLAVNI PROGRAM
# ============================================================


if "dataset" in st.session_state:


    df = st.session_state["dataset"]



    st.divider()



    st.header(
        "🧠 Začetek večfaktorske AI analize"
    )



    if st.button(
        "🚀 ZAŽENI AI ANALIZO"
    ):



        if not api_key:


            st.error(
                "Vnesite Gemini API ključ."
            )


        else:


            model = initialize_gemini(

                api_key,

                model_name

            )



            if model:


                with st.spinner(

                    "AI razgrajuje odgovore na več dejavnikov..."

                ):


                    results = run_multifactor_analysis(

                        df,

                        model

                    )



                    aggregated = aggregate_factors(

                        results

                    )



                    factor_df = factors_to_dataframe(

                        aggregated

                    )



                    sigma = calculate_stress_power(

                        aggregated

                    )



                    st.session_state["results"] = results


                    st.session_state["aggregated"] = aggregated


                    st.session_state["factor_df"] = factor_df


                    st.session_state["sigma"] = sigma



                st.success(

                    "AI analiza zaključena."

                )






# ============================================================
# 19. PRIKAZ REZULTATOV
# ============================================================


if "sigma" in st.session_state:


    aggregated = st.session_state[

        "aggregated"

    ]


    factor_df = st.session_state[

        "factor_df"

    ]


    sigma = st.session_state[

        "sigma"

    ]



    W_I, W_LS, W_EU, eta = calculate_energy(

        sigma

    )



    st.divider()


    st.header(

        "📊 Rezultati Psihosocialnega Barometra"

    )



    col1, col2, col3, col4 = st.columns(4)



    with col1:

        st.metric(

            "Stresna moč",

            f"{sigma:.1f} °S"

        )


    with col2:

        st.metric(

            "Izguba energije",

            f"{W_LS:.0f}"

        )


    with col3:

        st.metric(

            "Uporabna energija",

            f"{W_EU:.0f}"

        )


    with col4:

        st.metric(

            "Učinkovitost",

            f"{eta:.1f}%"

        )




    st.divider()



    col_a, col_b = st.columns(2)



    with col_a:


        pie_df = pd.DataFrame(

            {

            "Tip":

                [

                "Stresorji",

                "Pozitivni",

                "Predlogi"

                ],


            "Vrednost":

                [

                aggregated["SF_weight"],

                aggregated["PF_weight"],

                aggregated["PR_weight"]

                ]

            }

        )



        st.plotly_chart(

            px.pie(

                pie_df,

                names="Tip",

                values="Vrednost",

                hole=0.4

            ),

            use_container_width=True

        )





    with col_b:


        st.subheader(

            "Vsi faktorji"

        )


        st.dataframe(

            factor_df,

            use_container_width=True

        )





    st.divider()



    st.subheader(

        "🔥 Najmočnejši stresorji"

    )


    sf_top = top_factors(

        factor_df,

        "Stresorji"

    )


    if not sf_top.empty:


        st.plotly_chart(

            px.bar(

                sf_top,

                x="Moč",

                y="Faktor",

                orientation="h"

            ),

            use_container_width=True

        )





    st.subheader(

        "🛡️ Zaščitni dejavniki"

    )


    pf_top = top_factors(

        factor_df,

        "Pozitivni"

    )


    if not pf_top.empty:


        st.plotly_chart(

            px.bar(

                pf_top,

                x="Moč",

                y="Faktor",

                orientation="h"

            ),

            use_container_width=True

        )





    st.subheader(

        "💡 Predlogi izboljšav"

    )


    pr_top = top_factors(

        factor_df,

        "Predlogi"

    )


    st.dataframe(

        pr_top

    )





    # ========================================================
    # IZVOZ
    # ========================================================


    csv = factor_df.to_csv(

        index=False

    ).encode(

        "utf-8"

    )



    st.download_button(

        label="⬇️ Prenesi rezultat CSV",

        data=csv,

        file_name="Psihosocialni_Barometer_rezultat.csv",

        mime="text/csv"

    )



# ============================================================
# KONEC APLIKACIJE
# ============================================================
