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

def extract_json(text):
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: return json.loads(match.group())
    except: pass
    return []

# --- MATEMATIČNI MODEL ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    def get_rho_co(fv, frv):
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10
    
    F_sf = get_rho_co(fv_sf, frv_sf)
    F_pf = get_rho_co(fv_pf, frv_pf)
    F_pr = get_rho_co(fv_pr, frv_pr)
    
    if F_pf <= 0: F_pf = 0.32
    sigma = math.degrees(math.asin(min(1.0, math.sqrt((F_sf * F_pr) / F_pf))))
    
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    return sigma, w_eu, (w_eu / 2500) * 100

uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        data = [l.strip() for l in uploaded_file.read().decode("utf-8").splitlines() if len(l.strip()) > 2]

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                genai.configure(api_key=api_key)
                
                # DINAMIČNA IZBIRA MODELA (Rešitev za 404)
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Izberemo prvi flash model, če obstaja, sicer prvega na seznamu
                model_name = next((m for m in available if 'flash' in m), available[0])
                st.info(f"Povezava vzpostavljena preko: `{model_name}`")
                
                model = genai.GenerativeModel(model_name)
                all_text = "\n".join([f"R{i+1}: {txt}" for i, txt in enumerate(data)])
                
                prompt = f"""Extract ALL psychosocial factors (SF/PF/PR) for these {len(data)} responses as a JSON list. 
                Categories: At, St, So, PS, IP, HB. 
                Format: [{{ "tip": "SF/PF/PR", "enota": "...", "opis": "..." }}]
                Data: {all_text}"""
                
                with st.spinner("AI analizira..."):
                    response = model.generate_content(prompt)
                    factors = extract_json(response.text)
                
                if factors:
                    f_df = pd.DataFrame(factors)
                    def get_f(t):
                        sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                        return len(sub), max(1, sub['opis'].nunique())

                    s, we, et = calculate_petric_model(*(get_f('SF') + get_f('PF') + get_f('PR')), len(data))

                    st.balloons()
                    col1, col2 = st.columns(2)
                    col1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                    col2.metric("Učinkovitost (η)", f"{et:.2f} %")
                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                else:
                    st.error("AI ni vrnil JSON-a. Poskusite ponovno.")
                    
            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
