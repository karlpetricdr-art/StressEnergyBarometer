import streamlit as st
import pandas as pd
import plotly.express as px
import json
import math
import re
import time
from google import genai

# ============================================================
# 1. NASTAVITVE IN UI
# ============================================================
st.set_page_config(page_title="Psihosocialni Barometer v3.0", layout="wide")

st.title("📊 Psihosocialni Barometer v3.0")
st.subheader("Model Petrič (2025) - Agregirana Single-Shot Analiza")

with st.sidebar:
    st.header("⚙️ Nastavitve")
    api_key = st.text_input("Google API ključ:", type="password")
    model_choice = st.selectbox("Model:", ["gemini-1.5-flash", "gemini-2.0-flash-exp"])
    
    st.divider()
    No_input = st.number_input("Dejansko število respondentov (No):", min_value=1, value=200)
    W_I_kcal = st.number_input("Vhodna energija W_I (kcal):", value=2500)
    
    st.divider()
    st.info("Ta verzija analizira celotno besedilo hkrati. Rezultat bo pripravljen v manj kot 20 sekundah.")

# ============================================================
# 2. MATEMATIČNO JEDRO (Enačbe 12-39)
# ============================================================
def calculate_petric_logic(stats, No, WI):
    # No = število ljudi, stats = fv in frv vrednosti od AI
    
    def get_Fo(fv, frv):
        if fv == 0 or No == 0 or frv == 0: return 0.05
        rho = fv / No                         # Enačba 12 (Gostota)
        Co = fv / frv                         # Enačba 18 (Kompleksnost)
        return (Co * rho) / 10                # Enačba 24 (Realni faktor Fo, rhot=10)

    # Izračun realnih faktorjev za vse tri stebre
    F_sf = get_Fo(stats['fv_sf'], stats['frv_sf'])
    F_pf = get_Fo(stats['fv_pf'], stats['frv_pf'])
    F_pr = get_Fo(stats['fv_pr'], stats['frv_pr'])

    # Varovalka: F_pf ne sme biti 0 (stran 40 članka)
    if F_pf <= 0: F_pf = 0.32
    if F_pr <= 0: F_pr = 0.25

    # Enačba 27: Stresna moč (sigma)
    # sigma = arcsin(sqrt((F_sf * F_pr) / F_pf))
    try:
        val = (F_sf * F_pr) / F_pf
        sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    except:
        sigma = 0

    # Enačba 38: Dejansko porabljena energija (W_EU)
    # W_EU = W_I - (W_I * sigma / 90) --> Upoštevamo 90 stopinj kot max nagib
    loss_kcal = (WI * sigma) / 90
    w_eu = WI - loss_kcal
    efficiency = (w_eu / WI) * 100

    return {
        "sigma": sigma, "w_eu": w_eu, "loss": loss_kcal, "eff": efficiency,
        "F_sf": F_sf, "F_pf": F_pf, "F_pr": F_pr
    }

# ============================================================
# 3. AI STATISTIČNA EKSTRAKCIJA
# ============================================================
def run_single_shot_analysis(text, No, api_key, model_name):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Deluj kot ekspertni analitik po modelu Psihosocialni Barometer Petrič (2025).
    Analiziraj spodnjo množico odgovorov {No} respondentov.
    
    Naloga:
    Izračunaj agregatno statistiko za celoten vzorec. Upoštevaj, da respondenti v enem stavku pogosto navedejo več dejavnikov.
    
    Vrni IZKLJUČNO JSON objekt:
    {{
      "fv_sf": int, "frv_sf": int, (Stresorji: vsi zaznani / unikatni)
      "fv_pf": int, "frv_pf": int, (Pozitivni: vsi zaznani / unikatni)
      "fv_pr": int, "frv_pr": int, (Predlogi: vsi zaznani / unikatni)
      "enote_dist": {{"At": int, "St": int, "So": int, "PS": int, "IP": int, "HB": int}}, (Število zaznav po enotah)
      "top_stresorji": ["seznam 5 najpogostejših besednih zvez"]
    }}

    Besedilo za analizo:
    {text}
    """

    response = client.models.generate_content(model=model_name, contents=prompt)
    
    # Čiščenje JSON-a
    clean_text = re.sub(r'```json|```', '', response.text).strip()
    match = re.search(r'\{.*\}', clean_text, re.DOTALL)
    return json.loads(match.group()) if match else None

# ============================================================
# 4. GLAVNI TOK APLIKACIJE
# ============================================================
uploaded_file = st.file_uploader("📂 Naložite besedilno datoteko z vsemi odgovori (.txt)", type=["txt"])

if uploaded_file:
    raw_text = uploaded_file.read().decode("utf-8")
    st.success(f"Datoteka naložena. Velikost: {len(raw_text)} znakov.")

    if st.button("🚀 IZRAČUNAJ STRESNO MOČ IN ENERGIJO"):
        if not api_key:
            st.error("Vnesite API ključ!")
        else:
            with st.spinner("AI izvaja Single-Shot statistično analizo celotne množice..."):
                try:
                    # 1. AI oceni frekvence fv in frv
                    stats = run_single_shot_analysis(raw_text, No_input, api_key, model_choice)
                    
                    if stats:
                        # 2. Python izračuna matematiko po Petrič (2025)
                        res = calculate_petric_logic(stats, No_input, W_I_kcal)
                        
                        # 3. PRIKAZ REZULTATOV
                        st.divider()
                        st.balloons()
                        st.header(f"Končni rezultati analize (N={No_input})")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Stresna moč (σ)", f"{res['sigma']:.2f} °S")
                        col2.metric("Učinkovitost (η)", f"{res['eff']:.1f} %")
                        col3.metric("Uporabna energija", f"{int(res['w_eu'])} kcal")
                        col4.metric("Izguba energije", f"{int(res['loss'])} kcal")

                        st.divider()
                        c1, c2 = st.columns(2)
                        
                        with c1:
                            st.subheader("Porazdelitev po enotah (At, St, So...)")
                            enote_df = pd.DataFrame(stats['enote_dist'].items(), columns=['Enota', 'Zaznave'])
                            fig = px.bar(enote_df, x='Enota', y='Zaznave', color='Zaznave', color_continuous_scale='Reds')
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with c2:
                            st.subheader("Statistični parametri modela")
                            st.write(f"**Realni faktorji ($F_o$):**")
                            st.write(f"- Stresorji ($F_{{oSF}}$): `{res['F_sf']:.4f}`")
                            st.write(f"- Pozitivni ($F_{{oPF}}$): `{res['F_pf']:.4f}`")
                            st.write(f"- Predlogi ($F_{{oPR}}$): `{res['F_pr']:.4f}`")
                            st.write("---")
                            st.write(f"**Frekvence ($f_v$ / $f_{{rv}}$):**")
                            st.write(f"- SF: {stats['fv_sf']} / {stats['frv_sf']}")
                            st.write(f"- PF: {stats['fv_pf']} / {stats['frv_pf']}")
                            st.write(f"- PR: {stats['fv_pr']} / {stats['frv_pr']}")

                        st.subheader("🔥 Izpostavljeni stresorji")
                        st.write(", ".join(stats['top_stresorji']))

                except Exception as e:
                    st.error(f"Prišlo je do napake pri analizi: {e}")

# ============================================================




