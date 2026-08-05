import streamlit as st
import pandas as pd
import plotly.express as px
import json
import math
import re
from google import genai

# ============================================================
# 1. NASTAVITVE IN UPORABNIŠKI VMESNIK
# ============================================================
st.set_page_config(page_title="Psihosocialni Barometer v3.0", layout="wide")

st.title("📊 Psihosocialni Barometer v3.0 (Agregirana analiza)")
st.markdown("Model Petrič (2025) - Analiza celotne množice respondentov hkrati.")

with st.sidebar:
    st.header("⚙️ Nastavitve")
    api_key = st.text_input("Google API ključ:", type="password")
    
    st.divider()
    No_input = st.number_input("Število respondentov (No):", min_value=1, value=200)
    W_I_kcal = st.number_input("Vhodna energija W_I (kcal):", value=2500)
    
    st.divider()
    st.info("Ta verzija procesira celotno besedilo hkrati in izračuna stresno moč v manj kot 20 sekundah.")

# ============================================================
# 2. MATEMATIČNE ENAČBE (Petrič, 2025)
# ============================================================
def calculate_petric_model(stats, No, WI):
    # Enačbe 12, 18 in 24 za SF, PF in PR
    def get_F(fv, frv):
        if fv == 0 or No == 0 or frv == 0: return 0.05
        rho = fv / No                         # Enačba 12
        Co = fv / frv                         # Enačba 18
        return (Co * rho) / 10                # Enačba 24

    F_sf = get_F(stats['fv_sf'], stats['frv_sf'])
    F_pf = get_F(stats['fv_pf'], stats['frv_pf'])
    F_pr = get_F(stats['fv_pr'], stats['frv_pr'])

    # Varovalka: F_pf ne sme biti 0 (stran 40)
    if F_pf <= 0: F_pf = 0.32
    if F_pr <= 0: F_pr = 0.25

    # Enačba 27: Stresna moč (sigma) v stopinjah
    try:
        val = (F_sf * F_pr) / F_pf
        sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    except:
        sigma = 0

    # Enačba 38: Dejansko porabljena energija (W_EU)
    # W_EU = WI - (WI * sigma / 90)
    loss_kcal = (WI * sigma) / 90
    w_eu = WI - loss_kcal
    efficiency = (w_eu / WI) * 100

    return {
        "sigma": sigma, "w_eu": w_eu, "loss": loss_kcal, "eff": efficiency,
        "F_sf": F_sf, "F_pf": F_pf, "F_pr": F_pr
    }

# ============================================================
# 3. AI ANALIZA (Single-Shot Aggregation)
# ============================================================
def run_bulk_analysis(text_content, No, api_key):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Analiziraj spodnje besedilo, ki vsebuje odgovore {No} respondentov po modelu Petrič (2025).
    Tvoja naloga je izračunati agregatne frekvence za celotno množico.
    
    Upoštevaj:
    - Vsak respondent lahko v enem stavku navede več dejavnikov.
    - fv (frekvenca mnenj): skupno število vseh zaznanih pojavov.
    - frv (variabilnost): število vsebinsko unikatnih/različnih mnenj.

    Izračunaj/oceni:
    1. Stresorji (SF): fv_sf in frv_sf.
    2. Pozitivni dejavniki (PF): fv_pf in frv_pf.
    3. Predlogi (PR): fv_pr in frv_pr.
    4. Porazdelitev vseh dejavnikov po enotah (At, St, So, PS, IP, HB) v številu zaznav.

    Vrni IZKLJUČNO JSON objekt v tem formatu:
    {{
      "fv_sf": int, "frv_sf": int,
      "fv_pf": int, "frv_pf": int,
      "fv_pr": int, "frv_pr": int,
      "enote": {{"At": int, "St": int, "So": int, "PS": int, "IP": int, "HB": int}}
    }}

    Besedilo za analizo:
    {text_content}
    """

    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    
    # Čiščenje JSON-a
    clean_text = re.sub(r'```json|```', '', response.text).strip()
    match = re.search(r'\{.*\}', clean_text, re.DOTALL)
    return json.loads(match.group()) if match else None

# ============================================================
# 4. GLAVNI TOK
# ============================================================
uploaded_file = st.file_uploader("📂 Naložite tekstovno datoteko z vsemi odgovori (.txt)", type=["txt"])

if uploaded_file:
    # Preprosto preberemo celotno besedilo
    raw_text = uploaded_file.read().decode("utf-8")
    st.success(f"Datoteka naložena ({len(raw_text)} znakov).")

    if st.button("🚀 IZRAČUNAJ STRESNO MOČ IN ENERGIJO"):
        if not api_key:
            st.error("Vnesite API ključ!")
        else:
            with st.spinner("AI statistično ocenjuje množico podatkov..."):
                try:
                    # AI prebere vse hkrati
                    stats = run_bulk_analysis(raw_text, No_input, api_key)
                    
                    if stats:
                        # Python izračuna po enačbah
                        res = calculate_petric_model(stats, No_input, W_I_kcal)
                        
                        # PRIKAZ REZULTATOV
                        st.divider()
                        st.balloons()
                        st.header(f"Končni rezultati (N={No_input})")
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Stresna moč (σ)", f"{res['sigma']:.2f} °S")
                        m2.metric("Učinkovitost (η)", f"{res['eff']:.1f}%")
                        m3.metric("Uporabna energija", f"{int(res['w_eu'])} kcal")
                        m4.metric("Izguba", f"{int(res['loss'])} kcal")

                        st.divider()
                        c1, c2 = st.columns(2)
                        
                        with c1:
                            st.subheader("Struktura zaznanih dejavnikov")
                            enote_df = pd.DataFrame(stats['enote'].items(), columns=['Enota', 'Število'])
                            fig = px.bar(enote_df, x='Enota', y='Število', color='Enota', title="Porazdelitev po enotah (At, St, So...)")
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with c2:
                            st.subheader("Statistični parametri modela")
                            st.write(f"**Realni faktorji ($F_o$):**")
                            st.write(f"- $F_{{oSF}}$ (Stresorji): {res['F_sf']:.4f}")
                            st.write(f"- $F_{{oPF}}$ (Pozitivni): {res['F_pf']:.4f}")
                            st.write(f"- $F_{{oPR}}$ (Predlogi): {res['F_pr']:.4f}")
                            st.write("---")
                            st.write(f"**Frekvence ($f_v$ / $f_{{rv}}$):**")
                            st.write(f"- Stresorji: {stats['fv_sf']} / {stats['frv_sf']}")
                            st.write(f"- Pozitivni: {stats['fv_pf']} / {stats['frv_pf']}")
                            st.write(f"- Predlogi: {stats['fv_pr']} / {stats['frv_pr']}")

                except Exception as e:
                    st.error(f"Prišlo je do napake pri analizi: {e}")



