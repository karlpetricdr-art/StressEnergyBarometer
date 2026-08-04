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

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    if api_key:
        st.success("API ključ vnesen.")
    else:
        st.warning("Vnesite API ključ za začetek.")

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
    genai.configure(api_key=api_key)
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if '1.5-flash' in m.lower():
                return genai.GenerativeModel(m)
        return genai.GenerativeModel(models[0]) if models else None
    except Exception as e:
        st.error(f"Napaka pri pridobivanju modela: {e}")
        return None

# --- NALAGANJE DATOTEKE ---
st.subheader("1. Korak: Naložite datoteko z odgovori")
uploaded_file = st.file_uploader("Izberite datoteko (.xlsx, .csv ali .txt)", type=['xlsx', 'csv', 'txt'])

text_data = []

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df_in = pd.read_excel(uploaded_file)
            text_data = df_in.iloc[:, 0].dropna().astype(str).tolist()
        elif uploaded_file.name.endswith('.csv'):
            df_in = pd.read_csv(uploaded_file)
            text_data = df_in.iloc[:, 0].dropna().astype(str).tolist()
        else:
            content = uploaded_file.read().decode("utf-8")
            text_data = [line.strip() for line in content.splitlines() if len(line.strip()) > 2]
        
        if text_data:
            st.success(f"✅ Datoteka uspešno naložena! Zaznanih je {len(text_data)} odgovorov.")
            st.subheader("2. Korak: Zaženite analizo")
        else:
            st.error("Datoteka je prazna ali nima berljivega besedila.")
    except Exception as e:
        st.error(f"Napaka pri branju datoteke: {e}")

# --- GUMB ZA ANALIZO ---
# Gumb se prikaže le, če so podatki pripravljeni
if len(text_data) > 0:
    if st.button("🚀 ZAŽENI GLOBOKO ANALIZO"):
        if not api_key:
            st.error("Niste vnesli API ključa v stransko vrstico!")
        else:
            model = get_working_model(api_key)
            if model:
                st.info(f"Analiza se izvaja z modelom: {model.model_name}. Prosimo, počakajte...")
                
                extracted_data = []
                batch_size = 10 
                clean_list = text_data
                total_batches = math.ceil(len(clean_list) / batch_size)
                
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i in range(0, len(clean_list), batch_size):
                    batch = clean_list[i : i + batch_size]
                    batch_str = "\n---\n".join([f"R{idx+1}: {txt}" for idx, txt in enumerate(batch)])
                    
                    prompt = f"""
                    Extract psychosocial factors (SF, PF, PR) based on Petrič (2025) model.
                    Analyze each respondent (R1, R2...) separately. Units: At, St, So, PS, IP, HB.
                    Return ONLY a JSON list of objects. No intro text.
                    Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label"}} ]
                    Data: {batch_str}
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        factors = clean_ai_json(response.text)
                        if factors:
                            extracted_data.extend(factors)
                    except Exception as e:
                        st.warning(f"Težava pri paketu {i//batch_size + 1}: {e}")
                    
                    current_idx = (i // batch_size) + 1
                    progress_bar.progress(current_idx / total_batches)
                    status_text.text(f"Obdelava: {current_idx} / {total_batches} paketov...")
                    time.sleep(4) # Rate limit protection
                
                factors_df = pd.DataFrame(extracted_data)

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
                    st.header(f"Rezultat: Zaznanih {len(factors_df)} dejavnikov")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Moč stresa (σ)", f"{sigma_m:.2f} °S")
                    m2.metric("Učinkovitost (η)", f"{((w_eu/2500)*100):.1f} %")
                    m3.metric("Število stresorjev (fv_sf)", fv_sf)

                    st.plotly_chart(px.histogram(factors_df, x='enota', color='tip', barmode='group'))
                    st.write("### Podrobna tabela izluščenih dejavnikov:")
                    st.dataframe(factors_df)
                else:
                    st.error("AI ni vrnil nobenih podatkov. Poskusite ponovno.")
