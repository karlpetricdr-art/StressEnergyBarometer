import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import json
import re

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025) - Optimizirana Analiza")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.warning("Uporabljamo paketno obdelavo (10 respondentov naenkrat) za hitrejše rezultate.")

def clean_ai_json(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

def run_batch_analysis(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    extracted_data = []
    batch_size = 10  # Obdelamo 10 respondentov hkrati
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_text = st.empty()
    
    clean_list = [str(t).strip() for t in text_list if len(str(t).strip()) > 2]
    total_batches = math.ceil(len(clean_list) / batch_size)

    for i in range(0, len(clean_list), batch_size):
        batch = clean_list[i : i + batch_size]
        batch_str = "\n---\n".join([f"Respondent {idx+1}: {txt}" for idx, txt in enumerate(batch)])
        
        prompt = f"""
        Instructions: Extract all psychosocial factors (Stressors SF, Positive PF, Suggestions PR) 
        based on the Petrič (2025) model.
        Analyze each respondent separately.
        Categories: At, St, So, PS, IP, HB.
        
        Data to analyze:
        {batch_str}

        Return ONLY a flat JSON list of objects for all respondents combined.
        Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "short label"}} ]
        """
        
        try:
            response = model.generate_content(prompt)
            factors = clean_ai_json(response.text)
            if factors:
                extracted_data.extend(factors)
                log_text.info(f"Trenutno zaznanih dejavnikov: {len(extracted_data)}")
        except Exception as e:
            st.warning(f"Napaka pri paketu {i//batch_size + 1}: {e}")
        
        # Posodobitev napredka
        current_batch = (i // batch_size) + 1
        progress_bar.progress(current_batch / total_batches)
        status_text.text(f"Obdelava paketa {current_batch} od {total_batches}...")
        
        time.sleep(5) # Premor med paketi za Free Tier (15 RPM)
            
    return pd.DataFrame(extracted_data)

uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        text_data = pd.read_excel(uploaded_file).iloc[:, 0].tolist()
    elif uploaded_file.name.endswith('.csv'):
        text_data = pd.read_csv(uploaded_file).iloc[:, 0].tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = content.splitlines()

    if st.button("ZAŽENI ANALIZO 215 RESPONDENTOV"):
        if not api_key:
            st.error("Prosim vnesite API ključ.")
        else:
            with st.spinner("AI analizira podatke v paketih..."):
                factors_df = run_batch_analysis(text_data, api_key)
            
            if not factors_df.empty:
                No = len(text_data)
                
                def get_metrics(type_code):
                    subset = factors_df[factors_df['tip'].str.contains(type_code, na=False, case=False)]
                    fv, frv = len(subset), subset['opis'].nunique()
                    rho, Co = fv/No, (fv/frv if frv > 0 else 1)
                    return (Co * rho) / 10, fv, frv

                Fo_SF, fv_sf, frv_sf = get_metrics('SF')
                Fo_PF, fv_pf, frv_pf = get_metrics('PF')
                Fo_PR, fv_pr, frv_pr = get_metrics('PR')

                if Fo_PF <= 0: Fo_PF = 0.32
                if Fo_PR <= 0: Fo_PR = 0.25

                # Izračun stresne moči
                val = (Fo_SF * Fo_PR) / Fo_PF
                sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
                
                # Energija
                w_ls = (2500 * sigma_m) / 90
                w_eu = 2500 - w_ls

                # PRIKAZ
                st.balloons()
                st.header(f"Analiza končana! Zaznanih {len(factors_df)} dejavnikov.")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Stresna moč (σ)", f"{sigma_m:.2f} °S")
                c2.metric("Učinkovitost (η)", f"{((w_eu/2500)*100):.1f} %")
                c3.metric("Izguba (W_LS)", f"{int(w_ls)} kcal")

                st.plotly_chart(px.histogram(factors_df, x='enota', color='tip', barmode='group', title="Analiza po enotah Petrič (2025)"))
                st.write("### Podatki izluščeni iz besedil:")
                st.dataframe(factors_df)
            else:
                st.error("AI ni vrnil nobenih podatkov. Preverite API ključ ali vsebino datoteke.")
