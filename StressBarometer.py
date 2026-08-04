import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import json
import re

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Sistem bo samodejno izbral najboljši dostopen model.")

def clean_ai_json(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None

def run_multi_factor_analysis(text_list, api_key):
    genai.configure(api_key=api_key)
    
    # DIAGNOSTIKA: Preverimo dostopne modele
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # Izbira najboljšega modela
    selected_model = "gemini-1.5-flash" # Privzeto
    if "models/gemini-1.5-flash" not in available_models:
        if "models/gemini-pro" in available_models:
            selected_model = "gemini-pro"
        else:
            # Če nič ne najde, vzame prvega na seznamu
            selected_model = available_models[0].replace("models/", "") if available_models else "gemini-1.5-flash"

    st.write(f"Uporabljam model: `{selected_model}`")
    model = genai.GenerativeModel(selected_model)
    
    extracted_data = []
    debug_logs = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    clean_list = [t for t in text_list if len(str(t).strip()) > 2]
    
    for i, text in enumerate(clean_list):
        prompt = f"""
        Extract psychosocial factors based on Petrič (2025). 
        Return ONLY a JSON list.
        Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label"}} ]
        Text: "{text}"
        """
        try:
            response = model.generate_content(prompt)
            factors = clean_ai_json(response.text)
            if factors:
                for f in factors:
                    if all(k in f for k in ('tip', 'enota', 'opis')):
                        extracted_data.append(f)
            else:
                debug_logs.append(f"Respondent {i+1}: Ni JSON-a. AI odgovor: {response.text[:50]}")
        except Exception as e:
            debug_logs.append(f"Respondent {i+1}: {str(e)}")
        
        progress_bar.progress((i + 1) / len(clean_list))
        status_text.text(f"Analiza: {i+1} / {len(clean_list)}")
        time.sleep(1.5) # Varnostni premor za brezplačni ključ
            
    return pd.DataFrame(extracted_data), debug_logs

uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        text_data = pd.read_excel(uploaded_file).iloc[:, 0].astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        text_data = pd.read_csv(uploaded_file).iloc[:, 0].astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = [line.strip() for line in content.splitlines() if line.strip()]

    if st.button("ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Vnesite API ključ.")
        else:
            factors_df, logs = run_multi_factor_analysis(text_data, api_key)
            
            if not factors_df.empty:
                No = len(text_data)
                def get_metrics(type_code):
                    subset = factors_df[factors_df['tip'].str.contains(type_code, na=False)]
                    fv, frv = len(subset), subset['opis'].nunique()
                    rho, Co = fv/No, (fv/frv if frv > 0 else 1)
                    return (Co * rho) / 10, fv, frv

                Fo_SF, fv_sf, frv_sf = get_metrics('SF')
                Fo_PF, fv_pf, frv_pf = get_metrics('PF')
                Fo_PR, fv_pr, frv_pr = get_metrics('PR')

                if Fo_PF <= 0: Fo_PF = 0.32
                if Fo_PR <= 0: Fo_PR = 0.25

                try:
                    val = (Fo_SF * Fo_PR) / Fo_PF
                    sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
                except: sigma_m = 0

                st.balloons()
                st.header(f"Analiza zaključena: {len(factors_df)} dejavnikov")
                m1, m2, m3 = st.columns(3)
                m1.metric("Stresna moč (σ)", f"{sigma_m:.2f} °S")
                m2.metric("Učinkovitost (η)", f"{((2500 - (2500*sigma_m/90)) / 2500)*100:.1f} %")
                m3.metric("Zaznanih stresorjev (fv)", fv_sf)

                st.plotly_chart(px.histogram(factors_df, x='enota', color='tip', barmode='group'))
                st.write("### Podrobna tabela izluščenih dejavnikov:")
                st.dataframe(factors_df)
            
            if logs:
                with st.expander("Diagnostika (Debug Log)"):
                    for log in logs: st.text(log)
