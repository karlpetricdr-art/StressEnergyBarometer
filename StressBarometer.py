import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re

# 1. Osnovne nastavitve
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Način: Ultra-hitra statistična klasifikacija (< 20s)")

# --- MATEMATIČNA LOGIKA ---
def calculate_petric_math(stats, No):
    results = {}
    for tip in ['SF', 'PF', 'PR']:
        fv = stats.get(f'fv_{tip.lower()}', 0)
        frv = stats.get(f'frv_{tip.lower()}', 1)
        if fv == 0: 
            results[f'F_{tip.lower()}'] = 0.32 if tip == 'PF' else 0.25 if tip == 'PR' else 0.05
        else:
            rho = fv / No
            co = fv / frv if frv > 0 else 1
            results[f'F_{tip.lower()}'] = (co * rho) / 10
    
    # Enačba 27: Stresna moč
    F_sf, F_pf, F_pr = results['F_sf'], results['F_pf'], results['F_pr']
    if F_pf <= 0: F_pf = 0.32
    
    ratio = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(ratio))))
    
    # Energija (vhod 2500 kcal)
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    return sigma, w_eu, (w_eu / 2500) * 100, results

# --- ANALITIČNA FUNKCIJA (Single-Shot Statistical Estimation) ---
def run_ultra_fast_analysis(all_text, No, api_key):
    genai.configure(api_key=api_key)
    # Uporaba stabilnega modela
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Kot ekspert za psihosocialno diagnostiko analiziraj spodnjih {No} odgovorov.
    Na podlagi celotnega besedila oceni STATISTIČNO VERJETNOST in FREKVENCO dejavnikov po modelu Petrič (2025).
    
    Upoštevaj, da respondenti v enem stavku pogosto navajajo VEČ dejavnikov.
    Izračunaj/oceni naslednje vrednosti:
    1. fv_sf: skupna frekvenca vseh omenjenih stresorjev (SF).
    2. frv_sf: število različnih/unikatnih stresorjev.
    3. fv_pf: skupna frekvenca vseh pozitivnih dejavnikov (PF).
    4. frv_pf: število unikatnih pozitivnih dejavnikov.
    5. fv_pr: skupna frekvenca vseh predlogov (PR).
    6. frv_pr: število unikatnih predlogov.
    7. Razporeditev po enotah (At, St, So, PS, IP, HB) v odstotkih.

    Podatki:
    {all_text}

    Vrni IZKLJUČNO JSON objekt v tem formatu:
    {{
      "fv_sf": int, "frv_sf": int,
      "fv_pf": int, "frv_pf": int,
      "fv_pr": int, "frv_pr": int,
      "enote": {{"At": %, "St": %, "So": %, "PS": %, "IP": %, "HB": %}}
    }}
    """
    
    response = model.generate_content(prompt)
    # Čiščenje JSON-a
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return None

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
        text_data = df.iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = [l.strip() for l in content.splitlines() if len(l.strip()) > 5]

    No = len(text_data)
    st.success(f"Pripravljeno {No} odgovorov.")

    if st.button("🚀 ZAŽENI BLISKAVICO ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            with st.spinner("AI ocenjuje verjetnosti in frekvence..."):
                combined_text = "\n".join(text_data[:300]) # Omejitev na 300 vrstic za stabilnost
                stats = run_ultra_fast_analysis(combined_text, No, api_key)
            
            if stats:
                # Izračun po Petrič (2025)
                sigma, we, et, factors = calculate_petric_math(stats, No)

                # --- VIZUALIZACIJA ---
                st.balloons()
                st.header(f"Rezultat: {sigma:.2f} °S")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Moč stresa (σ)", f"{sigma:.2f} °S")
                c2.metric("Učinkovitost (η)", f"{et:.2f} %")
                c3.metric("Ocenjenih dejavnikov (fv_sf)", stats['fv_sf'])

                col_l, col_r = st.columns(2)
                with col_l:
                    # Graf razporeditve po enotah
                    enote_df = pd.DataFrame(stats['enote'].items(), columns=['Enota', 'Odstotek'])
                    fig = px.bar(enote_df, x='Enota', y='Odstotek', title="Ocenjena porazdelitev po enotah (%)", color='Odstotek')
                    st.plotly_chart(fig)
                
                with col_r:
                    st.write("### Statistični povzetek klasifikacije")
                    st.write(f"- Skupno stresorjev ($f_v$): {stats['fv_sf']}")
                    st.write(f"- Unikatnih stresorjev ($f_{{rv}}$): {stats['frv_sf']}")
                    st.write(f"- Pozitivnih dejavnikov ($f_v$): {stats['fv_pf']}")
                    st.write(f"- Predlogov ($f_v$): {stats['fv_pr']}")
                    st.info("Rezultat temelji na verjetnostni klasifikaciji celotnega vzorca.")
            else:
                st.error("AI ni uspel generirati statistike. Poskusite še enkrat.")
