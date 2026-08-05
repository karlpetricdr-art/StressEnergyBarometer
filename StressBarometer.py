# ============================================================
# PSIHOSOCIALNI BAROMETER v2.1
# Karl Petrič, 2025/2026
#
# Nova Gemini SDK verzija
# google-genai
#
# DEL 1/3
# ============================================================


import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
import math
import re

from google import genai



# ============================================================
# 1. STREAMLIT NASTAVITVE
# ============================================================

st.set_page_config(
    page_title="Psihosocialni Barometer v2.1",
    layout="wide"
)


st.title(
    "📊 Psihosocialni Barometer v2.1"
)


st.markdown(
"""
### Model Petrič (2025/2026)

AI večfaktorska analiza psihosocialnih dejavnikov.

Aplikacija omogoča:

✅ več stresorjev iz enega odgovora  
✅ zaščitne dejavnike  
✅ predloge izboljšav  
✅ strukturiran JSON izhod  
✅ agregacijo respondentov
"""
)



# ============================================================
# 2. SIDEBAR
# ============================================================

with st.sidebar:


    st.header(
        "⚙️ Nastavitve"
    )


    api_key = st.text_input(

        "Gemini API ključ:",

        type="password"

    )


    st.divider()



    model_name = st.selectbox(

    "AI model:",

    [

        "gemini-2.0-flash",

        "gemini-2.0-flash-lite",

        "gemma-4-26b-a4b-it",

        "gemma-4-31b-it"

    ]

)


    st.info(
        "Priporočen model: gemini-2.0-flash"
    )


    st.write(
        "Avtor:"
    )


    st.write(
        "Karl Petrič"
    )





# ============================================================
# 3. GEMINI INICIALIZACIJA
# ============================================================


def initialize_gemini(
        api_key):


    """
    Nova Gemini SDK inicializacija.
    """


    if not api_key:

        return None



    try:


        client = genai.Client(

            api_key=api_key

        )


        return client



    except Exception as e:


        st.error(

            f"Gemini napaka: {e}"

        )


        return None





# ============================================================
# 4. GEMINI TEST
# ============================================================


def test_gemini(client, model_name):


    try:


        response = client.models.generate_content(

            model=model_name,

            contents="Pozdravi uporabnika."

        )


        return response.text



    except Exception as e:


        return f"Napaka modela: {e}"







# ============================================================
# 5. NALAGANJE PODATKOV
# ============================================================


def load_dataset(uploaded_file):

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


        elif filename.endswith(".tsv"):

            df = pd.read_csv(
                uploaded_file,
                sep="\t",
                encoding="utf-8"
            )


        elif filename.endswith(".txt"):

            df = pd.read_csv(
                uploaded_file,
                sep="\t",
                encoding="utf-8"
            )


        else:

            st.error(
                "Nepodprt format datoteke. Uporabite XLSX, CSV, TSV ali TXT."
            )

            return None



        return df



    except Exception as e:

        st.error(
            f"Napaka pri uvozu podatkov: {e}"
        )

        return None

# ============================================================
# 6. PRIPRAVA DATAFRAME
# ============================================================


def prepare_dataframe(df):


    if df is None:

        return None



    if len(df.columns)==0:

        return None




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



    df = df[

        df["Odgovor"].str.len()>5

    ]



    df.reset_index(

        drop=True,

        inplace=True

    )


    return df






# ============================================================
# 7. JSON FUNKCIJE
# ============================================================


def clean_json_response(text):


    if not text:

        return "{}"



    text=text.strip()



    text=re.sub(

        r"```json",

        "",

        text,

        flags=re.IGNORECASE

    )


    text=text.replace(

        "```",

        ""

    )



    start=text.find("{")

    end=text.rfind("}")



    if start>=0 and end>=0:

        text=text[start:end+1]



    return text.strip()





def empty_analysis():


    return {


        "stresorji":[],

        "pozitivni_dejavniki":[],

        "predlogi":[]

    }





# ============================================================
# 8. UPLOAD PODATKOV
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



        st.session_state["dataset"]=df





# ============================================================
# KONEC DELA 1/3
# ============================================================

# ============================================================
# DEL 2/3
# GEMINI AI ANALIZA + AGREGACIJA FAKTORJEV
# ============================================================



# ============================================================
# 9. PROMPT ZA AI ANALIZO
# ============================================================


def build_analysis_prompt(answer):


    prompt = f"""

Analiziraj odgovor respondenta po modelu:

Psihosocialni Barometer Petrič (2025/2026).


En odgovor lahko vsebuje več dejavnikov.


Identificiraj:


1. STRESORJE
Kaj povzroča stres.


2. POZITIVNE DEJAVNIKE
Kaj zmanjšuje stres.


3. PREDLOGE
Kaj bi izboljšalo stanje.


Ocena intenzivnosti:

0 = ni prisotno
1 = zelo nizko
2 = nizko
3 = srednje
4 = visoko
5 = zelo visoko


Vrni IZKLJUČNO JSON.


Uporabi naslednjo strukturo:


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

{answer}


"""


    return prompt





# ============================================================
# 10. ANALIZA ENEGA ODGOVORA
# ============================================================


def analyze_single_response(
        client,
        model_name,
        answer):


    default = empty_analysis()



    try:


        response = client.models.generate_content(

            model=model_name,

            contents=

            build_analysis_prompt(

                answer

            )

        )



        raw = response.text



        cleaned = clean_json_response(

            raw

        )



        data = json.loads(

            cleaned

        )



        if not isinstance(data, dict):

            return default



        if "stresorji" not in data:

            data["stresorji"]=[]


        if "pozitivni_dejavniki" not in data:

            data["pozitivni_dejavniki"]=[]


        if "predlogi" not in data:

            data["predlogi"]=[]



        return data



    except Exception as e:


        st.warning(

            f"AI analiza neuspešna: {e}"

        )


        return default






# ============================================================
# 11. ANALIZA CELOTNEGA DATASETA
# ============================================================


def run_multifactor_analysis(
        df,
        client,
        model_name):


    results=[]


    progress = st.progress(0)


    total=len(df)



    for i,row in df.iterrows():


        answer=row["Odgovor"]



        result = analyze_single_response(

            client,

            model_name,

            answer

        )



        results.append(

            result

        )



        progress.progress(

            int(

                ((i+1)/total)*100

            )

        )



        # zaščita omejitev API

        if (i+1)%20==0:

            time.sleep(2)



    return results







# ============================================================
# 12. VARNA KONVERZIJA
# ============================================================


def safe_number(value):


    try:

        return int(value)


    except:

        return 0







# ============================================================
# 13. AGREGACIJA
# ============================================================


def aggregate_factors(results):


    data={


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



        # ----------------------------
        # STRESORJI
        # ----------------------------


        for sf in item.get(

            "stresorji",

            []

        ):


            name=sf.get(

                "faktor",

                "neznan"

            )


            value=safe_number(

                sf.get(

                    "intenzivnost",

                    0

                )

            )



            data["SF_count"]+=1

            data["SF_weight"]+=value



            data["SF_list"].append(

                (

                    name,

                    value

                )

            )





        # ----------------------------
        # POZITIVNI
        # ----------------------------


        for pf in item.get(

            "pozitivni_dejavniki",

            []

        ):


            name=pf.get(

                "faktor",

                "neznan"

            )


            value=safe_number(

                pf.get(

                    "intenzivnost",

                    0

                )

            )



            data["PF_count"]+=1

            data["PF_weight"]+=value



            data["PF_list"].append(

                (

                    name,

                    value

                )

            )





        # ----------------------------
        # PREDLOGI
        # ----------------------------


        for pr in item.get(

            "predlogi",

            []

        ):


            name=pr.get(

                "faktor",

                "neznan"

            )


            value=safe_number(

                pr.get(

                    "ucinek",

                    0

                )

            )



            data["PR_count"]+=1

            data["PR_weight"]+=value



            data["PR_list"].append(

                (

                    name,

                    value

                )

            )



    return data






# ============================================================
# 14. ZDRUŽEVANJE FAKTORJEV
# ============================================================


def merge_factors(items):


    merged={}



    for name,value in items:


        if name not in merged:

            merged[name]=0



        merged[name]+=value



    return list(

        merged.items()

    )






# ============================================================
# 15. DATAFRAME REZULTATOV
# ============================================================


def factors_to_dataframe(
        aggregated):


    rows=[]



    categories=[

        ("Stresorji","SF_list"),

        ("Pozitivni","PF_list"),

        ("Predlogi","PR_list")

    ]



    for category,key in categories:


        for name,value in merge_factors(

            aggregated[key]

        ):


            rows.append(

                {

                "Kategorija":category,

                "Faktor":name,

                "Moč":value

                }

            )



    return pd.DataFrame(rows)





# ============================================================
# KONEC DELA 2/3
# ============================================================

# ============================================================
# DEL 3/3
# MATEMATIČNI MODEL + GLAVNI PROGRAM + REZULTATI
# ============================================================



# ============================================================
# 16. MODEL STRESNE MOČI
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



    stress_ratio = (

        SF /

        (PF + 1)

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



    sigma=max(

        0,

        min(

            50,

            sigma

        )

    )



    return sigma





# ============================================================
# 17. ENERGETSKI MODEL
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



    efficiency=(

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
# 18. TOP FAKTORJI
# ============================================================


def top_factors(
        df,
        category):


    if df.empty:

        return pd.DataFrame()



    result=(

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
# 19. GLAVNI PROGRAM
# ============================================================


if "dataset" in st.session_state:


    df = st.session_state["dataset"]



    st.divider()



    st.header(

        "🧠 AI analiza respondentov"

    )



    if st.button(

        "🚀 ZAŽENI AI ANALIZO"

    ):



        if not api_key:


            st.error(

                "Vnesite Gemini API ključ."

            )



        else:



            client = initialize_gemini(

                api_key

            )



                        if client:


                with st.spinner(

                    f"{model_name} analizira odgovore..."

                ):


                    results = run_multifactor_analysis(

                        df,

                        client,

                        model_name

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

                    "Analiza uspešno zaključena."

                )







# ============================================================
# 20. PRIKAZ REZULTATOV
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





    col1,col2,col3,col4 = st.columns(4)



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



    c1,c2 = st.columns(2)



    with c1:



        pie_df=pd.DataFrame(

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







    with c2:


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

        pr_top,

        use_container_width=True

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

        label="⬇️ Prenesi CSV rezultat",

        data=csv,

        file_name=

        "Psihosocialni_Barometer_rezultat.csv",

        mime=

        "text/csv"

    )



# ============================================================
# KONEC APLIKACIJE
# ============================================================
