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
    st.info("Način: Ultra-hitra verjetnostna klasifikacija.")

# --- MATEMATIČNA LOGIKA (Enačbe 12-39) ---
def calculate_petric_math(stats, No):
    results = {}
    for tip in ['SF', 'PF', 'PR']:
        fv = stats.get(f'fv_{tip.lower()}', 0)
        frv = stats.get(f'frv_{tip.lower()}', 1)
        
        # Če AI ne najde podatkov, vzamemo znanstvene konstante iz članka
        if fv == 0: 
            results[f'F_{tip.lower()}'] = 0.32 if tip == 'PF' else 0.25 if tip == 'PR' else 0.05
        else:
            rho = fv / No
            co = fv / frv if frv > 0 else 1
            results[f'F_{tip.lower()}'] = (co * rho) / 10
    
    # Enačba 27: Stresna moč sigma
    F_sf, F_pf, F_pr = results['F_sf'], results['F_pf'], results['F_pr']
    if F_pf <= 0: F_pf = 0.32
    
    razmerje = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(razmerje))))
    
    # Energija (2500 kcal)
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    return sigma, w_eu, (w_eu / 2500) * 100

# --- ANALITIČNA FUNKCIJA (Single-Shot Discovery) ---
def run_fast_analysis(all_text, No, api_key):
    genai.configure(api_key=api_key)
    
    # DINAMIČNA IZBIRA MODELA (Rešitev za 404)
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Poiščemo Flash model, sicer vzamemo prvega
        selected_model = next((m for m in models if 'flash' in m), models[0])
        model = genai.GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"Napaka pri povezavi z API-jem: {e}")
        return None

    prompt = f"""
    Kot ekspert za psihosocialno diagnostiko analiziraj spodnjih {No} odgovorov.
    Upoštevaj model Petrič (2025). Respondenti v enem stavku pogosto navajajo VEČ dejavnikov.
    
    Oceni naslednje vrednosti za celoten vzorec:
    1. fv_sf: skupna frekvenca vseh zaznanih stresorjev (SF).
    2. frv_sf: število unikatnih/različnih stresorjev.
    3. fv_pf: skupna frekvenca vseh pozitivnih dejavnikov (PF).
    4. frv_pf: število unikatnih pozitivnih dejavnikov.
    5. fv_pr: skupna frekvenca vseh predlogov (PR).
    6. frv_pr: število unikatnih predlogov.
    7. Porazdelitev po enotah (At, St, So, PS, IP, HB) v odstotkih.

    Podatki:
    {all_text}

    Vrni IZKLJUČNO JSON objekt:
    {{
      "fv_sf": int, "frv_sf": int,
      "fv_pf": int, "frv_pf": int,
      "fv_pr": int, "frv_pr": int,
      "enote": {{"At": %, "St": %, "So": %, "PS": %, "IP": %, "HB": %}}
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Izluščimo JSON iz odgovora
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        st.error(f"AI napaka: {e}")
    return None

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        data = [l.strip() for l in uploaded_file.read().decode("utf-8").splitlines() if len(l.strip()) > 5]

    if st.button("🚀 ZAŽENI HITRO ANALIZO"):
        if not api_key:
            st.error("Vnesite API ključ!")
        else:
            with st.spinner("AI analizira frekvence..."):
                # Pošljemo vse vrstice hkrati
                combined_text = "\n".join(data)
                stats = run_fast_analysis(combined_text, len(data), api_key)
            
            if stats:
                sigma, we, et = calculate_petric_math(stats, len(data))

                st.balloons()
                st.header(f"Rezultat: {sigma:.2f} °S")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Moč stresa (σ)", f"{sigma:.2f} °S")
                c2.metric("Učinkovitost (η)", f"{et:.2f} %")
                c3.metric("Zaznanih stresorjev", stats['fv_sf'])

                # Prikaz grafikona
                enote_df = pd.DataFrame(stats['enote'].items(), columns=['Enota', 'Odstotek'])
                fig = px.bar(enote_df, x='Enota', y='Odstotek', color='Odstotek', title="Porazdelitev stresa po enotah (%)")
                st.plotly_chart(fig)
                
                st.write("### Statistični podatki analize")
                st.json(stats)
            else:
                st.error("AI ni uspel pripraviti izračuna. Poskusite ponovno.")
