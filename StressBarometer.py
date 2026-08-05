import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Prisilno nastavljen model: gemini-1.5-flash")

def extract_json(text):
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: return json.loads(match.group())
    except: pass
    return []

# --- MATEMATIČNI MODEL ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    def get_F(fv, frv):
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10
    
    F_sf = get_F(fv_sf, frv_sf)
    F_pf = get_F(fv_pf, frv_pf)
    F_pr = get_F(fv_pr, frv_pr)
    
    if F_pf <= 0: F_pf = 0.32 # Default konstanta
    
    # Izračun stresne moči
    val = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    
    # Energija (2500 kcal je vhod)
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    return sigma, w_eu, (w_eu / 2500) * 100

uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    st.success(f"Naloženo {len(data)} vrstic.")

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                # 1. Konfiguracija
                genai.configure(api_key=api_key)
                
                # 2. PRISILNA IZBIRA STABILNEGA MODELA
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 3. Priprava vseh podatkov v enem bloku (Single-Shot)
                all_text = "\n".join([f"Vnos {i+1}: {txt}" for i, txt in enumerate(data)])
                
                prompt = f"""
                Extract ALL psychosocial factors (SF, PF, PR) as JSON list. 
                Categories: At, St, So, PS, IP, HB. 
                Format: [{{ "tip": "SF/PF/PR", "enota": "...", "opis": "..." }}]
                Data:
                {all_text}
                """
                
                with st.spinner("AI analizira vseh 215 odgovorov hkrati..."):
                    response = model.generate_content(prompt)
                    factors = extract_json(response.text)
                
                if factors:
                    f_df = pd.DataFrame(factors)
                    def get_f(t):
                        sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                        return len(sub), max(1, sub['opis'].nunique())

                    s, we, et = calculate_petric_model(*(get_f('SF') + get_f('PF') + get_f('PR')), len(data))

                    st.balloons()
                    c1, c2 = st.columns(2)
                    c1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                    c2.metric("Učinkovitost (η)", f"{et:.2f} %")
                    
                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group', title="Analiza po enotah"))
                    st.write("### Zaznani dejavniki vseh respondentov:")
                    st.dataframe(f_df)
                else:
                    st.error("AI ni vrnil podatkov. Poskusite še enkrat.")
                    st.text("AI odgovor (za debug):")
                    st.write(response.text[:300])
                    
            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
