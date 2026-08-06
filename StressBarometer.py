# ============================================================
# DEL 1/6
# PSIHOSOCIALNI BAROMETER v2.4
# OSNOVNA STRUKTURA + KONFIGURACIJA + KLASIFIKACIJSKE ENOTE
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
# 0. KLASIFIKACIJSKE ENOTE
# Petrič (2025/2026)
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
    "fizično okolje, čuti, hrup, svetloba, temperatura, ergonomija",


    "ST":
    "delovne naloge, informacije, postopki, obremenitve, čas",


    "IP":
    "notranje psihično stanje, občutki, motivacija, samozavest",


    "PS":
    "družbena pričakovanja, nagrajevanje, status, priznanje",


    "SO":
    "medosebni odnosi, konflikti, podpora, sodelovanje",


    "HB":
    "zdravje, bolezni, prehrana, telesno stanje"

}



def build_unit_legend():


    text = []


    for code in UNIT_CODES:


        text.append(

            f"{code}: "
            f"{UNIT_LABELS[code]} - "
            f"{UNIT_DESCRIPTIONS[code]}"

        )


    return "\n".join(text)



# ============================================================
# 1. STREAMLIT NASTAVITVE
# ============================================================


st.set_page_config(

    page_title=
    "Psihosocialni Barometer v2.4",

    layout=
    "wide"

)



st.title(

    "📊 Psihosocialni Barometer v2.4"

)



st.markdown(

"""

### Model Petrič (2025/2026)


AI večfaktorska analiza psihosocialnih dejavnikov.


Funkcije:


✅ analiza več stresorjev

✅ pozitivni dejavniki

✅ predlogi izboljšav

✅ AI klasifikacija v 6 enot

✅ JSON ekstrakcija

✅ izračun stresne moči °S

✅ energijski model kcal/kJ

✅ analiza po kategorijah

✅ AI pomoč pri spornih primerih


"""

)



# ============================================================
# 2. SIDEBAR
# ============================================================


with st.sidebar:



    st.header(

        "⚙️ AI Nastavitve"

    )



    api_key = st.text_input(

        "Google API ključ:",

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

        "Priporočilo: gemini-2.0-flash"

    )



    st.divider()



    test_mode = st.checkbox(

        "Testni način (3 odgovori)",

        value=False

    )



    st.divider()



    max_retries = st.slider(

        "Ponovitve ob napaki:",

        0,

        5,

        3

    )



    request_delay = st.slider(

        "Premor med AI klici (s):",

        0.0,

        3.0,

        0.5

    )



    st.divider()



    W_I_kcal = st.number_input(

        "Izhodiščna energija (kcal):",

        500,

        6000,

        2500,

        step=100

    )



    st.divider()



    if st.button(

        "🗑️ RESET",

        use_container_width=True

    ):



        reset_keys = [

            "dataset",

            "results",

            "aggregated",

            "units_data",

            "factor_df",

            "sigma",

            "unit_results",

            "manual_help_result"

        ]



        for key in reset_keys:


            if key in st.session_state:


                del st.session_state[key]



        st.success(

            "Podatki počiščeni."

        )


        st.rerun()



# ============================================================
# 3. AI INICIALIZACIJA
# ============================================================


def initialize_ai(api_key):


    if not api_key:


        return None



    try:


        return genai.Client(

            api_key=api_key

        )



    except Exception as e:


        st.error(

            f"AI inicializacija neuspešna: {e}"

        )


        return None



# ============================================================
# 4. TEST MODELA
# ============================================================


def test_ai(

        client,

        model_name):


    try:


        response = client.models.generate_content(

            model=model_name,

            contents="Pozdravi uporabnika."

        )


        return response.text



    except Exception as e:


        return str(e)



# ============================================================
# 5. NALAGANJE DATASET-a
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



        elif filename.endswith(".txt"):


            df = pd.read_csv(

                uploaded_file,

                sep="\t"

            )



        else:


            st.error(

                "Nepodprt format."

            )


            return None



        return df



    except Exception as e:


        st.error(

            f"Napaka pri uvozu: {e}"

        )


        return None



# ============================================================
# 6. PRIPRAVA PODATKOV
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

        df["Odgovor"].str.len() > 5

    ]



    df.reset_index(

        drop=True,

        inplace=True

    )



    return df



# ============================================================
# 7. JSON ČIŠČENJE
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



# ============================================================
# 8. PRAZEN REZULTAT
# ============================================================


def empty_analysis():


    return {


        "stresorji":[],

        "pozitivni_dejavniki":[],

        "predlogi":[]


    }



# ============================================================
# KONEC DELA 1/6
# ============================================================
		
		# ============================================================
# DEL 2/6
# AI ANALIZA + JSON OBDELAVA + AGREGACIJA FAKTORJEV
# ============================================================


# ============================================================
# 9. JSON FUNKCIJE
# ============================================================


def clean_json_response(text):

    """
    Očisti AI odgovor in izlušči samo JSON objekt.
    """

    if not text:

        return "{}"


    text = str(text).strip()


    # odstrani markdown oznake

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )


    text = text.replace(
        "```",
        ""
    )


    # poišče prvi in zadnji JSON blok

    start = text.find("{")

    end = text.rfind("}")


    if start >= 0 and end >= 0:

        text = text[start:end + 1]


    return text.strip()



def empty_analysis():

    return {

        "stresorji": [],

        "pozitivni_dejavniki": [],

        "predlogi": []

    }



def safe_unit(value):

    """
    Standardizacija AI klasifikacijske enote.
    """

    if isinstance(value, str):

        value = value.strip().upper()


        if value in UNIT_CODES:

            return value



    return "NEZ"



def safe_number(value):

    try:

        return int(value)

    except:

        return 0



# ============================================================
# 10. AI PROMPT
# ============================================================


def build_unit_legend():

    lines = []


    for code in UNIT_CODES:

        lines.append(

            f"{code}: {UNIT_LABELS[code]} - "
            f"{UNIT_DESCRIPTIONS[code]}"

        )


    return "\n".join(lines)



def build_analysis_prompt(answer):


    legend = build_unit_legend()


    return f"""

Analiziraj odgovor respondenta po modelu:

Psihosocialni Barometer Petrič (2025/2026).


Iz odgovora identificiraj:


1. stresorje

2. pozitivne dejavnike

3. predloge izboljšav


Vsak faktor mora imeti:

- faktor
- enota
- intenzivnost 0-5

Za predloge uporabi:

- ucinek 0-5


Uporabi samo naslednje kode enot:


{legend}


Če faktorja ni mogoče razvrstiti:

NEZ


Vrni IZKLJUČNO JSON.


FORMAT:


{{
"stresorji":[
 {{
 "faktor":"",
 "enota":"",
 "intenzivnost":0
 }}
],


"pozitivni_dejavniki":[
 {{
 "faktor":"",
 "enota":"",
 "intenzivnost":0
 }}
],


"predlogi":[
 {{
 "faktor":"",
 "enota":"",
 "ucinek":0
 }}
]

}}


Odgovor respondenta:


{answer}

"""



# ============================================================
# 11. ANALIZA ENEGA ODGOVORA
# ============================================================


def analyze_single_response(
        client,
        model_name,
        answer,
        max_retries=3):


    default = empty_analysis()


    attempt = 0

    wait_time = 2



    while attempt <= max_retries:


        try:


            response = client.models.generate_content(

                model=model_name,

                contents=
                build_analysis_prompt(answer)

            )



            raw = getattr(
                response,
                "text",
                ""
            )



            cleaned = clean_json_response(
                raw
            )


            data = json.loads(
                cleaned
            )


            if not isinstance(
                data,
                dict
            ):

                return default, "prazen_json"



            data.setdefault(
                "stresorji",
                []
            )

            data.setdefault(
                "pozitivni_dejavniki",
                []
            )

            data.setdefault(
                "predlogi",
                []
            )



            return data, "ok"



        except json.JSONDecodeError:



            attempt += 1


            if attempt > max_retries:

                return default, "prazen_json"



            time.sleep(
                wait_time
            )


            wait_time *= 2



        except Exception as e:


            error = str(e)


            quota_error = (

                "429" in error

                or

                "RESOURCE_EXHAUSTED"
                in error

            )


            attempt += 1



            if attempt > max_retries:


                if quota_error:

                    return default, "napaka_kvote"


                return default, "napaka"



            if quota_error:

                time.sleep(
                    wait_time * 2
                )

            else:

                time.sleep(
                    wait_time
                )



            wait_time *= 2



    return default, "napaka"



# ============================================================
# 12. ANALIZA CELOTNEGA DATASETA
# ============================================================


def run_multifactor_analysis(
        df,
        client,
        model_name,
        test_mode=False,
        max_retries=3,
        request_delay=0.5):



    results = []


    status_counts = {

        "ok":0,

        "prazen_json":0,

        "napaka_kvote":0,

        "napaka":0

    }



    if test_mode:

        df = df.head(3)



    total = len(df)



    progress = st.progress(0)

    status = st.empty()



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


        status_counts[state] += 1



        done = len(results)



        elapsed = time.time() - start


        avg = elapsed / done


        remaining = (
            total - done
        ) * avg



        progress.progress(

            int(
                done / total * 100
            )

        )



        status.text(

            f"Obdelano {done}/{total} | "

            f"OK:{status_counts['ok']} | "

            f"JSON:{status_counts['prazen_json']} | "

            f"429:{status_counts['napaka_kvote']} | "

            f"Napake:{status_counts['napaka']} | "

            f"Preostanek ~{remaining:.0f}s"

        )



        if request_delay:

            time.sleep(
                request_delay
            )



    progress.empty()

    status.empty()



    return (
        results,
        status_counts,
        total
    )



# ============================================================
# 13. PRAZEN BUCKET
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
# 14. AGREGACIJA FAKTORJEV
# ============================================================


def aggregate_factors(results):


    aggregated = empty_bucket()



    units_data = {

        code:
        empty_bucket()

        for code in UNIT_CODES

    }


    units_data["NEZ"] = empty_bucket()



    for item in results:



        for sf in item.get(
            "stresorji",
            []
        ):


            name = sf.get(
                "faktor",
                "neznan"
            )


            value = safe_number(

                sf.get(
                    "intenzivnost",
                    0
                )

            )


            unit = safe_unit(

                sf.get(
                    "enota",
                    ""
                )

            )



            aggregated["SF_count"] += 1

            aggregated["SF_weight"] += value

            aggregated["SF_list"].append(
                (name,value)
            )



            units_data[unit]["SF_count"] += 1

            units_data[unit]["SF_weight"] += value

            units_data[unit]["SF_list"].append(
                (name,value)
            )



        for pf in item.get(
            "pozitivni_dejavniki",
            []
        ):


            name = pf.get(
                "faktor",
                "neznan"
            )


            value = safe_number(

                pf.get(
                    "intenzivnost",
                    0
                )

            )


            unit = safe_unit(

                pf.get(
                    "enota",
                    ""
                )

            )


            aggregated["PF_count"] += 1

            aggregated["PF_weight"] += value

            aggregated["PF_list"].append(
                (name,value)
            )



            units_data[unit]["PF_count"] += 1

            units_data[unit]["PF_weight"] += value

            units_data[unit]["PF_list"].append(
                (name,value)
            )



        for pr in item.get(
            "predlogi",
            []
        ):


            name = pr.get(
                "faktor",
                "neznan"
            )


            value = safe_number(

                pr.get(
                    "ucinek",
                    0
                )

            )


            unit = safe_unit(

                pr.get(
                    "enota",
                    ""
                )

            )



            aggregated["PR_count"] += 1

            aggregated["PR_weight"] += value

            aggregated["PR_list"].append(
                (name,value)
            )



            units_data[unit]["PR_count"] += 1

            units_data[unit]["PR_weight"] += value

            units_data[unit]["PR_list"].append(
                (name,value)
            )



    return (
        aggregated,
        units_data
    )



# ============================================================
# KONEC DELA 2/6
# ============================================================

# ============================================================
# DEL 3/6
# PREDELAVA FAKTORJEV + DATAFRAME + POMOŽNE FUNKCIJE
# ============================================================


# ============================================================
# 15. ZDRUŽEVANJE ENAKIH FAKTORJEV
# ============================================================


def merge_factors(items):


    merged = {}



    for name, value in items:


        if not name:

            name = "neznan"



        if name not in merged:

            merged[name] = 0



        merged[name] += value



    return list(
        merged.items()
    )



# ============================================================
# 16. DATAFRAME VSEH FAKTORJEV
# ============================================================


def factors_to_dataframe(units_data):


    rows = []



    categories = [

        (
            "Stresorji",
            "SF_list"
        ),

        (
            "Pozitivni dejavniki",
            "PF_list"
        ),

        (
            "Predlogi",
            "PR_list"
        )

    ]



    for unit_code, bucket in units_data.items():



        label = UNIT_LABELS.get(

            unit_code,

            "Nerazvrščeno"

        )



        for category, key in categories:



            merged = merge_factors(

                bucket.get(
                    key,
                    []
                )

            )



            for factor, strength in merged:



                rows.append(

                    {

                        "Enota":
                        label,

                        "EnotaKoda":
                        unit_code,

                        "Kategorija":
                        category,

                        "Faktor":
                        factor,

                        "Moč":
                        strength

                    }

                )



    if not rows:

        return pd.DataFrame(

            columns=[

                "Enota",

                "EnotaKoda",

                "Kategorija",

                "Faktor",

                "Moč"

            ]

        )



    return pd.DataFrame(rows)



# ============================================================
# 17. TOP FAKTORJI
# ============================================================


def top_factors(
        df,
        category,
        unit_code="VSE"):


    if df is None or df.empty:

        return pd.DataFrame()



    result = df[

        df["Kategorija"] == category

    ]



    if unit_code != "VSE":


        result = result[

            result["EnotaKoda"] == unit_code

        ]



    if result.empty:

        return pd.DataFrame()



    result = (

        result

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
# 18. MATEMATIČNI MODEL STRESNE MOČI
# Petrič (2025)
# ============================================================


def calculate_stress_power(
        data,
        No,
        pf_default=0.05,
        pr_default=0.05):


    """
    Izračun realnih faktorjev Fo in stresne moči.

    Vrne:

    sigma
    FoSF
    FoPF
    FoPR

    """



    def calculate_Fo(
            fv,
            frv):



        if No <= 0:

            return 0



        if fv <= 0:

            return 0



        if frv <= 0:

            frv = 1



        rho = fv / No



        Co = fv / frv



        Fo = (

            Co * rho

        ) / 10



        return Fo



    # frekvence

    f_sf = data.get(

        "SF_count",
        0

    )


    f_pf = data.get(

        "PF_count",
        0

    )


    f_pr = data.get(

        "PR_count",
        0

    )



    frv_sf = len(

        set(

            x[0]

            for x in data.get(
                "SF_list",
                []
            )

        )

    )



    frv_pf = len(

        set(

            x[0]

            for x in data.get(
                "PF_list",
                []
            )

        )

    )



    frv_pr = len(

        set(

            x[0]

            for x in data.get(
                "PR_list",
                []
            )

        )

    )



    FoSF = calculate_Fo(

        f_sf,

        frv_sf

    )


    FoPF = calculate_Fo(

        f_pf,

        frv_pf

    )


    FoPR = calculate_Fo(

        f_pr,

        frv_pr

    )



    if FoPF <= 0:

        FoPF = pf_default



    if FoPR <= 0:

        FoPR = pr_default



    try:


        argument = (

            FoSF * FoPR

        ) / FoPF



        argument = max(

            0,

            min(

                1,

                argument

            )

        )



        sigma = math.degrees(

            math.asin(

                math.sqrt(
                    argument
                )

            )

        )



    except Exception:


        sigma = 0



    return (

        sigma,

        FoSF,

        FoPF,

        FoPR

    )



# ============================================================
# 19. IZRAČUN PO POSAMEZNIH ENOTAH
# ============================================================


def calculate_all_unit_stress_power(
        units_data,
        No):


    results = {}



    all_units = UNIT_CODES.copy()



    if "NEZ" in units_data:

        all_units.append(
            "NEZ"
        )



    for code in all_units:


        bucket = units_data.get(

            code,

            empty_bucket()

        )



        sigma, fsf, fpf, fpr = calculate_stress_power(

            bucket,

            No

        )



        results[code] = {


            "sigma":
            sigma,


            "FoSF":
            fsf,


            "FoPF":
            fpf,


            "FoPR":
            fpr,


            "SF_count":
            bucket["SF_count"],


            "PF_count":
            bucket["PF_count"],


            "PR_count":
            bucket["PR_count"]

        }



    return results



# ============================================================
# 20. ENERGIJSKI MODEL
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

        if W_I_kcal

        else 0

    )



    return {


        "input":

        W_I_kcal,


        "loss_kcal":

        loss,


        "useful_kcal":

        useful,


        "efficiency":

        efficiency,


        "loss_kJ":

        loss * 4.184,


        "useful_kJ":

        useful * 4.184

    }



# ============================================================
# 21. LESTVICA STRESA
# ============================================================


def stress_level_label(
        sigma):


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
# KONEC DELA 3/6
# ============================================================

# ============================================================
# DEL 4/6
# GLAVNI PROGRAM + AI ANALIZA + SHRANJEVANJE REZULTATOV
# ============================================================


# ============================================================
# 22. GLAVNI PROGRAM - ZAGON AI ANALIZE
# ============================================================


if st.session_state.get("dataset") is not None:


    df = st.session_state["dataset"]


    st.divider()


    st.header(
        "🧠 AI analiza respondentov"
    )



    st.info(

        f"Pripravljenih odgovorov: {len(df)}"

    )



    if test_mode:


        st.warning(

            "Testni način: analizirani bodo samo prvi 3 odgovori."

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

                    f"{model_name} analizira odgovore..."

                ):



                    results, status_counts, total = run_multifactor_analysis(

                        df,

                        client,

                        model_name,

                        test_mode=test_mode,

                        max_retries=max_retries,

                        request_delay=request_delay

                    )



                    # agregacija

                    aggregated, units_data = aggregate_factors(

                        results

                    )



                    factor_df = factors_to_dataframe(

                        units_data

                    )



                    # stresna moč

                    sigma, FoSF, FoPF, FoPR = calculate_stress_power(

                        aggregated,

                        len(df)

                    )



                    # po enotah

                    unit_results = calculate_all_unit_stress_power(

                        units_data,

                        len(df)

                    )



                    # shranjevanje

                    st.session_state["results"] = results

                    st.session_state["aggregated"] = aggregated

                    st.session_state["units_data"] = units_data

                    st.session_state["factor_df"] = factor_df

                    st.session_state["sigma"] = sigma

                    st.session_state["f_factors"] = (

                        FoSF,

                        FoPF,

                        FoPR

                    )

                    st.session_state["unit_results"] = unit_results

                    st.session_state["status_counts"] = status_counts

                    st.session_state["total_processed"] = total





                ok = status_counts["ok"]



                if ok == total:



                    st.success(

                        f"AI analiza uspešna: {ok}/{total}"

                    )


                else:


                    st.warning(

                        f"Uspešno analizirano {ok}/{total}. "

                        f"JSON napake: "

                        f"{status_counts['prazen_json']}, "

                        f"Kvota: "

                        f"{status_counts['napaka_kvote']}, "

                        f"Druge napake: "

                        f"{status_counts['napaka']}"

                    )



# ============================================================
# 23. PRIKAZ REZULTATOV
# ============================================================


if st.session_state.get("sigma") is not None:



    sigma = st.session_state["sigma"]

    aggregated = st.session_state["aggregated"]

    factor_df = st.session_state["factor_df"]

    unit_results = st.session_state["unit_results"]



    energy = calculate_energy(

        sigma,

        W_I_kcal

    )



    st.divider()


    st.header(

        "📊 Rezultati"

    )



    # --------------------------------------------------------
    # Glavni rezultat
    # --------------------------------------------------------


    col1, col2, col3, col4 = st.columns(4)



    with col1:


        st.metric(

            "Stresna moč",

            f"{sigma:.2f} °S"

        )


        st.caption(

            stress_level_label(sigma)

        )



    with col2:


        st.metric(

            "Izguba energije",

            f"{energy['loss_kcal']:.0f} kcal"

        )



    with col3:


        st.metric(

            "Uporabna energija",

            f"{energy['useful_kcal']:.0f} kcal"

        )



    with col4:


        st.metric(

            "Učinkovitost",

            f"{energy['efficiency']:.1f}%"

        )



    st.divider()



    st.subheader(

        "Realni faktorji Fo"

    )



    FoSF, FoPF, FoPR = st.session_state["f_factors"]



    c1,c2,c3 = st.columns(3)



    c1.metric(

        "FoSF - stresorji",

        f"{FoSF:.4f}"

    )


    c2.metric(

        "FoPF - pozitivni",

        f"{FoPF:.4f}"

    )


    c3.metric(

        "FoPR - predlogi",

        f"{FoPR:.4f}"

    )



# ============================================================
# 24. ANALIZA PO 6 ENOTAH
# ============================================================


    st.divider()


    st.header(

        "🧩 Analiza po klasifikacijskih enotah"

    )



    unit_rows = []



    for code in UNIT_CODES:



        result = unit_results.get(

            code,

            {}

        )



        u_sigma = result.get(

            "sigma",

            0

        )



        u_energy = calculate_energy(

            u_sigma,

            W_I_kcal

        )



        unit_rows.append(

            {


            "Enota":

            UNIT_LABELS[code],



            "Koda":

            code,



            "σ °S":

            round(u_sigma,2),



            "Ocena":

            stress_level_label(u_sigma),



            "Izguba kcal":

            round(

                u_energy["loss_kcal"],

                0

            ),



            "Učinkovitost %":

            round(

                u_energy["efficiency"],

                1

            ),



            "Stresorji":

            result.get(

                "SF_count",

                0

            ),



            "Pozitivni":

            result.get(

                "PF_count",

                0

            ),



            "Predlogi":

            result.get(

                "PR_count",

                0

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



    st.plotly_chart(

        px.bar(

            unit_df,

            x="Enota",

            y="σ °S",

            title="Stresna moč po enotah"

        ),

        use_container_width=True

    )



# ============================================================
# 25. VIZUALIZACIJA FAKTORJEV
# ============================================================


    st.divider()


    left,right = st.columns(2)



    with left:


        pie = pd.DataFrame(

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

                pie,

                names="Tip",

                values="Vrednost"

            ),

            use_container_width=True

        )



    with right:


        st.subheader(

            "Vsi faktorji"

        )


        st.dataframe(

            factor_df,

            use_container_width=True

        )



# ============================================================
# KONEC DELA 4/6
# ============================================================

# ============================================================
# DEL 5/6
# TOP FAKTORJI + FILTRIRANJE + IZVOZ REZULTATOV
# ============================================================


# ============================================================
# 26. PODROBNA ANALIZA FAKTORJEV
# ============================================================


if st.session_state.get("factor_df") is not None:


    factor_df = st.session_state["factor_df"]



    st.divider()


    st.header(
        "🔎 Podrobna analiza dejavnikov"
    )



    # --------------------------------------------------------
    # Filter enote
    # --------------------------------------------------------


    unit_options = [

        "VSE"

    ] + UNIT_CODES



    unit_labels = {

        "VSE":
        "Vse enote"

    }


    unit_labels.update(
        UNIT_LABELS
    )



    selected_unit = st.selectbox(

        "Izberi klasifikacijsko enoto:",

        options=unit_options,

        format_func=lambda x:
        unit_labels.get(
            x,
            x
        )

    )



    # --------------------------------------------------------
    # Najmočnejši stresorji
    # --------------------------------------------------------


    st.subheader(

        "🔥 Najmočnejši stresorji"

    )



    sf_top = top_factors(

        factor_df,

        "Stresorji",

        selected_unit

    )



    if not sf_top.empty:


        st.plotly_chart(

            px.bar(

                sf_top,

                x="Moč",

                y="Faktor",

                orientation="h",

                title="Top stresorji"

            ),

            use_container_width=True

        )


        st.dataframe(

            sf_top,

            use_container_width=True

        )


    else:


        st.info(

            "Ni zaznanih stresorjev."

        )



    # --------------------------------------------------------
    # Pozitivni dejavniki
    # --------------------------------------------------------


    st.subheader(

        "🛡️ Pozitivni dejavniki"

    )



    pf_top = top_factors(

        factor_df,

        "Pozitivni dejavniki",

        selected_unit

    )



    if not pf_top.empty:


        st.plotly_chart(

            px.bar(

                pf_top,

                x="Moč",

                y="Faktor",

                orientation="h",

                title="Top zaščitni dejavniki"

            ),

            use_container_width=True

        )


        st.dataframe(

            pf_top,

            use_container_width=True

        )


    else:


        st.info(

            "Ni zaznanih pozitivnih dejavnikov."

        )



    # --------------------------------------------------------
    # Predlogi
    # --------------------------------------------------------


    st.subheader(

        "💡 Predlogi izboljšav"

    )



    pr_top = top_factors(

        factor_df,

        "Predlogi",

        selected_unit

    )



    if not pr_top.empty:


        st.dataframe(

            pr_top,

            use_container_width=True

        )


    else:


        st.info(

            "Ni predlogov."

        )



# ============================================================
# 27. STATUS AI ANALIZE
# ============================================================


if st.session_state.get(
        "status_counts"):


    st.divider()


    st.header(

        "📋 Diagnostika AI analize"

    )



    status = st.session_state["status_counts"]



    c1,c2,c3,c4 = st.columns(4)



    c1.metric(

        "Uspešni JSON",

        status.get(
            "ok",
            0
        )

    )


    c2.metric(

        "Neveljaven JSON",

        status.get(
            "prazen_json",
            0
        )

    )


    c3.metric(

        "Quota napake",

        status.get(
            "napaka_kvote",
            0
        )

    )


    c4.metric(

        "Druge napake",

        status.get(
            "napaka",
            0
        )

    )



# ============================================================
# 28. IZVOZ PODATKOV
# ============================================================


if st.session_state.get(
        "factor_df") is not None:


    st.divider()


    st.header(

        "⬇️ Izvoz rezultatov"

    )



    factor_df = st.session_state["factor_df"]



    col1,col2 = st.columns(2)



    with col1:


        csv_factor = (

            factor_df

            .to_csv(

                index=False,

                encoding="utf-8"

            )

            .encode(
                "utf-8"
            )

        )



        st.download_button(

            label=
            "⬇️ Prenesi vse faktorje CSV",

            data=
            csv_factor,

            file_name=
            "Psihosocialni_Barometer_faktorji.csv",

            mime=
            "text/csv"

        )



    with col2:


        if st.session_state.get(
                "unit_results"):



            unit_results = st.session_state["unit_results"]



            export_rows = []



            for code, value in unit_results.items():


                export_rows.append(

                    {

                    "Enota":

                    UNIT_LABELS.get(
                        code,
                        "NEZ"
                    ),


                    "Koda":

                    code,


                    "Sigma":

                    value.get(
                        "sigma",
                        0
                    ),


                    "FoSF":

                    value.get(
                        "FoSF",
                        0
                    ),


                    "FoPF":

                    value.get(
                        "FoPF",
                        0
                    ),


                    "FoPR":

                    value.get(
                        "FoPR",
                        0
                    )

                    }

                )



            unit_export = pd.DataFrame(

                export_rows

            )



            csv_units = (

                unit_export

                .to_csv(

                    index=False

                )

                .encode(
                    "utf-8"
                )

            )



            st.download_button(

                label=
                "⬇️ Prenesi analizo po enotah CSV",

                data=
                csv_units,

                file_name=
                "Psihosocialni_Barometer_enote.csv",

                mime=
                "text/csv"

            )



# ============================================================
# 29. POVZETEK MODELA
# ============================================================


if st.session_state.get("sigma") is not None:


    st.divider()


    st.subheader(

        "📌 Povzetek"

    )



    sigma = st.session_state["sigma"]



    st.write(

        f"""

**Skupna stresna moč:** {sigma:.2f} °S  

**Stopnja:** {stress_level_label(sigma)}  

**Model:** Psihosocialni Barometer Petrič (2025/2026)

Aplikacija je analizirala večdimenzionalne psihosocialne dejavnike
in jih razvrstila v šest klasifikacijskih enot.

"""

    )



# ============================================================
# KONEC DELA 5/6
# ============================================================

# ============================================================
# DEL 6/6
# AI POMOČ PRI KLASIFIKACIJI + RESET + ZAKLJUČEK APLIKACIJE
# ============================================================


# ============================================================
# 30. AI POMOČ PRI TEŽJIH KLASIFIKACIJAH
# ============================================================


st.divider()


st.header(
    "🧭 AI pomoč pri klasifikaciji"
)



st.markdown(
"""
Če avtomatska analiza določenega odgovora ni dovolj jasna,
lahko tukaj uporabite dodatno AI razlago.

AI bo predlagal:

- stresorje
- pozitivne dejavnike
- predloge izboljšav
- klasifikacijsko enoto
- intenzivnost/učinek
- obrazložitev odločitve
"""
)



manual_text = st.text_area(

    "Vnesite problematičen odgovor:",

    height=150,

    placeholder=
    "Primer: Vodstvo me pogosto ignorira, "
    "vendar imam dobre odnose s sodelavci."

)



# ------------------------------------------------------------
# Prompt
# ------------------------------------------------------------


def build_manual_help_prompt(text):


    legend = build_unit_legend()



    return f"""

Si strokovni AI pomočnik za model
Psihosocialni Barometer Petrič (2025/2026).


Analiziraj spodnji odgovor respondenta.


Uporabi klasifikacijske enote:


{legend}


Za vsak dejavnik določi:


- faktor
- enota
- intenzivnost 0-5
- obrazložitev


Vrni IZKLJUČNO JSON:


{{
"stresorji":[],

"pozitivni_dejavniki":[],

"predlogi":[]
}}



Odgovor:


{text}

"""



# ------------------------------------------------------------
# Klic AI za ročni primer
# ------------------------------------------------------------


def classify_manual_case(
        client,
        model_name,
        text):


    try:


        response = client.models.generate_content(

            model=model_name,

            contents=
            build_manual_help_prompt(text)

        )



        cleaned = clean_json_response(

            response.text

        )



        data = json.loads(

            cleaned

        )



        if not isinstance(
                data,
                dict):


            return None



        data.setdefault(

            "stresorji",

            []

        )


        data.setdefault(

            "pozitivni_dejavniki",

            []

        )


        data.setdefault(

            "predlogi",

            []

        )


        return data



    except Exception as e:


        st.error(

            f"Napaka AI klasifikacije: {e}"

        )


        return None



# ------------------------------------------------------------
# Gumb
# ------------------------------------------------------------


if st.button(

    "🔎 Analiziraj primer z AI"

):


    if not api_key:


        st.error(

            "Najprej vnesite API ključ."

        )



    elif len(manual_text.strip()) < 3:


        st.warning(

            "Vnesite besedilo."

        )



    else:


        client = initialize_ai(

            api_key

        )



        if client:


            with st.spinner(

                "AI pripravlja klasifikacijo..."

            ):


                result = classify_manual_case(

                    client,

                    model_name,

                    manual_text

                )



            if result:


                st.session_state[

                    "manual_help_result"

                ] = result



# ------------------------------------------------------------
# Prikaz rezultata
# ------------------------------------------------------------


if st.session_state.get(
        "manual_help_result"):


    st.subheader(

        "📌 Predlagana klasifikacija"

    )



    result = st.session_state[

        "manual_help_result"

    ]



    for title, key in [

        ("🔥 Stresorji","stresorji"),

        ("🛡️ Pozitivni dejavniki",
         "pozitivni_dejavniki"),

        ("💡 Predlogi",
         "predlogi")

    ]:



        st.markdown(

            f"### {title}"

        )



        items = result.get(

            key,

            []

        )



        if not items:


            st.caption(

                "Ni zaznanih faktorjev."

            )


        else:



            for item in items:



                unit = safe_unit(

                    item.get(

                        "enota",

                        ""

                    )

                )



                st.write(

                    f"""

**{item.get('faktor','')}**

- Enota:
{UNIT_LABELS.get(unit,'NEZ')}

- Vrednost:
{item.get('intenzivnost',
item.get('ucinek',''))}

- Razlaga:
{item.get('obrazlozitev','')}

"""

                )



    if st.button(

        "🗑️ Skrij AI predlog"

    ):


        del st.session_state[

            "manual_help_result"

        ]

        st.rerun()



# ============================================================
# 31. KONČNI INFORMACIJSKI PANEL
# ============================================================


st.divider()


with st.expander(

    "ℹ️ O aplikaciji"

):


    st.markdown(

"""
## Psihosocialni Barometer v2.4

Avtor:
**Karl Petrič**

Model omogoča:


✅ AI ekstrakcijo psihosocialnih dejavnikov

✅ večfaktorsko analizo posameznih odgovorov

✅ klasifikacijo v šest hierarhičnih enot

✅ izračun stresne moči (°S)

✅ energijski model izgube/uporabne energije

✅ agregacijo rezultatov respondentov

✅ pomoč AI pri spornih primerih


Model:
Petrič (2025/2026)

"""

    )



# ============================================================
# 32. VARNOSTNI RESET OB NAPAKAH
# ============================================================


def safe_reset():


    keys = list(

        st.session_state.keys()

    )


    for key in keys:


        if key not in [

            "api_key"

        ]:


            del st.session_state[key]



# ============================================================
# KONEC APLIKACIJE
# ============================================================





