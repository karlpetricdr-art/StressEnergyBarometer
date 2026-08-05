import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re

# 1. Nastavitve strani
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Sistem bo samodejno poiskal delujoč model.")

def extract_json(text):
    """Izlušči JSON seznam iz odgovora AI."""
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

# --- MATEMATIČNI MODEL (Enačbe 12-39) ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    def get_F(fv, frv):
        if No <= 0: return 0
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10
    
    F_sf = get_F(fv_sf, frv_sf)
    F_pf = get_F(fv_pf, frv_pf)
    F_pr = get_F(fv_pr, frv_pr)
    
    if F_pf <= 0: F_pf = 0.32
    
    val = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    return sigma, w_eu, (w_eu / 2500) * 100

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    st.success(f"Naloženo {len(data)} vrstic.")

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                # KONFIGURACIJA
                genai.configure(api_key=api_key)
                
                # DINAMIČNO ISKANJE MODELA (Rešitev za 404)
                # Vprašamo API, kateri modeli podpirajo 'generateContent'
                available_models = []
                for m in genai.list_models():
                    if 'generateContent' in m.supported_generation_methods:
                        available_models.append(m.name)
                
                if not available_models:
                    st.error("Vaš ključ nima dostopa do nobenega modela za generiranje vsebine.")
                else:
                    # Izberemo najboljšega (Flash) ali pa prvega dostopnega
                    selected_model_name = next((m for m in available_models if "1.5-flash" in m), available_models[0])
                    st.info(f"Povezava vzpostavljena z modelom: `{selected_model_name}`")
                    
                    model = genai.GenerativeModel(selected_model_name)
                    
                    # Priprava podatkov (Single-Shot klic)
                    all_text = "\n".join([f"Vnos {i+1}: {txt}" for i, txt in enumerate(data)])
                    
                    prompt = f"""
                    Extract ALL psychosocial factors (SF-stressor, PF-positive, PR-suggestion) 
                    based on Petrič (2025) for {len(data)} responses.
                    Units: At, St, So, PS, IP, HB.
                    Return ONLY a JSON list.
                    Format: [{{ "tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label" }}]
                    Data:
                    {all_text}
                    """
                    
                    with st.spinner("AI analizira... prosim počakajte."):
                        response = model.generate_content(prompt)
                        factors = extract_json(response.text)
                    
                    if factors:
                        f_df = pd.DataFrame(factors)
                        
                        def get_metrics(t):
                            # Preverimo 'tip' ne glede na male/velike črke
                            sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                            return len(sub), max(1, sub['opis'].nunique())

                        s, we, et = calculate_petric_model(*(get_metrics('SF') + get_metrics('PF') + get_metrics('PR')), len(data))

                        st.balloons()
                        st.header("Analiza uspešna")
                        c1, c2 = st.columns(2)
                        c1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                        c2.metric("Učinkovitost (η)", f"{et:.2f} %")
                        
                        st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                        st.dataframe(f_df)
                    else:
                        st.error("AI ni vrnil veljavnega JSON formata.")
                        st.write("Surovi odgovor AI (za debug):", response.text[:500])
                        
            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
