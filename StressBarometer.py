# ============================================================
# PSIHOSOCIALNI BAROMETER v2.0
# Karl Petrič, 2025/2026
#
# Namen:
# Večnivojska AI analiza psihosocialnih dejavnikov
#
# Izboljšava glede na v1:
# - en odgovor lahko vsebuje več SF, PF in PR elementov
# - AI vrača strukturiran JSON
# - faktorji se agregirajo po vseh respondentih
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
    page_title="Psihosocialni Barometer v2",
    layout="wide"
)


st.title(
    "📊 Psihosocialni Barometer v2.0 "
    "(Večfaktorska AI analiza stresa)"
)


st.markdown("""
### Model Petrič (2025)

Nova verzija omogoča:

✅ zaznavanje več stresorjev iz enega odgovora  
✅ zaznavanje pozitivnih zaščitnih faktorjev  
✅ zaznavanje predlogov za zmanjšanje stresa  
✅ izračun realnejše stresne moči

Primer:

> "Delo me zelo obremenjuje, nimam časa, 
> vendar me družina podpira in šport mi pomaga."

AI bo identificiral:

**SF**
- delovna obremenitev
- pomanjkanje časa

**PF**
- družinska podpora
- šport

**PR**
- boljša organizacija časa
""")



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
        "API ključ dobite v Google AI Studio"
    )


    st.divider()


    model_name = st.selectbox(
        "AI model:",
        [
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
    )


    st.write(
        "Avtor modela:"
    )

    st.write(
        "Karl Petrič"
    )



# ============================================================
# 3. KONFIGURACIJA GEMINI
# ============================================================

def initialize_gemini(api_key, model_name):

    """
    Inicializacija Gemini modela
    """

    if not api_key:
        return None


    try:

        genai.configure(
            api_key=api_key
        )


        model = genai.GenerativeModel(
            model_name
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
    Univerzalni uvoz:
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

            text = (
                uploaded_file
                .read()
                .decode("utf-8")
            )


            df = pd.DataFrame(
                text.splitlines(),
                columns=["Odgovor"]
            )


        else:

            st.error(
                "Nepodprt format"
            )

            return None



        return df



    except Exception as e:


        st.error(
            f"Napaka pri uvozu: {e}"
        )


        return None





# ============================================================
# 5. STANDARDIZACIJA STOLPCA
# ============================================================

def prepare_dataframe(df):


    if df is None:
        return None



    # prvi stolpec postavimo kot odgovor

    if "Odgovor" not in df.columns:


        df.rename(
            columns={
                df.columns[0]:
                "Odgovor"
            },
            inplace=True
        )



    # odstranimo prazne odgovore


    df["Odgovor"] = (
        df["Odgovor"]
        .astype(str)
        .str.strip()
    )


    df = df[
        df["Odgovor"]
        .str.len()
        > 5
    ]



    df.reset_index(
        drop=True,
        inplace=True
    )



    return df




# ============================================================
# 6. POMOŽNE FUNKCIJE ZA JSON
# ============================================================

def clean_json_response(text):

    text = text.strip()

    # odstrani markdown
    text = re.sub(
        r"```json",
        "",
        text
    )

    text = re.sub(
        r"```",
        "",
        text
    )


    # poišči prvi JSON objekt

    start = text.find("{")
    end = text.rfind("}")


    if start >= 0 and end >= 0:

        text = text[start:end+1]


    return text.strip()





def empty_analysis():

    """
    Privzeta struktura
    """

    return {

        "stresorji": [],

        "pozitivni_dejavniki": [],

        "predlogi": [],

        "intenzivnost": 0

    }




# ============================================================
# 7. ZAČETEK APLIKACIJE
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
            df.head(10)
        )



        st.session_state["dataset"] = df



# ============================================================
# KONEC DELA 1/3
# ============================================================

# ============================================================
# DEL 2/3
# VEČFAKTORSKA AI ANALIZA
# ============================================================



def build_analysis_prompt(answer):
    """
    Gemini prompt za hierarhično ekstrakcijo
    več psihosocialnih faktorjev.
    """


    prompt = f"""

Analiziraj odgovor respondenta po modelu
Psihosocialni Barometer Petrič (2025).

Pomembno:

En odgovor lahko vsebuje VEČ dejavnikov.

Identificiraj:

1. STRESORJE
   (kaj povzroča stres)

2. POZITIVNE DEJAVNIKE
   (kaj zmanjšuje stres ali povečuje odpornost)

3. PREDLOGE
   (kaj bi lahko zmanjšalo stres)


Vsak faktor ovrednoti z intenzivnostjo:

0 = zanemarljivo

1 = zelo nizko

2 = nizko

3 = srednje

4 = visoko

5 = zelo visoko



Vrni IZKLJUČNO veljaven JSON:


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





# ------------------------------------------------------------
# AI ANALIZA ENEGA ODGOVORA
# ------------------------------------------------------------


def analyze_single_response(model, answer):

    default = empty_analysis()


    try:

        response = model.generate_content(
            build_analysis_prompt(answer)
        )


        raw = response.text


        raw = clean_json_response(
            raw
        )


        data = json.loads(
            raw
        )


        # preverjanje strukture JSON

        if "stresorji" not in data:

            data["stresorji"] = []


        if "pozitivni_dejavniki" not in data:

            data["pozitivni_dejavniki"] = []


        if "predlogi" not in data:

            data["predlogi"] = []


        return data



    except Exception as e:


        st.warning(
            f"AI napaka: {e}"
        )


        st.write(
            "Originalni odgovor AI:"
        )


        if "raw" in locals():

            st.code(
                raw
            )

        else:

            st.code(
                "Gemini ni vrnil odgovora"
            )


        return default





# ============================================================
# ANALIZA CELOTNEGA DATASETA
# ============================================================


def run_multifactor_analysis(df, model):


    results = []



    progress = st.progress(
        0
    )


    total = len(df)



    for i, row in df.iterrows():


        answer = row["Odgovor"]



        result = analyze_single_response(
            model,
            answer
        )


        results.append(
            result
        )



        progress.progress(
            (i+1)/total
        )



        # preprečevanje omejitve API

        if (i+1)%20 == 0:

            time.sleep(2)



    return results





# ============================================================
# AGREGACIJA VEČ FAKTORJEV
# ============================================================


def aggregate_factors(results):


    data = {

        "SF_count": 0,
        "PF_count": 0,
        "PR_count": 0,

        "SF_weight": 0,
        "PF_weight": 0,
        "PR_weight": 0,

        "SF_list": [],
        "PF_list": [],
        "PR_list": []

    }



    for item in results:


        # ====================================================
        # STRESORJI
        # ====================================================

        for sf in item.get(
            "stresorji",
            []
        ):

            try:

                intensity = int(
                    sf.get(
                        "intenzivnost",
                        1
                    )
                )

            except:

                intensity = 1



            data["SF_count"] += 1

            data["SF_weight"] += intensity


            data["SF_list"].append(
                (
                    sf.get(
                        "faktor",
                        "neznan stresor"
                    ),
                    intensity
                )
            )



        # ====================================================
        # POZITIVNI DEJAVNIKI
        # ====================================================

        for pf in item.get(
            "pozitivni_dejavniki",
            []
        ):


            try:

                intensity = int(
                    pf.get(
                        "intenzivnost",
                        1
                    )
                )

            except:

                intensity = 1



            data["PF_count"] += 1

            data["PF_weight"] += intensity



            data["PF_list"].append(
                (
                    pf.get(
                        "faktor",
                        "neznan pozitivni dejavnik"
                    ),
                    intensity
                )
            )



        # ====================================================
        # PREDLOGI
        # ====================================================

        for pr in item.get(
            "predlogi",
            []
        ):


            try:

                effect = int(
                    pr.get(
                        "ucinek",
                        1
                    )
                )


            except:

                effect = 1



            data["PR_count"] += 1

            data["PR_weight"] += effect



            data["PR_list"].append(
                (
                    pr.get(
                        "faktor",
                        "neznan predlog"
                    ),
                    effect
                )
            )



    return data





# ============================================================
# PRETVORBA V DATAFRAME
# ============================================================


def factors_to_dataframe(aggregated):


    rows=[]



    for category, key in [

        ("Stresorji",
         "SF_list"),

        ("Pozitivni",
         "PF_list"),

        ("Predlogi",
         "PR_list")

    ]:


        for name,value in aggregated[key]:


            rows.append({

                "Kategorija":
                    category,

                "Faktor":
                    name,

                "Moč":
                    value

            })



    return pd.DataFrame(rows)




# ============================================================
# KONEC DELA 2/3
# ============================================================

# ============================================================
# DEL 3/3
# MATEMATIČNI MODEL + PRIKAZ REZULTATOV
# ============================================================



# ============================================================
# NOV MODEL STRESNE MOČI
# ============================================================


def calculate_stress_power(data):

    """
    Novi Petrič model 2026

    Rezultat:
    0 - 50 stresnih stopinj

    Višja vrednost =
    večja psihosocialna obremenitev
    """



    SF = data["SF_weight"]

    PF = data["PF_weight"]

    PR = data["PR_weight"]



    # zaščita pred ničlo

    if PF == 0:
        PF = 1



    # ------------------------------------------------
    # 1. Osnovna stresna obremenitev
    # ------------------------------------------------

    stress_ratio = (
        SF /
        (PF + 1)
    )



    # ------------------------------------------------
    # 2. Korekcija zaradi predlogov
    # ------------------------------------------------

    recovery_factor = (
        1 +
        PR / 10
    )



    adjusted = (
        stress_ratio /
        recovery_factor
    )



    # ------------------------------------------------
    # 3. Logaritemska normalizacija
    #
    # prepreči eksplozijo rezultatov
    # ------------------------------------------------


    sigma = (

        math.log(
            adjusted + 1
        )

        /

        math.log(10)

    ) * 50



    # omejitev

    sigma = max(
        0,
        min(
            50,
            sigma
        )
    )


    return sigma





# ============================================================
# ENERGETSKI MODEL
# ============================================================


def calculate_energy(sigma):


    """
    Model psihične energije

    W_I = začetni energijski potencial
    """

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
# TOP FAKTORJI
# ============================================================


def top_factors(df, category):


    result = (

        df[
            df["Kategorija"]
            ==
            category
        ]

        .groupby(
            "Faktor"
        )

        ["Moč"]

        .sum()

        .sort_values(
            ascending=False
        )

        .head(10)

        .reset_index()

    )


    return result





# ============================================================
# GLAVNI PROGRAM
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


        st.write(
            "DEBUG AI REZULTATI"
        )

        st.json(
            results[:3]
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



                    W_I, W_LS, W_EU, eta = calculate_energy(
                        sigma
                    )



                    st.session_state[
                        "results"
                    ] = results


                    st.session_state[
                        "factor_df"
                    ] = factor_df


                    st.session_state[
                        "aggregated"
                    ] = aggregated


                    st.session_state[
                        "sigma"
                    ] = sigma





# ============================================================
# PRIKAZ REZULTATOV
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



    st.header(
        "📊 Rezultati Psihosocialnega Barometra"
    )



    col1,col2,col3,col4 = st.columns(4)



    with col1:

        st.metric(
            "Stresna moč",
            f"{sigma:.1f} °S"
        )



    with col2:

        st.metric(
            "Izguba energije",
            f"{W_LS:.0f} kcal"
        )



    with col3:

        st.metric(
            "Uporabna energija",
            f"{W_EU:.0f} kcal"
        )



    with col4:

        st.metric(
            "Energetska učinkovitost",
            f"{eta:.1f}%"
        )




    st.divider()



    c1,c2 = st.columns(2)



    with c1:


        st.subheader(
            "Razmerje SF / PF / PR"
        )


        pie_df = pd.DataFrame({

            "Tip":[
                "Stresorji",
                "Pozitivni",
                "Predlogi"
            ],

            "Vrednost":[

                aggregated["SF_weight"],

                aggregated["PF_weight"],

                aggregated["PR_weight"]

            ]

        })



        st.plotly_chart(

            px.pie(
                pie_df,
                names="Tip",
                values="Vrednost",
                hole=0.4
            ),

            use_container_width=True

        )





    with c2:


        st.subheader(
            "Vsi identificirani faktorji"
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


    st.download_button(

        label="⬇️ Prenesi Excel rezultat",

        data=factor_df.to_csv(
            index=False
        ),

        file_name=
        "Psihosocialni_Barometer_rezultat.csv",

        mime=
        "text/csv"

    )



# ============================================================
# KONEC DELA 3/3
# ============================================================
