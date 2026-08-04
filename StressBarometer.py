import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import json
import re

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025) - Diagnostična Analiza")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Če analiza ne uspe, poglejte 'Debug log' na dnu strani.")

def clean_ai_json(raw_text):
    """Izlušči JSON seznam iz besedila, ki ga vrne AI."""
    try:
        # Odstrani markdown oznake ```json in ```
        text = re.sub(r'```json|```', '', raw_text).strip()
        # Poišči vse med [ in ]
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        st.warning(f"Napaka pri branju JSON-a: {e}")
    return None

def run_multi_factor_analysis(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    extracted_data = []
    debug_logs = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Filtriramo samo dejansko vsebino
    clean_list = [t for t in text_list if len(str(t).strip()) > 2]
    
    if not clean_list:
        st.error("Datoteka ne vsebuje uporabnega besedila.")
        return pd.DataFrame(), []

    for i, text in enumerate(clean_list):
        prompt = f"""
        Instructions: Act as an expert organizational psychologist.
        Analyze the text and extract ALL psychosocial stress factors, positive factors, and suggestions.
        Based on Petrič (2025) model.
        Return ONLY a JSON list of objects. No intro, no outro.
        Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "short label"}} ]
        Text to analyze: "{text}"
        """
        
        try:
            response = model.generate_content(prompt)
            factors = clean_ai_json(response.text)
            
            if factors:
                for f in factors:
                    if all(k in f for k in ('tip', 'enota', 'opis')):
                        extracted_data.append(f)
            else:
                debug_logs.append(f"Respondent {i+1} - AI odgovor: {response.text}")
                
        except Exception as e:
            debug_logs.append(f"Respondent {i+1} - Sistemska napaka: {str(e)}")
            continue
        
        # Posodobitev vmesnika
        progress_bar.progress((i + 1) / len(clean_list))
        status_text.text(f"Obdelava respondenta {i+1} od {len(clean_list)}...")
        
        # Free-tier rate limit protection
        if (i+1) % 10 == 0: time.sleep(1.5)
            
    return pd.DataFrame(extracted_data), debug_logs

uploaded_file = st.file_uploader("Naložite datoteko z odgovori (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    # Branje datoteke
    if uploaded_file.name.endswith('.xlsx'):
        df_input = pd.read_excel(uploaded_file)
        text_data = df_input.iloc[:, 0].astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        df_input = pd.read_csv(uploaded_file)
        text_data = df_input.iloc[:, 0].astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = [line.strip() for line in content.splitlines() if line.strip()]

    st.write(f"Zaznanih vrstic z besedilom: {len(text_data)}")

    if st.button("ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Prosim, vnesite API ključ.")
        else:
            with st.spinner("AI analizira odgovore..."):
                factors_df, logs = run_multi_factor_analysis(text_data, api_key)
            
            if not factors_df.empty:
                # IZRAČUNI
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

                # Default vrednosti po modelu (če ni podatkov)
                if Fo_PF <= 0: Fo_PF = 0.32
                if Fo_PR <= 0: Fo_PR = 0.25

                # Stresna moč
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
                m2.metric("Učinkovitost (η)", f"{(w_eu/2500)*100:.1f} %")
                m3.metric("Izguba energije", f"{int(w_ls)} kcal")

                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(px.histogram(factors_df, x='enota', color='tip', barmode='group', title="Dejavniki po enotah"))
                with c2:
                    st.write("### Seznam dejavnikov (vzorčni pregled)")
                    st.dataframe(factors_df.head(20))
            
            if logs:
                with st.expander("Poglej diagnostične podatke (Debug Log)"):
                    for log in logs:
                        st.text(log)
