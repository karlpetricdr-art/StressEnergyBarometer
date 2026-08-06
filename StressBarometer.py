# ============================================================
# PSIHOSOCIALNI BAROMETER v2.5
#
# DEL 1/5
#
# OSNOVA APLIKACIJE
# STREAMLIT VMESNIK
# NALAGANJE PODATKOV
# PRIPRAVA ODGOVOROV
#
# AI in matematika sta ločena modula
# ============================================================


import streamlit as st
import pandas as pd
import json
import time
import re
import plotly.express as px

from google import genai

# ============================================================
# 1. STREAMLIT NASTAVITVE
# ============================================================


st.set_page_config(

    page_title="Psihosocialni Barometer v2.5",

    layout="wide"

)



st.title(
    "📊 Psihosocialni Barometer v2.5"
)



st.markdown(

"""
### Model Petrič (2025/2026)

Ločena arhitektura:

- AI modul → klasifikacija psihosocialnih dejavnikov
- Python modul → matematični izračun stresne moči in energije

"""

)



# ============================================================
# 2. KLASIFIKACIJSKE ENOTE
# ============================================================


UNIT_CODES = [

    "AT",
    "ST",
    "IP",
    "PS",
    "SO",
    "HB"

]


UNIT_LABELS = {


    "AT":
    "Pozorna (fizična)",


    "ST":
    "Storilnostna",


    "IP":
    "Individualna psihološka",


    "PS":
    "Delna socialna",


    "SO":
    "Socialna",


    "HB":
    "Zdravstveno-biološka"

}



UNIT_DESCRIPTIONS = {


    "AT":
    "okoljski in fizični vplivi: hrup, svetloba, temperatura, ergonomija",


    "ST":
    "naloge, informacije, postopki, delovna obremenitev",


    "IP":
    "notranje psihološko stanje posameznika",


    "PS":
    "pričakovanja, priznanje, nagrajevanje, status",


    "SO":
    "odnosi, konflikti, sodelovanje, socialna podpora",


    "HB":
    "zdravje, bolezen, prehrana, telesno stanje"

}



# ============================================================
# 3. SIDEBAR
# ============================================================


with st.sidebar:


    st.header(
        "⚙️ Nastavitve"
    )


    api_key = st.text_input(

        "Google API ključ",

        type="password"

    )


    st.divider()



    model_name = st.selectbox(

        "AI model",

        [

            "gemini-2.0-flash",

            "gemini-2.0-flash-lite",

            "gemma-4-26b-a4b-it",

            "gemma-4-31b-it"

        ]

    )


    st.divider()



    max_retries = st.slider(

        "Ponovitve ob napaki",

        0,

        5,

        3

    )


    request_delay = st.slider(

        "Premor med AI analizami (s)",

        0.0,

        5.0,

        0.5

    )



    st.divider()



    test_mode = st.checkbox(

        "Testni način (3 odgovori)",

        value=False

    )



    st.divider()



    if st.button(

        "🗑️ RESET",

        use_container_width=True

    ):


        for key in list(st.session_state.keys()):

            del st.session_state[key]


        st.rerun()



# ============================================================
# 4. UPLOAD DATOTEKE
# ============================================================


uploaded_file = st.file_uploader(

    "📂 Naloži podatke respondentov "
    "(TXT, CSV, XLSX - do 200 MB)",

    type=[

        "txt",

        "csv",

        "xlsx"

    ]

)



# ============================================================
# 5. BRANJE DATOTEK
# ============================================================


def load_dataset(file):


    if file is None:

        return None



    filename = file.name.lower()



    try:


        if filename.endswith(".xlsx"):


            df = pd.read_excel(file)



        elif filename.endswith(".csv"):


            try:

                df = pd.read_csv(

                    file,

                    encoding="utf-8"

                )

            except:


                file.seek(0)


                df = pd.read_csv(

                    file,

                    encoding="latin1"

                )



        elif filename.endswith(".txt"):


            try:

                df = pd.read_csv(

                    file,

                    sep="\t",

                    encoding="utf-8"

                )

            except:


                file.seek(0)


                df = pd.read_csv(

                    file,

                    sep="\t",

                    encoding="latin1"

                )



        else:


            st.error(
                "Nepodprt format."
            )

            return None



        return df



    except Exception as e:


        st.error(

            f"Napaka pri branju datoteke: {e}"

        )


        return None



# ============================================================
# 6. STANDARDIZACIJA ODGOVOROV
# ============================================================


def prepare_dataframe(df):


    if df is None:

        return None



    if len(df.columns) == 0:

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

        df["Odgovor"].str.len() > 5

    ]



    df.reset_index(

        drop=True,

        inplace=True

    )



    return df



# ============================================================
# 7. IZVEDBA UPLOADA
# ============================================================


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
# 8. POMOŽNE FUNKCIJE
# ============================================================


def clean_json_response(text):


    if not text:

        return "{}"



    text = text.strip()



    text = re.sub(

        r"```json",

        "",

        text,

        flags=re.I

    )


    text = text.replace(

        "```",

        ""

    )



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
# KONEC DELA 1/5
# ============================================================

# ============================================================
# PSIHOSOCIALNI BAROMETER v2.5
#
# DEL 2/5
#
# AI KLASIFIKACIJSKI MODUL
#
# Naloga AI:
# - prepozna stresorje
# - prepozna pozitivne dejavnike
# - prepozna predloge
# - razvrsti faktorje v 6 enot
# - določi intenzivnost 0-5
#
# AI NE IZRAČUNAVA STRESA
# ============================================================


from google import genai



# ============================================================
# 9. AI INICIALIZACIJA
# ============================================================


def initialize_ai(api_key):


    if not api_key:

        return None



    try:


        client = genai.Client(

            api_key=api_key

        )


        return client



    except Exception as e:


        st.error(

            f"AI inicializacija neuspešna: {e}"

        )


        return None



# ============================================================
# 10. TEST AI POVEZAVE
# ============================================================


def test_ai(client, model_name):


    try:


        response = client.models.generate_content(

            model=model_name,

            contents="Pozdravi uporabnika."

        )


        return response.text



    except Exception as e:


        return f"Napaka: {e}"



# ============================================================
# 11. AI PROMPT ZA KLASIFIKACIJO
# ============================================================


def build_classifier_prompt(answer):


    unit_text = ""


    for code in UNIT_CODES:


        unit_text += (

            f"{code} - "
            f"{UNIT_LABELS[code]}: "
            f"{UNIT_DESCRIPTIONS[code]}\n"

        )



    prompt = f"""

Si strokovni analizator psihosocialnih dejavnikov.

Uporabljaš model:
Psihosocialni Barometer Petrič (2025/2026).

Tvoja naloga NI izračun stresne moči.

Tvoja edina naloga je:

1. najti dejavnike v odgovoru,
2. jih razvrstiti,
3. določiti intenzivnost.


Klasifikacijske enote:


{unit_text}



Kategorije:


STRESORJI

Kaj povzroča obremenitev.


POZITIVNI_DEJAVNIKI

Kaj zmanjšuje stres ali povečuje odpornost.


PREDLOGI

Kaj bi lahko izboljšalo stanje.



Lestvica:

0 = ni prisotno

1 = zelo nizko

2 = nizko

3 = srednje

4 = visoko

5 = zelo visoko



Vrni IZKLJUČNO JSON.


FORMAT:


{{
"stresorji":[

 {{

 "faktor":"",

 "enota":"AT/ST/IP/PS/SO/HB",

 "intenzivnost":0

 }}

],


"pozitivni_dejavniki":[

 {{

 "faktor":"",

 "enota":"AT/ST/IP/PS/SO/HB",

 "intenzivnost":0

 }}

],


"predlogi":[

 {{

 "faktor":"",

 "enota":"AT/ST/IP/PS/SO/HB",

 "ucinek":0

 }}

]

}}



ODGOVOR RESPONDENTA:


{answer}

"""


    return prompt



# ============================================================
# 12. VALIDACIJA AI REZULTATA
# ============================================================


def validate_ai_result(data):


    if not isinstance(data, dict):

        return False



    required = [

        "stresorji",

        "pozitivni_dejavniki",

        "predlogi"

    ]



    for key in required:


        if key not in data:


            return False



        if not isinstance(

            data[key],

            list

        ):


            return False



    return True



# ============================================================
# 13. ANALIZA ENEGA ODGOVORA
# ============================================================


def analyze_single_response(

        client,

        model_name,

        answer,

        max_retries=3):


    default = empty_analysis()



    attempt = 0


    wait = 2



    while attempt <= max_retries:



        try:



            response = client.models.generate_content(

                model=model_name,

                contents=build_classifier_prompt(answer)

            )



            raw = response.text



            cleaned = clean_json_response(

                raw

            )



            data = json.loads(

                cleaned

            )



            if validate_ai_result(data):


                return data, "OK"



            else:


                return default, "INVALID_JSON"



        except json.JSONDecodeError:



            attempt += 1



            if attempt > max_retries:


                return default, "INVALID_JSON"



            time.sleep(wait)

            wait *= 2




        except Exception as e:



            error = str(e)



            attempt += 1



            if attempt > max_retries:



                if "429" in error or "RESOURCE_EXHAUSTED" in error:


                    return default, "QUOTA_ERROR"



                return default, "ERROR"



            time.sleep(wait)

            wait *= 2



    return default, "ERROR"




# ============================================================
# 14. ANALIZA CELOTNEGA DATASETA
# ============================================================


def run_ai_classification(

        df,

        client,

        model_name,

        test_mode=False,

        max_retries=3,

        request_delay=0.5):



    results = []



    status = {


        "OK":0,

        "INVALID_JSON":0,

        "QUOTA_ERROR":0,

        "ERROR":0

    }



    progress = st.progress(0)

    message = st.empty()



    if test_mode:


        df = df.head(3)



    total = len(df)



    start = time.time()



    for index, row in df.iterrows():



        answer = row["Odgovor"]



        result, state = analyze_single_response(

            client,

            model_name,

            answer,

            max_retries

        )



        results.append(

            result

        )



        status[state] += 1



        done = index + 1



        progress.progress(

            int(done / total * 100)

        )



        elapsed = time.time() - start



        remaining = (

            (total-done)

            *

            elapsed

            /

            done

        )



        message.text(

            f"AI klasifikacija: {done}/{total} | "

            f"OK={status['OK']} | "

            f"Napake={status['ERROR']} | "

            f"Preostanek ~ {remaining:.0f}s"

        )



        if request_delay > 0:


            time.sleep(

                request_delay

            )



    progress.empty()

    message.empty()



    return results, status, total



# ============================================================
# KONEC DELA 2/5
# ============================================================

# ============================================================
# PSIHOSOCIALNI BAROMETER v2.5
#
# DEL 3/5
#
# PODATKOVNI ENGINE
#
# Namen:
# - prevzame AI rezultate
# - šteje faktorje
# - združuje faktorje
# - pripravi podatke za matematični model
#
# Brez AI in brez izračuna stresne moči
# ============================================================



# ============================================================
# 15. PRAZEN PODATKOVNI BLOK
# ============================================================


def empty_bucket():


    return {


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



# ============================================================
# 16. VARNA ŠTEVILA
# ============================================================


def safe_number(value):


    try:


        value = int(value)


        if value < 0:


            return 0



        if value > 5:


            return 5



        return value



    except:


        return 0



# ============================================================
# 17. VARNA ENOTA
# ============================================================


def safe_unit(value):


    if isinstance(value,str):


        value=value.strip().upper()



        if value in UNIT_CODES:


            return value



    return "NEZ"



# ============================================================
# 18. AGREGACIJA AI REZULTATOV
# ============================================================


def aggregate_factors(results):


    """

    Vhod:

    AI rezultati posameznih respondentov


    Izhod:


    aggregated

        vsi faktorji skupaj



    units_data

        faktorji po šestih enotah


    """



    aggregated = empty_bucket()



    units_data = {


        code:

        empty_bucket()

        for code in UNIT_CODES

    }



    units_data["NEZ"] = empty_bucket()



    for item in results:



        # --------------------------------
        # STRESORJI
        # --------------------------------


        for factor in item.get(

            "stresorji",

            []

        ):



            name = factor.get(

                "faktor",

                "neznano"

            )



            value = safe_number(

                factor.get(

                    "intenzivnost",

                    0

                )

            )



            unit = safe_unit(

                factor.get(

                    "enota",

                    ""

                )

            )



            aggregated["SF_count"] += 1

            aggregated["SF_weight"] += value

            aggregated["SF_list"].append(

                (

                    name,

                    value

                )

            )



            units_data[unit]["SF_count"] += 1

            units_data[unit]["SF_weight"] += value

            units_data[unit]["SF_list"].append(

                (

                    name,

                    value

                )

            )




        # --------------------------------
        # POZITIVNI DEJAVNIKI
        # --------------------------------


        for factor in item.get(

            "pozitivni_dejavniki",

            []

        ):



            name = factor.get(

                "faktor",

                "neznano"

            )



            value = safe_number(

                factor.get(

                    "intenzivnost",

                    0

                )

            )



            unit = safe_unit(

                factor.get(

                    "enota",

                    ""

                )

            )



            aggregated["PF_count"] += 1

            aggregated["PF_weight"] += value

            aggregated["PF_list"].append(

                (

                    name,

                    value

                )

            )



            units_data[unit]["PF_count"] += 1

            units_data[unit]["PF_weight"] += value

            units_data[unit]["PF_list"].append(

                (

                    name,

                    value

                )

            )




        # --------------------------------
        # PREDLOGI
        # --------------------------------


        for factor in item.get(

            "predlogi",

            []

        ):



            name = factor.get(

                "faktor",

                "neznano"

            )



            value = safe_number(

                factor.get(

                    "ucinek",

                    0

                )

            )



            unit = safe_unit(

                factor.get(

                    "enota",

                    ""

                )

            )



            aggregated["PR_count"] += 1

            aggregated["PR_weight"] += value

            aggregated["PR_list"].append(

                (

                    name,

                    value

                )

            )



            units_data[unit]["PR_count"] += 1

            units_data[unit]["PR_weight"] += value

            units_data[unit]["PR_list"].append(

                (

                    name,

                    value

                )

            )



    return aggregated, units_data



# ============================================================
# 19. ZDRUŽEVANJE ENAKIH FAKTORJEV
# ============================================================


def merge_factors(items):


    merged = {}



    for name,value in items:


        if name not in merged:


            merged[name]=0



        merged[name]+=value



    return list(

        merged.items()

    )



# ============================================================
# 20. PRETVORBA V DATAFRAME
# ============================================================


def factors_to_dataframe(units_data):


    rows=[]



    categories=[


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



    for unit,bucket in units_data.items():



        label = UNIT_LABELS.get(

            unit,

            "Nerazvrščeno"

        )



        for category,key in categories:



            for name,value in merge_factors(

                bucket[key]

            ):



                rows.append(


                    {


                        "Enota":

                        label,


                        "EnotaKoda":

                        unit,


                        "Kategorija":

                        category,


                        "Faktor":

                        name,


                        "Moč":

                        value

                    }


                )



    return pd.DataFrame(rows)



# ============================================================
# 21. TOP FAKTORJI
# ============================================================


def top_factors(

        factor_df,

        category,

        unit="VSE"):


    if factor_df.empty:


        return pd.DataFrame()



    df = factor_df[

        factor_df["Kategorija"] == category

    ]



    if unit != "VSE":


        df = df[

            df["EnotaKoda"] == unit

        ]



    if df.empty:


        return pd.DataFrame()



    result=(


        df.groupby(

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
# 22. SHRANJEVANJE REZULTATOV PO AI ANALIZI
# ============================================================


def store_classification_results(

        results,

        status,

        total):


    aggregated, units_data = aggregate_factors(

        results

    )



    factor_df = factors_to_dataframe(

        units_data

    )



    st.session_state["results"] = results

    st.session_state["status"] = status

    st.session_state["total_processed"] = total

    st.session_state["aggregated"] = aggregated

    st.session_state["units_data"] = units_data

    st.session_state["factor_df"] = factor_df



# ============================================================
# KONEC DELA 3/5
# ============================================================

# ============================================================
# PSIHOSOCIALNI BAROMETER v2.5
#
# DEL 4/5
#
# MATEMATIČNI MODEL
# ============================================================


import math


# ============================================================
# 23. IZRAČUN REALNEGA FAKTORJA Fo
# ============================================================


def calculate_Fo(fv, frv, No):

    if No == 0 or fv == 0:
        return 0

    rho = fv / No

    Co = fv / frv if frv > 0 else 1

    Fo = (Co * rho) / 10

    return Fo



# ============================================================
# 24. IZRAČUN STRESNE MOČI
# ============================================================


def calculate_stress_power(data, No):


    sf_count = data.get("SF_count", 0)
    pf_count = data.get("PF_count", 0)
    pr_count = data.get("PR_count", 0)


    sf_unique = len(
        set(
            x[0]
            for x in data.get("SF_list", [])
        )
    )


    pf_unique = len(
        set(
            x[0]
            for x in data.get("PF_list", [])
        )
    )


    pr_unique = len(
        set(
            x[0]
            for x in data.get("PR_list", [])
        )
    )



    FoSF = calculate_Fo(
        sf_count,
        sf_unique,
        No
    )


    FoPF = calculate_Fo(
        pf_count,
        pf_unique,
        No
    )


    FoPR = calculate_Fo(
        pr_count,
        pr_unique,
        No
    )


    # zaščita pred deljenjem z nič

    if FoPF <= 0:

        FoPF = 0.05


    if FoPR <= 0:

        FoPR = 0.05



    try:

        ratio = (

            FoSF * FoPR

        ) / FoPF


        ratio = max(
            0,
            min(
                1,
                ratio
            )
        )


        sigma = math.degrees(

            math.asin(

                math.sqrt(ratio)

            )

        )


    except Exception:

        sigma = 0



    return {

        "sigma": sigma,

        "FoSF": FoSF,

        "FoPF": FoPF,

        "FoPR": FoPR

    }



# ============================================================
# 25. IZRAČUN PO ENOTAH
# ============================================================


def calculate_unit_results(units_data, No):


    results = {}


    for code in list(UNIT_CODES) + ["NEZ"]:


        bucket = units_data.get(

            code,

            empty_bucket()

        )


        results[code] = calculate_stress_power(

            bucket,

            No

        )


    return results



# ============================================================
# 26. ENERGIJSKI MODEL
# ============================================================


def calculate_energy(
        sigma,
        W_I_kcal=2500):


    loss = (

        W_I_kcal *

        sigma /

        90

    )


    useful = (

        W_I_kcal -

        loss

    )


    efficiency = (

        useful /

        W_I_kcal *

        100

    ) if W_I_kcal else 0



    return {

        "input_kcal": W_I_kcal,

        "loss_kcal": loss,

        "useful_kcal": useful,

        "efficiency": efficiency,

        "loss_kJ": loss * 4.184,

        "useful_kJ": useful * 4.184

    }



# ============================================================
# 27. KLASIFIKACIJA STRESA
# ============================================================


def stress_level_label(sigma):


    if sigma <= 15:

        return "Zelo nizka"


    elif sigma <= 30:

        return "Nizka"


    elif sigma <= 45:

        return "Srednja"


    elif sigma <= 60:

        return "Višja"


    elif sigma <= 75:

        return "Visoka"


    else:

        return "Zelo visoka"



# ============================================================
# 28. GLAVNI IZRAČUN
# ============================================================


def run_calculation_pipeline():


    required = [

        "aggregated",

        "units_data"

    ]


    for key in required:

        if key not in st.session_state:

            return False



    aggregated = st.session_state["aggregated"]

    units_data = st.session_state["units_data"]


    No = st.session_state.get(

        "total_processed",

        0

    )



    sigma_result = calculate_stress_power(

        aggregated,

        No

    )


    unit_results = calculate_unit_results(

        units_data,

        No

    )


    energy = calculate_energy(

        sigma_result["sigma"]

    )



    st.session_state["sigma_result"] = sigma_result

    st.session_state["unit_results"] = unit_results

    st.session_state["energy"] = energy



    return True



# ============================================================
# KONEC DEL 4/5
# ============================================================

# ============================================================
# PSIHOSOCIALNI BAROMETER v2.5
#
# DEL 5/5
#
# GLAVNI PROGRAM
# ZAGON AI ANALIZE
# PRIKAZ REZULTATOV
# IZVOZ
# ============================================================


# ============================================================
# 29. ZAGON AI ANALIZE
# ============================================================


if "dataset" in st.session_state:


    df = st.session_state["dataset"]


    st.divider()


    st.header(
        "🧠 AI klasifikacija odgovorov"
    )


    st.write(
        f"Število pripravljenih odgovorov: {len(df)}"
    )



    if st.button(

        "🚀 ZAŽENI AI ANALIZO",

        use_container_width=True

    ):



        if not api_key:


            st.error(
                "Vnesite Google API ključ."
            )



        else:


            client = initialize_ai(

                api_key

            )


            if client:


                with st.spinner(

                    "AI analizira odgovore..."

                ):



                    results, status, total = run_ai_classification(

                        df,

                        client,

                        model_name,

                        test_mode,

                        max_retries,

                        request_delay

                    )



                    store_classification_results(

                        results,

                        status,

                        total

                    )


                    run_calculation_pipeline()



                st.success(

                    "AI analiza in matematični izračun zaključena."

                )



                st.write(status)



# ============================================================
# 30. PRIKAZ REZULTATOV
# ============================================================


if "sigma_result" in st.session_state:



    sigma_result = st.session_state["sigma_result"]


    energy = st.session_state["energy"]


    unit_results = st.session_state["unit_results"]


    factor_df = st.session_state.get(

        "factor_df",

        pd.DataFrame()

    )



    st.divider()



    st.header(

        "📊 Rezultati Psihosocialnega Barometra"

    )



    # --------------------------------------------------------
    # GLAVNI REZULTAT
    # --------------------------------------------------------


    c1,c2,c3,c4 = st.columns(4)



    with c1:


        st.metric(

            "Stresna moč",

            f"{sigma_result['sigma']:.2f} °S"

        )


        st.caption(

            stress_level_label(

                sigma_result["sigma"]

            )

        )



    with c2:


        st.metric(

            "Izguba energije",

            f"{energy['loss_kcal']:.0f} kcal"

        )



    with c3:


        st.metric(

            "Uporabna energija",

            f"{energy['useful_kcal']:.0f} kcal"

        )



    with c4:


        st.metric(

            "Učinkovitost",

            f"{energy['efficiency']:.1f}%"

        )



    # --------------------------------------------------------
    # REALNI FAKTORJI
    # --------------------------------------------------------


    st.divider()


    st.subheader(

        "Realni faktorji Fo"

    )



    col1,col2,col3 = st.columns(3)



    col1.metric(

        "FoSF",

        f"{sigma_result['FoSF']:.4f}"

    )


    col2.metric(

        "FoPF",

        f"{sigma_result['FoPF']:.4f}"

    )


    col3.metric(

        "FoPR",

        f"{sigma_result['FoPR']:.4f}"

    )



    # --------------------------------------------------------
    # ENOTE
    # --------------------------------------------------------


    st.divider()


    st.subheader(

        "🧩 Stresna moč po klasifikacijskih enotah"

    )



    unit_rows = []



    for code,result in unit_results.items():



        if code == "NEZ" and result["sigma"] == 0:

            continue



        unit_rows.append(

            {

                "Enota":

                UNIT_LABELS.get(

                    code,

                    "Nerazvrščeno"

                ),


                "σ (°S)":

                round(

                    result["sigma"],

                    2

                ),


                "Ocena":

                stress_level_label(

                    result["sigma"]

                ),


                "FoSF":

                round(

                    result["FoSF"],

                    4

                ),


                "FoPF":

                round(

                    result["FoPF"],

                    4

                ),


                "FoPR":

                round(

                    result["FoPR"],

                    4

                )

            }

        )



    unit_df = pd.DataFrame(

        unit_rows

    )



    st.dataframe(

        unit_df,

        use_container_width=True

    )



    if not unit_df.empty:


        st.plotly_chart(

            px.bar(

                unit_df,

                x="Enota",

                y="σ (°S)",

                title="Stresna moč po enotah"

            ),

            use_container_width=True

        )



    # --------------------------------------------------------
    # FAKTORJI
    # --------------------------------------------------------


    st.divider()


    st.subheader(

        "📌 Faktorji"

    )



    if not factor_df.empty:


        st.dataframe(

            factor_df,

            use_container_width=True

        )


    else:


        st.warning(

            "Ni podatkov faktorjev."

        )



    # --------------------------------------------------------
    # TOP FAKTORJI
    # --------------------------------------------------------


    if not factor_df.empty:


        st.divider()


        st.subheader(

            "🔥 Najmočnejši stresorji"

        )


        sf = top_factors(

            factor_df,

            "Stresorji"

        )


        st.dataframe(

            sf,

            use_container_width=True

        )



        st.subheader(

            "🛡️ Pozitivni dejavniki"

        )


        pf = top_factors(

            factor_df,

            "Pozitivni"

        )


        st.dataframe(

            pf,

            use_container_width=True

        )



        st.subheader(

            "💡 Predlogi"

        )


        pr = top_factors(

            factor_df,

            "Predlogi"

        )


        st.dataframe(

            pr,

            use_container_width=True

        )



    # --------------------------------------------------------
    # IZVOZ
    # --------------------------------------------------------


    st.divider()


    if not factor_df.empty:


        csv = factor_df.to_csv(

            index=False

        ).encode(

            "utf-8"

        )


        st.download_button(

            "⬇️ Prenesi faktorje CSV",

            csv,

            "Psihosocialni_Barometer_faktorji.csv",

            "text/csv"

        )



    if not unit_df.empty:


        csv_units = unit_df.to_csv(

            index=False

        ).encode(

            "utf-8"

        )


        st.download_button(

            "⬇️ Prenesi enote CSV",

            csv_units,

            "Psihosocialni_Barometer_enote.csv",

            "text/csv"

        )



# ============================================================
# KONEC v2.5
# ============================================================





