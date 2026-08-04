import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import json
import re

# 1. Osnovne nastavitve
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Uporabljamo model: gemini-1.5-flash")

def clean_ai_json(raw_text):
    """Izlušči JSON iz odgovora AI."""
    try:
        text = re.sub(r'```json|```', '', raw_text).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None

def run_multi_factor_analysis(text_list, api_key):
    # Konfiguracija API-ja
    genai.configure(api_key=api_key)
    
    # Ročna določitev modela - gemini-1.5-flash je trenutno najbolj stabilen
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Napaka pri povezavi z modelom: {e}")
        return pd.DataFrame(), [str(e)]
    
    extracted_data = []
    debug_logs = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Filtriramo samo uporabno besedilo
    clean_list = [t for t in text_list if len(str(t).strip()) > 2]
    
    for i, text in enumerate(clean_list):
        prompt = f"""
        Instructions: Extract all psychosocial factors based on Petrič (2025).
        Return ONLY a JSON list. 
        Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label"}} ]
        Text: "{text}"
        """
        
        try:
            # Klic modela
            response = model.generate_content(prompt)
            factors = clean_ai_json(response.text)
            
            if factors:
                for f in factors:
                    if all(k in f for k in ('tip', 'enota', 'opis')):
                        extracted_data.append(f)
            else:
                debug_logs.append(f"Respondent {i+1}: AI ni vrnil JSON-a. Odgovor: {response.text[:50]}")
                
        except Exception as e:
            debug_logs.append(f"Respondent {i+1}: {str(e)}")
        
        # Posodobitev vmesnika
        progress_bar.progress((i + 1) / len(clean_list))
        status_text.text(f"Analiziram respondenta {i+1} od {len(clean_list)}...")
        
        # Rate limit za free ključ (15 RPM)
        time.sleep(4.1) # Povečan premor za varnost
            
    return pd.DataFrame(extracted_data), debug_logs

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        text_data = pd.read_excel(uploaded_file).iloc[:, 0].astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        text_data = pd.read_csv(uploaded_file).iloc[:, 0].astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = [line.strip() for line in content.splitlines() if line.strip()]

    st.write(f"Zaznanih vrstic: {len(text_data)}")

    if st.button("ZAŽENI GLOBOKO ANALIZO"):
        if not api_key:
            st.error("Prosim, vnesite API ključ.")
        else:
            with st.spinner("AI razčlenjuje stavke... to bo trajalo nekaj minut."):
                factors_df, logs = run_multi_factor_analysis(text_data, api_key)
            
            if not factors_df.empty:
                No = len(text_data)
                
                def get_metrics(type_code):
                    subset = factors_df[factors_df['tip'].str.contains(type_code, na=False)]
                    fv = len(subset)
                    frv = subset['opis'].nunique()
                    rho = fv / No
                    Co = fv / frv if frv > 0 else 1
                    return (Co * rho) / 10, fv, frv

                Fo_SF, fv_sf, frv_sf = get_metrics('SF')
                Fo_PF, fv_pf, frv_pf = get_metrics('PF')
                Fo_PR, fv_pr, frv_pr = get_metrics('PR')

                # Default vrednosti po modelu (če ni podatkov v datoteki)
                if Fo_PF <= 0: Fo_PF = 0.32
                if Fo_PR <= 0: Fo_PR = 0.25

                # Izračun stresne moči
                try:
                    val = (Fo_SF * Fo_PR) / Fo_PF
                    sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
                except:
                    sigma_m = 0

                # Energija
                w_ls = (2500 * sigma_m) / 90
                w_eu = 2500 - w_ls

                # PRIKAZ
                st.balloons()
                st.header(f"Analiza zaključena: {len(factors_df)} dejavnikov")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Stresna moč (σ)", f"{sigma_m:.2f} °S")
                m2.metric("Učinkovitost (η)", f"{((w_eu/2500)*100):.1f} %")
                m3.metric("Zaznanih stresorjev (fv)", fv_sf)

                st.plotly_chart(px.histogram(factors_df, x='enota', color='tip', barmode='group'))
                st.write("### Seznam vseh izluščenih dejavnikov:")
                st.dataframe(factors_df)
            
            if logs:
                with st.expander("Diagnostika (Debug Log)"):
                    for log in logs:
                        st.text(log)
