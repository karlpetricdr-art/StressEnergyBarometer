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
    st.info("Sistem bo samodejno poiskal delujoč model na vašem računu.")

def clean_ai_json(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

def get_working_model(api_key):
    """Poišče prvi model, ki dejansko deluje za vaš ključ."""
    genai.configure(api_key=api_key)
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prednost dajemo flash modelu
        for m in models:
            if 'flash' in m.lower():
                return genai.GenerativeModel(m)
        return genai.GenerativeModel(models[0]) if models else None
    except Exception as e:
        st.error(f"Ni mogoče dobiti seznama modelov: {e}")
        return None

def run_batch_analysis(text_list, api_key):
    model = get_working_model(api_key)
    if not model:
        st.error("Model ni na voljo. Preverite API ključ.")
        return pd.DataFrame()
    
    st.success(f"Uporabljam model: {model.model_name}")
    
    extracted_data = []
    batch_size = 10 
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    clean_list = [str(t).strip() for t in text_list if len(str(t).strip()) > 2]
    total_batches = math.ceil(len(clean_list) / batch_size)

    for i in range(0, len(clean_list), batch_size):
        batch = clean_list[i : i + batch_size]
        batch_str = "\n---\n".join([f"Respondent {idx+1}: {txt}" for idx, txt in enumerate(batch)])
        
        prompt = f"""
        Extract all psychosocial factors (SF, PF, PR) based on Petrič (2025) model.
        Analyze each respondent separately. Units: At, St, So, PS, IP, HB.
        Data: {batch_str}
        Return ONLY a JSON list of objects. No text before or after.
        Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label"}} ]
        """
        
        try:
            response = model.generate_content(prompt)
            factors = clean_ai_json(response.text)
            if factors:
                extracted_data.extend(factors)
        except Exception as e:
            st.warning(f"Težava pri paketu {i//batch_size + 1}: {e}")
        
        progress_bar.progress(((i // batch_size) + 1) / total_batches)
        status_text.text(f"Analiza paketa {(i // batch_size) + 1} od {total_batches}...")
        time.sleep(4) # Premor za stabilnost
            
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

    if st.button("ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Vnesite API ključ.")
        else:
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

                val = (Fo_SF * Fo_PR) / Fo_PF
                sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
                
                w_ls = (2500 * sigma_m) / 90
                w_eu = 2500 - w_ls

                st.balloons()
                st.header(f"Zaznanih dejavnikov: {len(factors_df)}")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Stresna moč (σ)", f"{sigma_m:.2f} °S")
                m2.metric("Učinkovitost (η)", f"{((w_eu/2500)*100):.1f} %")
                m3.metric("Stresorjev (fv_sf)", fv_sf)

                st.plotly_chart(px.histogram(factors_df, x='enota', color='tip', barmode='group'))
                st.dataframe(factors_df)
