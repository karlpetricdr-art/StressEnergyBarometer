# ============================================================
# PSIHOSOCIALNI BAROMETER v2.3
# Karl Petrič, 2025/2026
#
# Gemini + Gemma kompatibilna verzija
# google-genai SDK
#
# SPREMEMBE GLEDE NA v2.2:
# - retry logika ob napaki 429 / RESOURCE_EXHAUSTED (exponential backoff)
# - sledenje uspešnim / neuspešnim AI klicem (ne le tiho "prazen rezultat")
# - jasno opozorilo v UI, če je testni način vklopljen
# - prikaz dejanskega števila obdelanih odgovorov (ne le naloženih)
# - ocena preostalega časa med analizo
# - manjši, a še vedno varen premor med klici
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
    page_title="Psihosocialni Barometer v2.3",
    layout="wide"
)


st.title(
    "📊 Psihosocialni Barometer v2.3"
)


st.markdown(
"""
### Model Petrič (2025/2026)

AI večfaktorska analiza psihosocialnih dejavnikov.

Aplikacija omogoča:

✅ več stresorjev iz enega odgovora  
✅ pozitivne zaščitne dejavnike  
✅ predloge izboljšav  
✅ JSON ekstrakcijo  
✅ agregacijo respondentov  
✅ energijski model stresa v kcal in kJ  
✅ retry ob napaki + sledenje uspešnosti analize (novo v v2.3)
"""
)



# ============================================================
# 2. SIDEBAR
# ============================================================


with st.sidebar:


    st.header(
        "⚙️ Nastavitve AI"
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

        "Priporočilo: gemma-4-26b-a4b-it za testiranje"

    )


    st.divider()


    # POMEMBNO: privzeto NASTAVLJENO NA False, da uporabnik
    # po nesreči ne analizira le 3 odgovorov namesto vseh 200.
    test_mode = st.checkbox(

        "Testni način (analizira samo prve 3 odgovore)",

        value=False

    )


    if test_mode:

        st.warning(
            "⚠️ Testni način je VKLOPLJEN. "
            "Analizirani bodo samo prvi 3 odgovori, ne celoten nabor."
        )


    st.divider()


    st.subheader("Robustnost klicev")


    max_retries = st.slider(

        "Največ ponovitev ob napaki (429):",

        min_value=0,

        max_value=5,

        value=3

    )


    request_delay = st.slider(

        "Premor med klici (sekunde):",

        min_value=0.0,

        max_value=3.0,

        value=0.5,

        step=0.1

    )


    st.divider()


    st.subheader("Energijski model")


    W_I_kcal = st.number_input(

        "Izhodiščna dnevna energijska vrednost (kcal):",

        min_value=500,

        max_value=6000,

        value=2500,

        step=100,

        help="Referenčna dnevna energijska poraba, glede na katero se izračuna izguba zaradi stresa."

    )


    st.divider()


    st.write(
        "Avtor:"
    )


    st.write(
        "Karl Petrič"
    )





# ============================================================
# 3. GOOGLE AI INICIALIZACIJA
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
# 4. TEST AI MODELA
# ============================================================


def test_ai(client, model_name):


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

                "Nepodprt format datoteke."

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
# 7. JSON FUNKCIJE
# ============================================================


def clean_json_response(text):


    if not text:

        return "{}"



    text = text.strip()



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


        st.session_state["dataset"] = df



# ============================================================
# KONEC DELA 1
# ============================================================

# ============================================================
# DEL 2
# AI ANALIZA + AGREGACIJA FAKTORJEV
# ============================================================



# ============================================================
# 9. PROMPT ZA AI ANALIZO
# ============================================================


def build_analysis_prompt(answer):


    prompt = f"""

Analiziraj odgovor respondenta po modelu:

Psihosocialni Barometer Petrič (2025/2026).


Naloga:

Iz enega odgovora identificiraj več možnih dejavnikov.


Vrni IZKLJUČNO veljaven JSON.


Kategorije:


1. stresorji

Kaj povzroča psihološko ali socialno obremenitev.


2. pozitivni_dejavniki

Kaj zmanjšuje stres ali povečuje odpornost.


3. predlogi

Kaj bi lahko izboljšalo stanje.



Lestvica intenzivnosti:

0 = ni prisotno

1 = zelo nizko

2 = nizko

3 = srednje

4 = visoko

5 = zelo visoko



Struktura:


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
# 10. ANALIZA ENEGA ODGOVORA (z retry logiko)
# ============================================================


def analyze_single_response(
        client,
        model_name,
        answer,
        max_retries=3):
    """
    Vrne (rezultat, status) kjer je status eden od:
    "ok"            - analiza uspešna
    "prazen_json"   - AI je odgovoril, a JSON ni bil veljaven / uporaben
    "napaka_kvote"  - po vseh ponovitvah še vedno 429 / RESOURCE_EXHAUSTED
    "napaka"        - druga napaka po vseh ponovitvah
    """


    default = empty_analysis()


    attempt = 0

    wait_time = 2  # sekunde, se podvoji ob vsakem retry-u


    while attempt <= max_retries:


        try:


            response = client.models.generate_content(

                model=model_name,

                contents=build_analysis_prompt(

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

            # AI ni vrnil veljavnega JSON - ponovitev ne bo verjetno pomagala,
            # a poskusimo enkrat vseeno, ker so LLM odgovori nedeterministični
            attempt += 1

            if attempt > max_retries:

                return default, "prazen_json"

            time.sleep(wait_time)

            wait_time *= 2



        except Exception as e:


            error_text = str(e)


            is_quota_error = (

                "429" in error_text

                or "RESOURCE_EXHAUSTED" in error_text

            )


            attempt += 1


            if attempt > max_retries:

                if is_quota_error:

                    return default, "napaka_kvote"

                else:

                    return default, "napaka"


            # počakaj dlje ob napaki kvote kot ob drugih napakah
            time.sleep(

                wait_time * (2 if is_quota_error else 1)

            )

            wait_time *= 2


    return default, "napaka"





# ============================================================
# 11. ANALIZA CELOTNEGA DATASETA (s sledenjem uspešnosti)
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

        "ok": 0,

        "prazen_json": 0,

        "napaka_kvote": 0,

        "napaka": 0

    }


    progress = st.progress(0)

    status_text = st.empty()



    if test_mode:


        df = df.head(3)



    total = len(df)


    start_time = time.time()



    for i, row in df.iterrows():



        answer = row["Odgovor"]



        result, status = analyze_single_response(

            client,

            model_name,

            answer,

            max_retries=max_retries

        )



        results.append(

            result

        )


        status_counts[status] += 1



        done = i + 1


        elapsed = time.time() - start_time

        avg_per_item = elapsed / done

        remaining = (total - done) * avg_per_item


        progress.progress(

            int(

                (done / total) * 100

            )

        )


        status_text.text(

            f"Obdelano {done}/{total} "
            f"(✅ {status_counts['ok']}  ⚠️ {status_counts['prazen_json']}  "
            f"🚫 {status_counts['napaka_kvote']}  ❌ {status_counts['napaka']})  "
            f"— ocena preostalega časa: {remaining:.0f}s"

        )



        if request_delay > 0:

            time.sleep(request_delay)



    status_text.empty()

    progress.empty()


    return results, status_counts, total





# ============================================================
# 12. VARNA KONVERZIJA
# ============================================================


def safe_number(value):


    try:

        return int(value)


    except:


        return 0





# ============================================================
# 13. AGREGACIJA FAKTORJEV
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



            data["SF_count"] += 1

            data["SF_weight"] += value



            data["SF_list"].append(

                (

                    name,

                    value

                )

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



            data["PF_count"] += 1

            data["PF_weight"] += value



            data["PF_list"].append(

                (

                    name,

                    value

                )

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



            data["PR_count"] += 1

            data["PR_weight"] += value



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


    merged = {}



    for name, value in items:


        if name not in merged:


            merged[name] = 0



        merged[name] += value



    return list(

        merged.items()

    )





# ============================================================
# 15. DATAFRAME REZULTATOV
# ============================================================


def factors_to_dataframe(aggregated):


    rows = []



    categories = [


        ("Stresorji", "SF_list"),


        ("Pozitivni", "PF_list"),


        ("Predlogi", "PR_list")


    ]



    for category, key in categories:


        for name, value in merge_factors(

            aggregated[key]

        ):


            rows.append(

                {


                    "Kategorija": category,


                    "Faktor": name,


                    "Moč": value


                }

            )



    return pd.DataFrame(rows)



# ============================================================
# KONEC DELA 2
# ============================================================

# ============================================================
# DEL 3
# MATEMATIČNI MODEL + GLAVNI PROGRAM + REZULTATI
# ============================================================



# ============================================================
# 16. MODEL STRESNE MOČI (Petrič, 2025 - Enačbe 12, 18, 24, 27)
# ============================================================

def calculate_stress_power(data, No):
    # No = število respondentov
    
    def get_Fo(fv, frv):
        if fv == 0 or No == 0: return 0.05 # Osnovna vrednost, če ni podatkov
        rho = fv / No                         # Enačba 12
        Co = fv / frv if frv > 0 else 1       # Enačba 18
        return (Co * rho) / 10                # Enačba 24 (rhot=10, Ct=1)

    # Pridobivanje frekvenc (fv) in unikatnih mnenj (frv) iz agregiranih podatkov
    # SF_list vsebuje npr. [("hrup", 3), ("konflikt", 4)] -> fv je število vseh, frv število unikatnih
    f_sf = data.get("SF_count", 0)
    frv_sf = len(set([x[0] for x in data.get("SF_list", [])]))
    
    f_pf = data.get("PF_count", 0)
    frv_pf = len(set([x[0] for x in data.get("PF_list", [])]))
    
    f_pr = data.get("PR_count", 0)
    frv_pr = len(set([x[0] for x in data.get("PR_list", [])]))

    # Izračun realnih faktorjev Fo
    Fo_SF = get_Fo(f_sf, frv_sf)
    Fo_PF = get_Fo(f_pf, frv_pf)
    Fo_PR = get_Fo(f_pr, frv_pr)

    # Varovalka po članku: Fo_PF ne sme biti 0 (Enačba 27)
    if Fo_PF <= 0: Fo_PF = 0.32
    if Fo_PR <= 0: Fo_PR = 0.25

    # Enačba 27: sigma = arcsin(sqrt((Fo_SF * Fo_PR) / Fo_PF))
    try:
        val = (Fo_SF * Fo_PR) / Fo_PF
        sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    except:
        sigma = 0
        
    return sigma, Fo_SF, Fo_PF, Fo_PR

# ============================================================
# 17. ENERGETSKI MODEL (Petrič, 2025 - Enačba 38)
# ============================================================

def calculate_energy(sigma, W_I_kcal=2500):
    # Enačba 38: W_EU = W_I - (W_I * sigma / 90)
    # Pozor: V vašem modelu je maksimalna moč 90 stopinj
    loss_kcal = (W_I_kcal * sigma) / 90
    useful_kcal = W_I_kcal - loss_kcal
    efficiency = (useful_kcal / W_I_kcal) * 100

    KCAL_TO_KJ = 4.184
    return {
        "W_I_kcal": W_I_kcal,
        "loss_kcal": loss_kcal,
        "useful_kcal": useful_kcal,
        "efficiency": efficiency,
        "loss_kJ": loss_kcal * KCAL_TO_KJ,
        "useful_kJ": useful_kcal * KCAL_TO_KJ
    }
# ============================================================
# 18. TOP FAKTORJI
# ============================================================


def top_factors(df, category):


    if df.empty:


        return pd.DataFrame()



    result = (

        df[

            df["Kategorija"] == category

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


    st.caption(

        f"Naloženih odgovorov skupaj: {len(df)}. "
        + (
            "⚠️ Testni način je vklopljen - obdelanih bo le prvih 3."
            if test_mode
            else "Analizirani bodo vsi zgornji odgovori."
        )

    )



    if st.button(

        "🚀 ZAŽENI AI ANALIZO"

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


                st.info(

                    f"Uporabljen model: {model_name}"

                )



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



                    # --- POSODOBLJEN DEL ZA REALNI IZRAČUN ---
                    aggregated = aggregate_factors(results)
                    factor_df = factors_to_dataframe(aggregated)

                    # Novo: Funkciji podamo število vseh respondentov 'len(df)'
                    # Funkcija zdaj vrne 4 vrednosti namesto ene
                    sigma, fsf, fpf, fpr = calculate_stress_power(aggregated, len(df))

                    # Shranjevanje v sejo (session_state), da ostane vidno ob osvežitvi
                    st.session_state["results"] = results
                    st.session_state["aggregated"] = aggregated
                    st.session_state["factor_df"] = factor_df
                    st.session_state["sigma"] = sigma
                    st.session_state["f_factors"] = (fsf, fpf, fpr) # Shranimo realne faktorje Fo
                    st.session_state["status_counts"] = status_counts
                    st.session_state["total_processed"] = total
                    # --- KONEC POSODOBLJENEGA DELA ---



                # Jasno povzetje uspešnosti - ne le "uspešno zaključeno"
                ok = status_counts["ok"]

                problematic = total - ok


                if problematic == 0:


                    st.success(

                        f"AI analiza uspešno zaključena. "
                        f"Vseh {total} odgovorov je bilo uspešno analiziranih."

                    )


                else:


                    st.warning(

                        f"AI analiza zaključena: {ok}/{total} odgovorov uspešno analiziranih. "
                        f"{problematic} odgovorov ni bilo mogoče v celoti obdelati "
                        f"(prazen/neveljaven JSON: {status_counts['prazen_json']}, "
                        f"presežena kvota: {status_counts['napaka_kvote']}, "
                        f"druge napake: {status_counts['napaka']}). "
                        f"To lahko vpliva na spodnje agregirane rezultate - razmisli o "
                        f"povečanju 'Premor med klici' ali ponovnem zagonu."

                    )





# ============================================================
# 20. PRIKAZ REZULTATOV (Popravljeno v2.4)
# ============================================================

if "sigma" in st.session_state:
    aggregated = st.session_state["aggregated"]
    factor_df = st.session_state["factor_df"]
    sigma = st.session_state["sigma"]
    status_counts = st.session_state.get("status_counts")
    total_processed = st.session_state.get("total_processed")

    # Izračun energije po novem modelu
    energy = calculate_energy(sigma, W_I_kcal=W_I_kcal)

    st.divider()
    st.header("📊 Rezultati Psihosocialnega Barometra")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Stresna moč (nagib)", f"{sigma:.2f} °S")

    with col2:
        st.metric("Izguba energije", f"{energy['loss_kcal']:.0f} kcal")
        st.caption(f"= {energy['loss_kJ']:.0f} kJ")

    with col3:
        st.metric("Uporabna energija", f"{energy['useful_kcal']:.0f} kcal")
        st.caption(f"= {energy['useful_kJ']:.0f} kJ")

    with col4:
        st.metric("Učinkovitost (η)", f"{energy['efficiency']:.1f}%")

    # --- TUKAJ VSTAVITE TRETJI KORAK ---
    st.divider()
    st.subheader("Vrednosti realnih faktorjev ($F_o$)")
    st.info("Te vrednosti predstavljajo realni vpliv posamezne skupine dejavnikov na celotno stresno moč po modelu Petrič (2025).")
    
    fs, fp, fpr = st.session_state.get("f_factors", (0,0,0))
    cf1, cf2, cf3 = st.columns(3)
    cf1.write(f"**$F_{{oSF}}$ (Stresorji):** {fs:.4f}")
    cf2.write(f"**$F_{{oPF}}$ (Pozitivni):** {fp:.4f}")
    cf3.write(f"**$F_{{oPR}}$ (Predlogi):** {fpr:.4f}")
    # --- KONEC TRETJEGA KORAKA ---

    st.divider()
    # ... naprej ostane koda za Pie chart in grafe ista ...



    c1, c2 = st.columns(2)



    with c1:


        pie_df = pd.DataFrame(

            {


                "Tip": [

                    "Stresorji",

                    "Pozitivni",

                    "Predlogi"

                ],


                "Vrednost": [

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





# ============================================================
# 21. IZVOZ CSV
# ============================================================


    csv = factor_df.to_csv(

        index=False

    ).encode(

        "utf-8"

    )



    st.download_button(

        label="⬇️ Prenesi CSV rezultat",

        data=csv,

        file_name="Psihosocialni_Barometer_rezultat.csv",

        mime="text/csv"

    )





# ============================================================
# KONEC APLIKACIJE
# ============================================================





