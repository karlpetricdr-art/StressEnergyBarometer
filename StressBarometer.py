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
    st.info("Strategija: Vsi podatki v enem klicu (Single-Shot) zaradi omejitve 20/dan.")

def extract_json(text):
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: return json.loads(match.group())
    except: pass
    return []

# --- MATEMATIČNI MODEL (Enačbe 12-39) ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    rho_sf, Co_sf = fv_sf/No, (fv_sf/frv_sf if frv_sf > 0 else 1)
    rho_pf, Co_pf = fv_pf/No, (fv_pf/frv_pf if frv_pf > 0 else 1)
    rho_pr, Co_pr = fv_pr/No, (fv_pr/frv_pr if frv_pr > 0 else 1)
    
    F_sf = (Co_sf * rho_sf) / 10
    F_pf = (Co_pf * rho_pf) / 10
    F_pr = (Co_pr * rho_pr) / 10
    
    if F_pf <= 0: F_pf = 0.32 # Konstanta iz članka, če ni podatkov
    
    val = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    
    W_I = 2500
    w_ls = (W_I * sigma) / 90
    w_eu = W_I - w_ls
    eta = (w_eu / W_I) * 100
    return sigma, w_eu, w_ls, eta

uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        data = [l.strip() for l in uploaded_file.read().decode("utf-8").splitlines() if len(l.strip()) > 2]

    st.success(f"Pripravljeno {len(data)} odgovorov.")

    if st.button("🚀 ZAŽENI ENKRATNO ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ.")
        else:
            try:
                genai.configure(api_key=api_key)
                # Uporabimo najbolj stabilno ime modela
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Združimo vse odgovore v en velik blok besedila
                all_text = "\n".join([f"ID_{i}: {txt}" for i, txt in enumerate(data)])
                
                prompt = f"""
                Analiziraj teh {len(data)} izjav po modelu Petrič (2025). 
                Za vsako izjavo izlušči dejavnike in jih vrni kot EN skupen JSON seznam.
                Format: [{{ "tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label" }}]
                
                Podatki:
                {all_text}
                """
                
                with st.spinner("Pošiljam vse podatke v enem klicu (Single-Shot)..."):
                    response = model.generate_content(prompt)
                    factors = extract_json(response.text)
                
                if factors:
                    f_df = pd.DataFrame(factors)
                    def get_f(t):
                        sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                        return len(sub), max(1, sub['opis'].nunique())

                    fv_sf, frv_sf = get_f('SF')
                    fv_pf, frv_pf = get_f('PF')
                    fv_pr, frv_pr = get_f('PR')

                    s, we, wl, et = calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, len(data))

                    st.balloons()
                    st.header("Analiza zaključena!")
                    st.metric("Moč stresa (σ)", f"{s:.2f} °S")
                    st.metric("Učinkovitost (η)", f"{et:.2f} %")
                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                    st.dataframe(f_df)
                else:
                    st.error("AI ni vrnil pravilnega formata. Poskusite še enkrat.")
                    st.text("Odgovor AI:")
                    st.write(response.text[:500])
                    
            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
