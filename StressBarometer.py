# ============================================================
# PSIHOSOCIALNI BAROMETER v2.4
# Karl Petrič, 2025/2026
#
# Gemini + Gemma kompatibilna verzija
# google-genai SDK
#
# SPREMEMBE GLEDE NA v2.3:
# - AI zdaj vsak faktor razvrsti tudi v eno od 6 klasifikacijskih enot
#   (Pozorna/fizična, Storilnostna, Individualna psihološka, Delna socialna,
#   Socialna, Zdravstveno-biološka) po modelu Petrič (2025)
# - izračun stresne moči (°S) in porabe energije (kcal) NI VEČ samo skupen,
#   ampak tudi ločeno po vseh 6 kategorijah (enačbe 6-11 in 28-37 iz članka)
# - dodana ocenjevalna lestvica stresne moči (Tabela 6 iz članka)
# - dodan RESET gumb, ki počisti vse rezultate in naložene podatke
# - dodano "promptno okno" - pomoč AI pri ročni klasifikaciji težjih/spornih
#   odgovorov, z obrazložitvijo predlagane kategorije
# - manjši popravki/čiščenje kode iz v2.3
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
# 0. KLASIFIKACIJSKE ENOTE (Petrič, 2025 - Tabela 1)
# ============================================================

# Kratke kode enot, uporabljene skozi celotno kodo
UNIT_CODES = ["AT", "ST", "IP", "PS", "SO", "HB"]

UNIT_LABELS = {
    "AT": "Pozorna (fizična)",
    "ST": "Storilnostna",
    "IP": "Individualna psihološka",
    "PS": "Delna socialna",
    "SO": "Socialna",
    "HB": "Zdravstveno-biološka",
}

# Kratek opis vsake enote (uporabljeno v AI promptu, da AI lažje pravilno
# razvrsti faktor), povzeto po klasifikaciji v članku (Petrič, 2025)
UNIT_DESCRIPTIONS = {
    "AT": "vpliva na čute in fizično okolje (svetloba, hrup, temperatura, "
          "vonjave, ergonomija pohištva, senzorna monotonija/pestrost)",
    "ST": "povezano z naporom pri opravljanju nalog, iskanjem/dostopnostjo "
          "informacij, delovnimi postopki, obremenitvijo, urniki",
    "IP": "subjektivno notranje psihično stanje posameznika (tesnoba, "
          "napetost, optimizem, mir, samozavest, osebni občutki)",
    "PS": "povezano z družbenimi normami, pričakovanji, kaznovanjem/"
          "nagrajevanjem, dokazovanjem lastne vrednosti, priznanjem, plačilom",
    "SO": "odnosi in interakcije med ljudmi, gneča/prostor, konflikti, "
          "mobing, sodelovanje, podpora, družinski/službeni odnosi",
    "HB": "fizično zdravje, bolezni, higiena, telesna kondicija, prehrana",
}

UNIT_ORDER_FOR_DISPLAY = [(code, UNIT_LABELS[code]) for code in UNIT_CODES]


# ============================================================
# 1. STREAMLIT NASTAVITVE
# ============================================================


st.set_page_config(
    page_title="Psihosocialni Barometer v2.4",
    layout="wide"
)


st.title("📊 Psihosocialni Barometer v2.4")


st.markdown(
"""
### Model Petrič (2025/2026)

AI večfaktorska analiza psihosocialnih dejavnikov.

Aplikacija omogoča:

✅ več stresorjev iz enega odgovora
✅ pozitivne zaščitne dejavnike
✅ predloge izboljšav
✅ razvrstitev vsakega faktorja v eno od 6 klasifikacijskih enot
✅ JSON ekstrakcijo
✅ agregacijo respondentov
✅ izračun stresne moči (°S) in energijskega modela (kcal/kJ) SKUPNO **in** po kategorijah
✅ retry ob napaki + sledenje uspešnosti analize
✅ AI pomoč pri ročni klasifikaciji težjih odgovorov (novo v v2.4)
✅ reset gumb (novo v v2.4)
"""
)


# ============================================================
# 2. SIDEBAR
# ============================================================


with st.sidebar:

    st.header("⚙️ Nastavitve AI")

    api_key = st.text_input("Google API ključ:", type="password")

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

    st.info("Priporočilo: gemma-4-26b-a4b-it za testiranje")

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
        min_value=0, max_value=5, value=3
    )

    request_delay = st.slider(
        "Premor med klici (sekunde):",
        min_value=0.0, max_value=3.0, value=0.5, step=0.1
    )

    st.divider()

    st.subheader("Energijski model")

    W_I_kcal = st.number_input(
        "Izhodiščna dnevna energijska vrednost (kcal):",
        min_value=500, max_value=6000, value=2500, step=100,
        help="Referenčna dnevna energijska poraba, glede na katero se "
             "izračuna izguba zaradi stresa."
    )

    st.divider()

    st.subheader("🔄 Ponastavitev")

    if st.button("🗑️ Počisti vse podatke in rezultate", use_container_width=True):
        keys_to_clear = [
            "dataset", "results", "aggregated", "units_data", "factor_df",
            "sigma", "f_factors", "unit_results", "status_counts",
            "total_processed", "manual_help_result"
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Vsi podatki in rezultati so bili počiščeni.")
        st.rerun()

    st.divider()

    st.write("Avtor:")
    st.write("Karl Petrič")


# ============================================================
# 3. GOOGLE AI INICIALIZACIJA
# ============================================================


def initialize_ai(api_key):

    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        return client

    except Exception as e:
        st.error(f"AI inicializacija neuspešna: {e}")
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
            df = pd.read_excel(uploaded_file)

        elif filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)

        elif filename.endswith(".tsv"):
            df = pd.read_csv(uploaded_file, sep="\t", encoding="utf-8")

        elif filename.endswith(".txt"):
            df = pd.read_csv(uploaded_file, sep="\t", encoding="utf-8")

        else:
            st.error("Nepodprt format datoteke.")
            return None

        return df

    except Exception as e:
        st.error(f"Napaka pri uvozu podatkov: {e}")
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
        df = df.rename(columns={df.columns[0]: "Odgovor"})

    df["Odgovor"] = df["Odgovor"].fillna("").astype(str).str.strip()

    df = df[df["Odgovor"].str.len() > 5]

    df.reset_index(drop=True, inplace=True)

    return df


# ============================================================
# 7. JSON FUNKCIJE
# ============================================================


def clean_json_response(text):

    if not text:
        return "{}"

    text = text.strip()

    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

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
    """Poskrbi, da je enota vedno ena od 6 veljavnih kod, sicer 'NEZ'
    (neznano/nerazvrščeno), da tak faktor ne pokvari izračunov po enotah."""

    if isinstance(value, str):
        v = value.strip().upper()

        if v in UNIT_CODES:
            return v

    return "NEZ"


# ============================================================
# 8. UPLOAD PODATKOV
# ============================================================


uploaded_file = st.file_uploader(
    "📂 Naložite odgovore respondentov",
    type=["xlsx", "csv", "txt"]
)


if uploaded_file:

    df = load_dataset(uploaded_file)
    df = prepare_dataframe(df)

    if df is not None:
        st.success(f"Naloženih odgovorov: {len(df)}")
        st.dataframe(df.head(10), use_container_width=True)
        st.session_state["dataset"] = df


# ============================================================
# KONEC DELA 1
# ============================================================

# ============================================================
# DEL 2
# AI ANALIZA + AGREGACIJA FAKTORJEV (PO ENOTAH)
# ============================================================


# ============================================================
# 9. PROMPT ZA AI ANALIZO
# ============================================================


def build_unit_legend():
    """Sestavi opis 6 klasifikacijskih enot za vključitev v prompt."""

    lines = []
    for code in UNIT_CODES:
        lines.append(f'- "{code}" ({UNIT_LABELS[code]}): {UNIT_DESCRIPTIONS[code]}')

    return "\n".join(lines)


def build_analysis_prompt(answer):

    unit_legend = build_unit_legend()

    prompt = f"""
Analiziraj odgovor respondenta po modelu:
Psihosocialni Barometer Petrič (2025/2026).

Naloga:
Iz enega odgovora identificiraj več možnih dejavnikov.

Vrni IZKLJUČNO veljaven JSON, brez dodatnega besedila.

Kategorije:

1. stresorji
Kaj povzroča psihološko ali socialno obremenitev.

2. pozitivni_dejavniki
Kaj zmanjšuje stres ali povečuje odpornost.

3. predlogi
Kaj bi lahko izboljšalo stanje.

Za VSAK identificiran faktor (v vseh treh kategorijah) moraš poleg imena
faktorja določiti tudi klasifikacijsko ENOTO, v katero faktor najbolje
sodi. Uporabi TOČNO eno od naslednjih kratkih kod:

{unit_legend}

Če faktorja resnično ni mogoče razvrstiti v nobeno od zgornjih enot,
uporabi kodo "NEZ".

Lestvica intenzivnosti (za stresorje in pozitivne dejavnike):
0 = ni prisotno
1 = zelo nizko
2 = nizko
3 = srednje
4 = visoko
5 = zelo visoko

Lestvica učinka (za predloge):
0 = brez učinka
1 = zelo nizek učinek
2 = nizek učinek
3 = srednji učinek
4 = visok učinek
5 = zelo visok učinek

Struktura:

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

    return prompt


# ============================================================
# 10. ANALIZA ENEGA ODGOVORA (z retry logiko)
# ============================================================


def analyze_single_response(client, model_name, answer, max_retries=3):
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
                contents=build_analysis_prompt(answer)
            )

            raw = response.text
            cleaned = clean_json_response(raw)
            data = json.loads(cleaned)

            if not isinstance(data, dict):
                return default, "prazen_json"

            data.setdefault("stresorji", [])
            data.setdefault("pozitivni_dejavniki", [])
            data.setdefault("predlogi", [])

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
                "429" in error_text or "RESOURCE_EXHAUSTED" in error_text
            )

            attempt += 1

            if attempt > max_retries:
                if is_quota_error:
                    return default, "napaka_kvote"
                else:
                    return default, "napaka"

            # počakaj dlje ob napaki kvote kot ob drugih napakah
            time.sleep(wait_time * (2 if is_quota_error else 1))
            wait_time *= 2

    return default, "napaka"


# ============================================================
# 11. ANALIZA CELOTNEGA DATASETA (s sledenjem uspešnosti)
# ============================================================


def run_multifactor_analysis(
        df, client, model_name,
        test_mode=False, max_retries=3, request_delay=0.5):

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
            client, model_name, answer, max_retries=max_retries
        )

        results.append(result)
        status_counts[status] += 1

        done = i + 1
        elapsed = time.time() - start_time
        avg_per_item = elapsed / done
        remaining = (total - done) * avg_per_item

        progress.progress(int((done / total) * 100))

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
    except Exception:
        return 0


# ============================================================
# 13. AGREGACIJA FAKTORJEV (SKUPAJ + PO ENOTAH)
# ============================================================


def _empty_bucket():
    return {
        "SF_count": 0, "PF_count": 0, "PR_count": 0,
        "SF_weight": 0, "PF_weight": 0, "PR_weight": 0,
        "SF_list": [], "PF_list": [], "PR_list": []
    }


def aggregate_factors(results):
    """Vrne (aggregated, units_data):
    - aggregated: skupna (celotna) agregacija čez vse enote (kot v v2.3)
    - units_data: slovar {koda_enote: bucket}, enaka struktura kot
      aggregated, a samo za posamezno klasifikacijsko enoto
    """

    aggregated = _empty_bucket()

    units_data = {code: _empty_bucket() for code in UNIT_CODES}
    # "NEZ" hrani faktorje, ki jih AI ni znal/uspel razvrstiti v 6 enot
    units_data["NEZ"] = _empty_bucket()

    for item in results:

        for sf in item.get("stresorji", []):
            name = sf.get("faktor", "neznan")
            value = safe_number(sf.get("intenzivnost", 0))
            unit = safe_unit(sf.get("enota", ""))

            aggregated["SF_count"] += 1
            aggregated["SF_weight"] += value
            aggregated["SF_list"].append((name, value))

            units_data[unit]["SF_count"] += 1
            units_data[unit]["SF_weight"] += value
            units_data[unit]["SF_list"].append((name, value))

        for pf in item.get("pozitivni_dejavniki", []):
            name = pf.get("faktor", "neznan")
            value = safe_number(pf.get("intenzivnost", 0))
            unit = safe_unit(pf.get("enota", ""))

            aggregated["PF_count"] += 1
            aggregated["PF_weight"] += value
            aggregated["PF_list"].append((name, value))

            units_data[unit]["PF_count"] += 1
            units_data[unit]["PF_weight"] += value
            units_data[unit]["PF_list"].append((name, value))

        for pr in item.get("predlogi", []):
            name = pr.get("faktor", "neznan")
            value = safe_number(pr.get("ucinek", 0))
            unit = safe_unit(pr.get("enota", ""))

            aggregated["PR_count"] += 1
            aggregated["PR_weight"] += value
            aggregated["PR_list"].append((name, value))

            units_data[unit]["PR_count"] += 1
            units_data[unit]["PR_weight"] += value
            units_data[unit]["PR_list"].append((name, value))

    return aggregated, units_data


# ============================================================
# 14. ZDRUŽEVANJE FAKTORJEV
# ============================================================


def merge_factors(items):

    merged = {}

    for name, value in items:
        if name not in merged:
            merged[name] = 0
        merged[name] += value

    return list(merged.items())


# ============================================================
# 15. DATAFRAME REZULTATOV (z dodano Enoto)
# ============================================================


def factors_to_dataframe(units_data):
    """Sestavi celoten DataFrame vseh faktorjev, z opredeljeno enoto,
    kategorijo, imenom faktorja in agregirano močjo."""

    rows = []

    categories = [
        ("Stresorji", "SF_list"),
        ("Pozitivni", "PF_list"),
        ("Predlogi", "PR_list"),
    ]

    for unit_code, bucket in units_data.items():

        unit_label = UNIT_LABELS.get(unit_code, "Nerazvrščeno")

        for category, key in categories:
            for name, value in merge_factors(bucket[key]):
                rows.append({
                    "Enota": unit_label,
                    "EnotaKoda": unit_code,
                    "Kategorija": category,
                    "Faktor": name,
                    "Moč": value
                })

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
# Uporablja se tako za SKUPNI izračun kot za izračun po posameznih enotah
# (enačbe 6-11 in 28-37 v članku sledijo popolnoma isti logiki, le da so
# fv/frv izračunani znotraj posamezne enote namesto čez celoten nabor).
# ============================================================

def calculate_stress_power(data, No, fo_pf_fallback=0.32, fo_pr_fallback=0.25):
    # No = število respondentov

    def get_Fo(fv, frv):
        if fv == 0 or No == 0:
            return 0.05  # Osnovna vrednost, če ni podatkov
        rho = fv / No                          # Enačba 12
        Co = fv / frv if frv > 0 else 1        # Enačba 18
        return (Co * rho) / 10                 # Enačba 24 (rhot=10, Ct=1)

    # Pridobivanje frekvenc (fv) in unikatnih mnenj (frv) iz agregiranih podatkov
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

    # Varovalka po članku: Fo_PF/Fo_PR ne smeta biti 0 (Enačba 27)
    if Fo_PF <= 0:
        Fo_PF = fo_pf_fallback
    if Fo_PR <= 0:
        Fo_PR = fo_pr_fallback

    # Enačba 27: sigma = arcsin(sqrt((Fo_SF * Fo_PR) / Fo_PF))
    try:
        val = (Fo_SF * Fo_PR) / Fo_PF
        sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    except Exception:
        sigma = 0

    return sigma, Fo_SF, Fo_PF, Fo_PR


def calculate_all_unit_stress_power(units_data, No):
    """Izračuna sigma (°S) in realne faktorje Fo za vsako od 6 klasifikacijskih
    enot posebej (Petrič, 2025 - enačbe 6-11 / 28-37). Vrne slovar:
    {koda_enote: {"sigma":..., "Fo_SF":..., "Fo_PF":..., "Fo_PR":...}}
    Vključi tudi "NEZ" (nerazvrščeni faktorji), če obstajajo.
    """

    unit_results = {}

    for code in list(UNIT_CODES) + (["NEZ"] if "NEZ" in units_data else []):

        bucket = units_data.get(code, _empty_bucket())

        sigma, fsf, fpf, fpr = calculate_stress_power(
            bucket, No,
            fo_pf_fallback=0.05,   # manjše, splošno varovalo za posamezne enote
            fo_pr_fallback=0.05
        )

        unit_results[code] = {
            "sigma": sigma,
            "Fo_SF": fsf,
            "Fo_PF": fpf,
            "Fo_PR": fpr,
            "SF_count": bucket["SF_count"],
            "PF_count": bucket["PF_count"],
            "PR_count": bucket["PR_count"],
        }

    return unit_results


# ============================================================
# 17. ENERGETSKI MODEL (Petrič, 2025 - Enačba 38)
# ============================================================

def calculate_energy(sigma, W_I_kcal=2500):
    # Enačba 38: W_EU = W_I - (W_I * sigma / 90)
    # Pozor: v modelu je maksimalna moč 90 stopinj
    loss_kcal = (W_I_kcal * sigma) / 90
    useful_kcal = W_I_kcal - loss_kcal
    efficiency = (useful_kcal / W_I_kcal) * 100 if W_I_kcal else 0

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
# 17b. OCENJEVALNA LESTVICA STRESNE MOČI (Petrič, 2025 - Tabela 6)
# ============================================================

def stress_level_label(sigma):

    if sigma < 0:
        sigma = 0

    if sigma <= 15.04:
        return "Zelo nizka"
    elif sigma <= 30.04:
        return "Nizka"
    elif sigma <= 45.04:
        return "Srednja"
    elif sigma <= 60.04:
        return "Višja"
    elif sigma <= 75.04:
        return "Visoka"
    else:
        return "Zelo visoka"


# ============================================================
# 18. TOP FAKTORJI
# ============================================================


def top_factors(df, category, unit_code=None):

    if df.empty:
        return pd.DataFrame()

    subset = df[df["Kategorija"] == category]

    if unit_code and unit_code != "VSE":
        subset = subset[subset["EnotaKoda"] == unit_code]

    if subset.empty:
        return pd.DataFrame()

    result = (
        subset
        .groupby("Faktor", as_index=False)["Moč"]
        .sum()
        .sort_values("Moč", ascending=False)
        .head(10)
    )

    return result


# ============================================================
# 19. GLAVNI PROGRAM
# ============================================================


if "dataset" in st.session_state:

    df = st.session_state["dataset"]

    st.divider()
    st.header("🧠 AI analiza respondentov")

    st.caption(
        f"Naloženih odgovorov skupaj: {len(df)}. "
        + (
            "⚠️ Testni način je vklopljen - obdelanih bo le prvih 3."
            if test_mode
            else "Analizirani bodo vsi zgornji odgovori."
        )
    )

    if st.button("🚀 ZAŽENI AI ANALIZO"):

        if not api_key:
            st.error("Vnesite Google API ključ.")

        else:
            client = initialize_ai(api_key)

            if client:
                st.info(f"Uporabljen model: {model_name}")

                with st.spinner(f"{model_name} analizira odgovore..."):

                    results, status_counts, total = run_multifactor_analysis(
                        df, client, model_name,
                        test_mode=test_mode,
                        max_retries=max_retries,
                        request_delay=request_delay
                    )

                    # --- SKUPNA + PO ENOTAH AGREGACIJA ---
                    aggregated, units_data = aggregate_factors(results)
                    factor_df = factors_to_dataframe(units_data)

                    # Skupni (celoten) izračun stresne moči - kot v v2.3
                    sigma, fsf, fpf, fpr = calculate_stress_power(aggregated, len(df))

                    # Izračun stresne moči POSEBEJ za vsako od 6 enot
                    unit_results = calculate_all_unit_stress_power(units_data, len(df))

                    # Shranjevanje v sejo (session_state)
                    st.session_state["results"] = results
                    st.session_state["aggregated"] = aggregated
                    st.session_state["units_data"] = units_data
                    st.session_state["factor_df"] = factor_df
                    st.session_state["sigma"] = sigma
                    st.session_state["f_factors"] = (fsf, fpf, fpr)
                    st.session_state["unit_results"] = unit_results
                    st.session_state["status_counts"] = status_counts
                    st.session_state["total_processed"] = total
                    # --- KONEC ---

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
# 20. PRIKAZ REZULTATOV
# ============================================================

if "sigma" in st.session_state:

    aggregated = st.session_state["aggregated"]
    units_data = st.session_state["units_data"]
    factor_df = st.session_state["factor_df"]
    sigma = st.session_state["sigma"]
    unit_results = st.session_state["unit_results"]
    status_counts = st.session_state.get("status_counts")
    total_processed = st.session_state.get("total_processed")

    # Izračun energije po skupnem (celotnem) modelu
    energy = calculate_energy(sigma, W_I_kcal=W_I_kcal)

    st.divider()
    st.header("📊 Rezultati Psihosocialnega Barometra")

    st.subheader("Skupna (celotna) stresna moč")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Stresna moč (nagib)", f"{sigma:.2f} °S")
        st.caption(f"Ocena: {stress_level_label(sigma)}")

    with col2:
        st.metric("Izguba energije", f"{energy['loss_kcal']:.0f} kcal")
        st.caption(f"= {energy['loss_kJ']:.0f} kJ")

    with col3:
        st.metric("Uporabna energija", f"{energy['useful_kcal']:.0f} kcal")
        st.caption(f"= {energy['useful_kJ']:.0f} kJ")

    with col4:
        st.metric("Učinkovitost (η)", f"{energy['efficiency']:.1f}%")

    st.divider()
    st.subheader("Vrednosti realnih faktorjev ($F_o$) - skupno")
    st.info(
        "Te vrednosti predstavljajo realni vpliv posamezne skupine dejavnikov "
        "na celotno stresno moč po modelu Petrič (2025)."
    )

    fs, fp, fpr = st.session_state.get("f_factors", (0, 0, 0))
    cf1, cf2, cf3 = st.columns(3)
    cf1.write(f"**$F_{{oSF}}$ (Stresorji):** {fs:.4f}")
    cf2.write(f"**$F_{{oPF}}$ (Pozitivni):** {fp:.4f}")
    cf3.write(f"**$F_{{oPR}}$ (Predlogi):** {fpr:.4f}")

    # --------------------------------------------------------
    # NOVO v2.4: Stresna moč in energija PO KATEGORIJAH (enotah)
    # --------------------------------------------------------

    st.divider()
    st.header("🧩 Rezultati po klasifikacijskih enotah")
    st.caption(
        "Izračun stresne moči (°S) in porabe energije (kcal) posebej za "
        "vsako od 6 klasifikacijskih enot po modelu Petrič (2025)."
    )

    unit_rows = []

    for code in UNIT_CODES:

        ur = unit_results.get(code, {"sigma": 0})
        u_sigma = ur["sigma"]
        u_energy = calculate_energy(u_sigma, W_I_kcal=W_I_kcal)

        unit_rows.append({
            "Enota": UNIT_LABELS[code],
            "σ (°S)": round(u_sigma, 2),
            "Ocena": stress_level_label(u_sigma),
            "Izguba energije (kcal)": round(u_energy["loss_kcal"], 0),
            "Učinkovitost (%)": round(u_energy["efficiency"], 1),
            "Št. stresorjev": ur.get("SF_count", 0),
            "Št. pozitivnih": ur.get("PF_count", 0),
            "Št. predlogov": ur.get("PR_count", 0),
        })

    # Nerazvrščeni faktorji (enota "NEZ"), če obstajajo
    nez = unit_results.get("NEZ")
    if nez and (nez.get("SF_count", 0) + nez.get("PF_count", 0) + nez.get("PR_count", 0)) > 0:
        u_sigma = nez["sigma"]
        u_energy = calculate_energy(u_sigma, W_I_kcal=W_I_kcal)
        unit_rows.append({
            "Enota": "Nerazvrščeno (NEZ)",
            "σ (°S)": round(u_sigma, 2),
            "Ocena": stress_level_label(u_sigma),
            "Izguba energije (kcal)": round(u_energy["loss_kcal"], 0),
            "Učinkovitost (%)": round(u_energy["efficiency"], 1),
            "Št. stresorjev": nez.get("SF_count", 0),
            "Št. pozitivnih": nez.get("PF_count", 0),
            "Št. predlogov": nez.get("PR_count", 0),
        })

    unit_df = pd.DataFrame(unit_rows)

    st.dataframe(unit_df, use_container_width=True)

    if nez and (nez.get("SF_count", 0) + nez.get("PF_count", 0) + nez.get("PR_count", 0)) > 0:
        st.caption(
            "⚠️ Nekaj faktorjev AI ni uspel razvrstiti v nobeno od 6 enot "
            "(prikazani kot 'Nerazvrščeno'). Za sporne primere lahko uporabiš "
            "AI pomoč pri klasifikaciji spodaj."
        )

    st.plotly_chart(
        px.bar(
            unit_df[unit_df["Enota"] != "Nerazvrščeno (NEZ)"],
            x="Enota", y="σ (°S)", color="Ocena",
            title="Stresna moč po klasifikacijskih enotah"
        ),
        use_container_width=True
    )

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        pie_df = pd.DataFrame({
            "Tip": ["Stresorji", "Pozitivni", "Predlogi"],
            "Vrednost": [
                aggregated["SF_weight"],
                aggregated["PF_weight"],
                aggregated["PR_weight"]
            ]
        })

        st.plotly_chart(
            px.pie(pie_df, names="Tip", values="Vrednost", hole=0.4),
            use_container_width=True
        )

    with c2:
        st.subheader("Vsi faktorji (z enoto)")
        st.dataframe(factor_df, use_container_width=True)

    st.divider()

    # Filter po enoti za spodnje top-liste
    filter_options = ["VSE"] + UNIT_CODES
    filter_labels = {"VSE": "Vse enote"}
    filter_labels.update(UNIT_LABELS)

    selected_unit = st.selectbox(
        "Filtriraj spodnje sezname po klasifikacijski enoti:",
        options=filter_options,
        format_func=lambda code: filter_labels.get(code, code)
    )

    st.subheader("🔥 Najmočnejši stresorji")

    sf_top = top_factors(factor_df, "Stresorji", selected_unit)

    if not sf_top.empty:
        st.plotly_chart(
            px.bar(sf_top, x="Moč", y="Faktor", orientation="h"),
            use_container_width=True
        )
    else:
        st.caption("Ni podatkov za izbrano kombinacijo.")

    st.subheader("🛡️ Zaščitni dejavniki")

    pf_top = top_factors(factor_df, "Pozitivni", selected_unit)

    if not pf_top.empty:
        st.plotly_chart(
            px.bar(pf_top, x="Moč", y="Faktor", orientation="h"),
            use_container_width=True
        )
    else:
        st.caption("Ni podatkov za izbrano kombinacijo.")

    st.subheader("💡 Predlogi izboljšav")

    pr_top = top_factors(factor_df, "Predlogi", selected_unit)

    st.dataframe(pr_top, use_container_width=True)

    # ========================================================
    # 21. IZVOZ CSV
    # ========================================================

    st.divider()

    exp1, exp2 = st.columns(2)

    with exp1:
        csv = factor_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Prenesi CSV - vsi faktorji (z enoto)",
            data=csv,
            file_name="Psihosocialni_Barometer_faktorji.csv",
            mime="text/csv"
        )

    with exp2:
        csv_units = unit_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Prenesi CSV - stresna moč po enotah",
            data=csv_units,
            file_name="Psihosocialni_Barometer_enote.csv",
            mime="text/csv"
        )


# ============================================================
# 22. PROMPTNO OKNO - AI POMOČ PRI KLASIFIKACIJI TEŽJIH PRIMEROV
# ============================================================

st.divider()
st.header("🧭 AI pomoč pri klasifikaciji težjega primera")

st.markdown(
    "Če imaš odgovor respondenta, ki ga avtomatska analiza slabo zajame "
    "(nejasen, dvoumen, večplasten odgovor), ga prilepi spodaj. AI bo "
    "predlagal razvrstitev v stresorje / pozitivne dejavnike / predloge, "
    "vsakega z ustrezno klasifikacijsko enoto, INTENZIVNOSTJO in **kratko "
    "obrazložitvijo**, zakaj je tako razvrstil."
)

manual_text = st.text_area(
    "Besedilo odgovora za ročno/podprto klasifikacijo:",
    height=120,
    placeholder="npr. 'Največ mi pomeni, ko me šef pohvali, čeprav me včasih "
                "moti, da je vedno prepozno na sestankih...'"
)


def build_manual_help_prompt(text):

    unit_legend = build_unit_legend()

    prompt = f"""
Si strokovni pomočnik za klasifikacijo psihosocialnih dejavnikov po modelu
Psihosocialni Barometer Petrič (2025/2026).

Spodnje besedilo je TEŽJI/SPORNI primer odgovora respondenta, ki ga je
človeški ocenjevalec označil kot nejasnega ali večplastnega. Tvoja naloga
je, da skrbno in razumljivo pomagaš pri ročni klasifikaciji.

Klasifikacijske enote:
{unit_legend}
- "NEZ": če faktorja resnično ni mogoče uvrstiti v nobeno od zgornjih enot

Za vsak faktor, ki ga zaznaš v besedilu (v katerikoli od treh kategorij:
stresorji, pozitivni_dejavniki, predlogi), navedi:
- "faktor": kratko ime dejavnika
- "enota": ena od kod zgoraj
- "intenzivnost" (za stresorje/pozitivne dejavnike) ali "ucinek" (za predloge): 0-5
- "obrazlozitev": ena do dve povedi, zakaj si faktor tako razvrstil/-a
  (npr. na kaj konkretno v besedilu se opira)

Vrni IZKLJUČNO veljaven JSON po tej strukturi (brez dodatnega besedila
zunaj JSON-a):

{{
"stresorji":[
    {{"faktor":"", "enota":"", "intenzivnost":0, "obrazlozitev":""}}
],
"pozitivni_dejavniki":[
    {{"faktor":"", "enota":"", "intenzivnost":0, "obrazlozitev":""}}
],
"predlogi":[
    {{"faktor":"", "enota":"", "ucinek":0, "obrazlozitev":""}}
]
}}

Besedilo za klasifikacijo:

{text}
"""

    return prompt


def classify_manual_case(client, model_name, text):

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=build_manual_help_prompt(text)
        )

        raw = response.text
        cleaned = clean_json_response(raw)
        data = json.loads(cleaned)

        if not isinstance(data, dict):
            return None, "AI ni vrnil veljavne strukture. Poskusi znova."

        data.setdefault("stresorji", [])
        data.setdefault("pozitivni_dejavniki", [])
        data.setdefault("predlogi", [])

        return data, None

    except json.JSONDecodeError:
        return None, "AI odgovora ni bilo mogoče razčleniti kot JSON. Poskusi znova."

    except Exception as e:
        return None, f"Napaka pri klicu AI: {e}"


if st.button("🔎 Vprašaj AI za pomoč pri klasifikaciji"):

    if not api_key:
        st.error("Vnesite Google API ključ v levem meniju.")

    elif not manual_text or len(manual_text.strip()) < 3:
        st.error("Vnesite besedilo odgovora za klasifikacijo.")

    else:
        client = initialize_ai(api_key)

        if client:
            with st.spinner(f"{model_name} analizira primer..."):
                result, error = classify_manual_case(client, model_name, manual_text)

            if error:
                st.error(error)

            else:
                st.session_state["manual_help_result"] = result


if "manual_help_result" in st.session_state:

    result = st.session_state["manual_help_result"]

    st.subheader("Predlagana klasifikacija")

    def _render_group(title, items, value_key):

        st.markdown(f"**{title}**")

        if not items:
            st.caption("Ni zaznanih faktorjev v tej kategoriji.")
            return

        for it in items:
            code = safe_unit(it.get("enota", ""))
            label = UNIT_LABELS.get(code, "Nerazvrščeno (NEZ)")
            value = it.get(value_key, "-")
            factor = it.get("faktor", "neznan")
            rationale = it.get("obrazlozitev", "")

            st.write(f"- **{factor}** → enota: *{label}*, vrednost: {value}")
            if rationale:
                st.caption(f"  {rationale}")

    _render_group("🔥 Stresorji", result.get("stresorji", []), "intenzivnost")
    _render_group("🛡️ Pozitivni dejavniki", result.get("pozitivni_dejavniki", []), "intenzivnost")
    _render_group("💡 Predlogi", result.get("predlogi", []), "ucinek")

    if st.button("Skrij predlog"):
        del st.session_state["manual_help_result"]
        st.rerun()


# ============================================================
# KONEC APLIKACIJE
# ============================================================





