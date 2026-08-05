import streamlit as st
import pandas as pd
import plotly.express as px
import json
import math
import re
import time
from google import genai

# ============================================================
# 1. NASTAVITVE IN UPORABNIŠKI VMESNIK
# ============================================================
st.set_page_config(page_title="Psihosocialni Barometer v3.1", layout="wide")

st.title("📊 Psihosocialni Barometer v3.1")
st.subheader("Model Petrič (2025/2026) - Multi-Model Agregirana Analiza")

with st.sidebar:
    st.header("⚙️ Nastavitve")
    api_key = st.text_input("Google API ključ:", type="password")
    
    # IZBIRA MODELA (Vključno z Gemmo)
    model_choice = st.selectbox(
        "Izberite AI model:", 
        [
            "gemini-1.5-flash", 
            "gemini-1.5-pro", 
            "gemini-2.0-flash-exp",
            "gemma-2-9b-it",
            "gemma-2-27b-it"
        ]
    )
    
    st.divider()
    No_input = st.number_input("Število respondentov (No):", min_value=1, value=200)
    W_I_kcal = st.number_input("Izhodiščna energija W_I (kcal):", value=2500)
    
    st.divider()
    st.info("Ta različica analizira celotno besedilo hkrati (Single-Shot), kar omogoča uporabo modelov Gemini in Gemma v realnem času.")

# ============================================================
# 2. MATEMATIČNI MODEL PETRIČ (2025)
# ============================================================
def calculate_petric_math(stats, No, WI):
    # fv: frekvenca vseh, frv: unikatna mnenja
    def get_F_factor(fv, frv):
        if fv == 0 or No == 0 or frv == 0: return 0.05
        rho = fv / No                         # Enačba 12 (Gostota)
        Co = fv / frv                         # Enačba 18 (Kompleksnost)
        return (Co * rho) / 10                # Enačba 24 (Realni faktor Fo)

    F_sf = get_F_factor(stats['fv_sf'], stats['frv_sf'])
    F_pf = get_F_factor(stats['fv_pf'], stats['frv_pf'])
    F_pr = get_F_factor(stats['fv_pr'], stats['frv_pr'])

    # Varovalke po članku (stran 40)
    if F_pf <= 0: F_pf = 0.32
    if F_pr <= 0: F_pr = 0.25

    # Enačba 27: Stresna moč (sigma) v stopinjah
    try:
        val = (F_sf * F_pr) / F_pf
        sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    except:
        sigma = 0

    # Enačba 38: Energetski model
    # Izguba energije glede na 90 stopinj maksimalne moči
    loss_kcal = (WI * sigma) / 90
    w_eu = WI - loss_kcal
    efficiency = (w_eu / WI) * 100

    return {
        "sigma": sigma, "w_eu": w_eu, "loss": loss_kcal, "eff": efficiency,
        "F_sf": F_sf, "F_pf": F_pf, "F_pr": F_pr
    }

# ============================================================
# 3. SINGLE-SHOT ANALIZA (Gemini/Gemma)
# ============================================================
def run_aggregate_analysis(text_content, No, api_key, model_name):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Kot ekspertni analitik po modelu Psihosocialni Barometer Petrič (2025) analiziraj odgovore {No} respondentov.
    
    Tvoja naloga:
    Preberi celotno besedilo in oceni agregatne statistike. 
    Upoštevaj, da respondenti v enem stavku pogosto navedejo VEČ dejavnikov hkrati.
    
    Vrni IZKLJUČNO JSON objekt:
    {{
      "fv_sf": int, "frv_sf": int, (Stresorji: vsi / unikatni)
      "fv_pf": int, "frv_pf": int, (Pozitivni: vsi / unikatni)
      "fv_pr": int, "frv_pr": int, (Predlogi: vsi / unikatni)
      "porazdelitev": {{"At": int, "St": int, "So": int, "PS": int, "IP": int, "HB": int}}, (Število zaznav po enotah)
      "kljucne_ugotovitve": ["seznam 3 glavnih ugotovitev"]
    }}

    Besedilo za analizo:
    {text_content}
    """

    response = client.models.generate_content(model=model_name, contents=prompt)
    
    # Čiščenje in ekstrahiranje JSON-a iz odgovora AI
    clean_text = re.sub(r'```json|```', '', response.text).strip()
    match = re.search(r'\{.*\}', clean_text, re.DOTALL)
    return json.loads(match.group()) if match else None

# ============================================================
# 4. GLAVNI PROGRAM
# ============================================================
uploaded_file = st.file_uploader("📂 Naložite tekstovno datoteko (.txt)", type=["txt"])

if uploaded_file:
    raw_text = uploaded_file.read().decode("utf-8")
    st.success(f"Datoteka uspešno naložena ({len(raw_text)} znakov).")

    if st.button(f"🚀 ZAŽENI ANALIZO Z MODELOM {model_choice}"):
        if not api_key:
            st.error("Prosim, vnesite API ključ!")
        else:
            with st.spinner(f"{model_choice} analizira celotno množico podatkov..."):
                try:
                    # 1. AI oceni statistiko frekvenc
                    stats = run_aggregate_analysis(raw_text, No_input, api_key, model_choice)
                    
                    if stats:
                        # 2. Python izvede matematične izračune po enačbah iz članka
                        res = calculate_petric_math(stats, No_input, W_I_kcal)
                        
                        # 3. PRIKAZ REZULTATOV
                        st.divider()
                        st.balloons()
                        st.header(f"Končni rezultati (N={No_input}, Model={model_choice})")
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Stresna moč (σ)", f"{res['sigma']:.2f} °S")
                        m2.metric("Učinkovitost (η)", f"{res['eff']:.1f}%")
                        m3.metric("Uporabna energija", f"{int(res['w_eu'])} kcal")
                        m4.metric("Izguba energije", f"{int(res['loss'])} kcal")

                        st.divider()
                        c1, c2 = st.columns(2)
                        
                        with c1:
                            st.subheader("Porazdelitev po enotah")
                            enote_df = pd.DataFrame(stats['porazdelitev'].items(), columns=['Enota', 'Zaznave'])
                            fig = px.bar(enote_df, x='Enota', y='Zaznave', color='Enota', title="Število zaznanih dejavnikov (At, St, So...)")
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with c2:
                            st.subheader("Parametri modela Petrič (2025)")
                            st.write(f"**Realni faktorji ($F_o$):**")
                            st.write(f"- $F_{{oSF}}$ (Stresorji): `{res['F_sf']:.4f}`")
                            st.write(f"- $F_{{oPF}}$ (Pozitivni): `{res['F_pf']:.4f}`")
                            st.write(f"- $F_{{oPR}}$ (Predlogi): `{res['F_pr']:.4f}`")
                            st.write("---")
                            st.write(f"**Vhodne frekvence ($f_v$ / $f_{{rv}}$):**")
                            st.write(f"- SF: {stats['fv_sf']} / {stats['frv_sf']}")
                            st.write(f"- PF: {stats['fv_pf']} / {stats['frv_pf']}")
                            st.write(f"- PR: {stats['fv_pr']} / {stats['frv_pr']}")

                        st.subheader("💡 Ključne ugotovitve analize")
                        for ugotovitev in stats['kljucne_ugotovitve']:
                            st.write(f"- {ugotovitev}")

                except Exception as e:
                    st.error(f"Prišlo je do napake: {e}")




