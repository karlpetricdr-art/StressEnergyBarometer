import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re
import time

# 1. Osnovna konfiguracija
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Uporabljamo preverjen model gemini-1.5-flash.")

# --- MATEMATIČNA LOGIKA (Tvoje enačbe 12-39) ---
def izracunaj_rezultate(factors_df, No):
    def get_F_factor(type_code):
        subset = factors_df[factors_df['tip'].str.contains(type_code, na=False, case=False)]
        fv = len(subset)
        frv = subset['opis'].nunique()
        if fv == 0: return 0.05
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10

    F_sf = get_F_factor('SF')
    F_pf = get_F_factor('PF')
    F_pr = get_F_factor('PR')

    if F_pf <= 0: F_pf = 0.32
    
    # Enačba 27
    razmerje = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(razmerje))))
    
    # Enačba 38-39
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    eta = (w_eu / 2500) * 100
    return sigma, w_eu, eta, F_sf, F_pf, F_pr

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        df_in = pd.read_excel(uploaded_file)
        text_data = df_in.iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        df_in = pd.read_csv(uploaded_file)
        text_data = df_in.iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    st.write(f"Zaznanih odgovorov: {len(text_data)}")

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Vnesite API ključ!")
        else:
            try:
                genai.configure(api_key=api_key)
                # Uporabimo točno to ime, ki je včeraj delovalo
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                extracted_factors = []
                # Analiziramo v paketih po 50 (varno za kvoto in natančno)
                batch_size = 50
                pb = st.progress(0)
                
                for i in range(0, len(text_data), batch_size):
                    batch = text_data[i : i + batch_size]
                    batch_text = "\n".join([f"- {t}" for t in batch])
                    
                    prompt = f"""
                    Analiziraj spodnjih 50 izjav respondentov. 
                    Iz VSEH stavkov izlušči VSE psychosocialne dejavnike po modelu Petrič (2025).
                    Tipi: SF, PF, PR. Enotne kategorije: At, St, So, PS, IP, HB.
                    Vrni IZKLJUČNO JSON seznam.
                    Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label"}} ]
                    
                    Izjave:
                    {batch_text}
                    """
                    
                    response = model.generate_content(prompt)
                    # Čiščenje JSON-a
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if match:
                        data_json = json.loads(match.group())
                        extracted_factors.extend(data_json)
                    
                    pb.progress(min(1.0, (i + batch_size) / len(text_data)))
                    time.sleep(2) # Premor za stabilnost

                if extracted_factors:
                    f_df = pd.DataFrame(extracted_factors)
                    sigma, we, et, f_sf, f_pf, f_pr = izracunaj_rezultate(f_df, len(text_data))

                    st.balloons()
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Moč stresa (σ)", f"{sigma:.2f} °S")
                    col2.metric("Učinkovitost (η)", f"{et:.2f} %")
                    col3.metric("Dejavnikov zaznanih", len(f_df))

                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                    st.write("### Seznam vseh izluščenih dejavnikov:")
                    st.dataframe(f_df)
                else:
                    st.error("AI ni vrnil podatkov. Poskusite še enkrat.")

            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
