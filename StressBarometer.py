# ============================================================
# PSIHOSOCIALNI BAROMETER v2.4
# Karl Petrič, 2025/2026
#
# Optimizirana Gemini / Gemma kompatibilna verzija
# google-genai SDK
#
# GLAVNE IZBOLJŠAVE:
# - hitrejša obdelava: single-shot pristop, manjši prompt
# - retry logika ob napaki 429 / RESOURCE_EXHAUSTED
# - sledenje uspešnim / neuspešnim AI klicem
# - jasno opozorilo v UI, če je testni način vklopljen
# - prikaz dejanskega števila obdelanih odgovorov
# - ocena preostalega časa med analizo
# - normalizacija faktorjev za boljše agregiranje
# - matematično doslednejši izračun sigma in energije
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import time
import math
import re
from collections import Counter
from google import genai

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
✅ JSON ekstrakcijo  
✅ agregacijo respondentov  
✅ energijski model stresa v kcal in kJ  
✅ retry ob napaki + sledenje uspešnosti analize  
✅ hitrejši single-shot pristop
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

    st.info("Priporočilo: gemini-2.0-flash za hitrost; gemma za lokalno testiranje")

    st.divider()

    test_mode = st.checkbox(
        "Testni način (analizira samo prve 3 odgovore)",
        value=False
    )

    if test_mode:
        st.warning(
            "⚠️ Testni način je VKLOPLJEN. Analizirani bodo samo prvi 3 odgovori."
        )

    st.divider()

    st.subheader("Robustnost klicev")

    max_retries = st.slider(
        "Največ ponovitev ob napaki:",
        min_value=0,
        max_value=3,
        value=1
    )

    request_delay = st.slider(
        "Premor med klici (sekunde):",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
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
# 4. NALAGANJE PODATKOV
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
# 5. PRIPRAVA DATAFRAME
# ============================================================

def prepare_dataframe(df):
    if df is None or len(df.columns) == 0:
        return None

    if "Odgovor" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Odgovor"})

    df["Odgovor"] = (
        df["Odgovor"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df = df[df["Odgovor"].str.len() > 5].copy()
    df.reset_index(drop=True, inplace=True)
    return df

# ============================================================
# 6. JSON FUNKCIJE
# ============================================================

def clean_json_response(text):
    if not text:
        return "{}"

    text = text.strip()
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end >= 0 and end > start:
        text = text[start:end + 1]

    return text.strip()

def empty_analysis():
    return {
        "stresorji": [],
        "pozitivni_dejavniki": [],
        "predlogi": []
    }

# ============================================================
# 7. PRIKAZ PODATKOV
# ============================================================

uploaded_file = st.file_uploader(
    "📂 Naložite odgovore respondentov",
    type=["xlsx", "csv", "txt", "tsv"]
)

if uploaded_file:
    df = load_dataset(uploaded_file)
    df = prepare_dataframe(df)

    if df is not None:
        st.success(f"Naloženih odgovorov: {len(df)}")
        st.dataframe(df.head(10), use_container_width=True)
        st.session_state["dataset"] = df

# ============================================================
# 8. PROMPT ZA AI ANALIZO
# ============================================================

def build_analysis_prompt(answer):
    return f"""
Analiziraj odgovor respondenta po modelu Psihosocialni Barometer Petrič (2025/2026).

Naloga:
Iz enega odgovora identificiraj dejavnike in vrni IZKLJUČNO veljaven JSON.

Kategorije:
- stresorji
- pozitivni_dejavniki
- predlogi

Lestvica intenzivnosti:
0 = ni prisotno
1 = zelo nizko
2 = nizko
3 = srednje
4 = visoko
5 = zelo visoko

Struktura:
{{
  "stresorji": [
    {{"faktor": "", "intenzivnost": 0}}
  ],
  "pozitivni_dejavniki": [
    {{"faktor": "", "intenzivnost": 0}}
  ],
  "predlogi": [
    {{"faktor": "", "ucinek": 0}}
  ]
}}

Pravila:
- Vrni samo JSON, brez razlage.
- Uporabi kratke, konsistentne nazive faktorjev.
- Če ni faktorja, vrni prazno listo.

Odgovor respondenta:
{answer}
"""

# ============================================================
# 9. ANALIZA ENEGA ODGOVORA
# ============================================================

def analyze_single_response(client, model_name, answer, max_retries=1):
    default = empty_analysis()
    attempt = 0
    wait_time = 1.0

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
            attempt += 1
            if attempt > max_retries:
                return default, "prazen_json"
            time.sleep(wait_time)
            wait_time *= 2

        except Exception as e:
            error_text = str(e)
            is_quota_error = ("429" in error_text or "RESOURCE_EXHAUSTED" in error_text)

            attempt += 1
            if attempt > max_retries:
                return default, "napaka_kvote" if is_quota_error else "napaka"

            time.sleep(wait_time * (2 if is_quota_error else 1))
            wait_time *= 2

    return default, "napaka"

# ============================================================
# 10. NORMALIZACIJA FAKTORJEV
# ============================================================

def normalize_factor_name(name):
    if not name:
        return "neznan"
    name = str(name).strip().lower()
    name = re.sub(r"\s+", " ", name)
    name = name.replace("občutek ", "")
    name = name.replace("stalen ", "")
    name = name.replace("zelo ", "")
    return name

# ============================================================
# 11. AGREGACIJA FAKTORJEV
# ============================================================

def safe_number(value):
    try:
        return int(value)
    except:
        return 0

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
        for sf in item.get("stresorji", []):
            name = normalize_factor_name(sf.get("faktor", "neznan"))
            value = safe_number(sf.get("intenzivnost", 0))
            data["SF_count"] += 1
            data["SF_weight"] += value
            data["SF_list"].append((name, value))

        for pf in item.get("pozitivni_dejavniki", []):
            name = normalize_factor_name(pf.get("faktor", "neznan"))
            value = safe_number(pf.get("intenzivnost", 0))
            data["PF_count"] += 1
            data["PF_weight"] += value
            data["PF_list"].append((name, value))

        for pr in item.get("predlogi", []):
            name = normalize_factor_name(pr.get("faktor", "neznan"))
            value = safe_number(pr.get("ucinek", 0))
            data["PR_count"] += 1
            data["PR_weight"] += value
            data["PR_list"].append((name, value))

    return data

def merge_factors(items):
    merged = Counter()
    for name, value in items:
        merged[name] += value
    return list(merged.items())

def factors_to_dataframe(aggregated):
    rows = []
    categories = [
        ("Stresorji", "SF_list"),
        ("Pozitivni", "PF_list"),
        ("Predlogi", "PR_list")
    ]

    for category, key in categories:
        for name, value in merge_factors(aggregated[key]):
            rows.append({
                "Kategorija": category,
                "Faktor": name,
                "Moč": value
            })

    return pd.DataFrame(rows)

# ============================================================
# 12. MODEL STRESNE MOČI
# ============================================================

def calculate_stress_power(data, No):
    def get_Fo(fv, frv):
        if fv <= 0 or No <= 0:
            return 0.05
        rho = fv / No
        Co = fv / frv if frv > 0 else 1
        return (Co * rho) / 10

    f_sf = data.get("SF_count", 0)
    frv_sf = len(set([x[0] for x in data.get("SF_list", [])]))

    f_pf = data.get("PF_count", 0)
    frv_pf = len(set([x[0] for x in data.get("PF_list", [])]))

    f_pr = data.get("PR_count", 0)
    frv_pr = len(set([x[0] for x in data.get("PR_list", [])]))

    Fo_SF = get_Fo(f_sf, frv_sf)
    Fo_PF = get_Fo(f_pf, frv_pf)
    Fo_PR = get_Fo(f_pr, frv_pr)

    if Fo_PF <= 0:
        Fo_PF = 0.32
    if Fo_PR <= 0:
        Fo_PR = 0.25

    try:
        val = (Fo_SF * Fo_PR) / Fo_PF
        val = max(0.0, min(1.0, val))
        sigma = math.degrees(math.asin(math.sqrt(val)))
    except:
        sigma = 0.0

    return sigma, Fo_SF, Fo_PF, Fo_PR

# ============================================================
# 13. ENERGETSKI MODEL
# ============================================================

def calculate_energy(sigma, W_I_kcal=2500):
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
# 14. ANALIZA CELOTNEGA DATASETA
# ============================================================

def run_multifactor_analysis(df, client, model_name, test_mode=False, max_retries=1, request_delay=0.0):
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

    for idx, row in df.iterrows():
        answer = row["Odgovor"]

        result, status = analyze_single_response(
            client,
            model_name,
            answer,
            max_retries=max_retries
        )

        results.append(result)
        status_counts[status] += 1

        done = len(results)
        elapsed = time.time() - start_time
        avg_per_item = elapsed / done if done else 0
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
# 15. GLAVNI PROGRAM
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
            else "Analizirani bodo vsi odgovori."
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
                        df,
                        client,
                        model_name,
                        test_mode=test_mode,
                        max_retries=max_retries,
                        request_delay=request_delay
                    )

                    aggregated = aggregate_factors(results)
                    factor_df = factors_to_dataframe(aggregated)

                    valid_n = total
                    sigma, fsf, fpf, fpr = calculate_stress_power(aggregated, valid_n)

                    st.session_state["results"] = results
                    st.session_state["aggregated"] = aggregated
                    st.session_state["factor_df"] = factor_df
                    st.session_state["sigma"] = sigma
                    st.session_state["f_factors"] = (fsf, fpf, fpr)
                    st.session_state["status_counts"] = status_counts
                    st.session_state["total_processed"] = total

                ok = status_counts["ok"]
                problematic = total - ok

                if problematic == 0:
                    st.success(
                        f"AI analiza uspešno zaključena. Vseh {total} odgovorov je bilo uspešno analiziranih."
                    )
                else:
                    st.warning(
                        f"AI analiza zaključena: {ok}/{total} odgovorov uspešno analiziranih. "
                        f"{problematic} odgovorov ni bilo mogoče v celoti obdelati "
                        f"(prazen/neveljaven JSON: {status_counts['prazen_json']}, "
                        f"presežena kvota: {status_counts['napaka_kvote']}, "
                        f"druge napake: {status_counts['napaka']})."
                    )

# ============================================================
# 16. PRIKAZ REZULTATOV
# ============================================================

if "sigma" in st.session_state:
    aggregated = st.session_state["aggregated"]
    factor_df = st.session_state["factor_df"]
    sigma = st.session_state["sigma"]
    status_counts = st.session_state.get("status_counts")
    total_processed = st.session_state.get("total_processed")

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

    st.divider()
    st.subheader("Vrednosti realnih faktorjev ($F_o$)")
    st.info("Te vrednosti predstavljajo realni vpliv posamezne skupine dejavnikov na celotno stresno moč po modelu Petrič (2025).")

    fs, fp, fpr = st.session_state.get("f_factors", (0, 0, 0))
    cf1, cf2, cf3 = st.columns(3)
    cf1.write(f"**$F_{{oSF}}$ (Stresorji):** {fs:.4f}")
    cf2.write(f"**$F_{{oPF}}$ (Pozitivni):** {fp:.4f}")
    cf3.write(f"**$F_{{oPR}}$ (Predlogi):** {fpr:.4f}")

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
        st.subheader("Vsi faktorji")
        st.dataframe(factor_df, use_container_width=True)

    st.divider()

    st.subheader("🔥 Najmočnejši stresorji")
    sf_top = factor_df[factor_df["Kategorija"] == "Stresorji"].groupby("Faktor", as_index=False)["Moč"].sum().sort_values("Moč", ascending=False).head(10) if not factor_df.empty else pd.DataFrame()
    if not sf_top.empty:
        st.plotly_chart(
            px.bar(sf_top, x="Moč", y="Faktor", orientation="h"),
            use_container_width=True
        )

    st.subheader("🛡️ Zaščitni dejavniki")
    pf_top = factor_df[factor_df["Kategorija"] == "Pozitivni"].groupby("Faktor", as_index=False)["Moč"].sum().sort_values("Moč", ascending=False).head(10) if not factor_df.empty else pd.DataFrame()
    if not pf_top.empty:
        st.plotly_chart(
            px.bar(pf_top, x="Moč", y="Faktor", orientation="h"),
            use_container_width=True
        )

    st.subheader("💡 Predlogi izboljšav")
    pr_top = factor_df[factor_df["Kategorija"] == "Predlogi"].groupby("Faktor", as_index=False)["Moč"].sum().sort_values("Moč", ascending=False).head(10) if not factor_df.empty else pd.DataFrame()
    st.dataframe(pr_top, use_container_width=True)

    csv = factor_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Prenesi CSV rezultat",
        data=csv,
        file_name="Psihosocialni_Barometer_rezultat.csv",
        mime="text/csv"
    )

# ============================================================
# KONEC APLIKACIJE
# ============================================================



