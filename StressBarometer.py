import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re

# 1. Nastavitve
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Hitra statistična analiza celotnega vzorca.")

# --- MATEMATIČNI MODEL ---
def calculate_petric_math(stats, No):
    # fv_sf, fv_pf, fv_pr so ocenjene frekvence iz AI
    f_sf = stats.get('fv_sf', 50)
    frv_sf = stats.get('frv_sf', 10)
    f_pf = stats.get('fv_pf', 50)
    frv_pf = stats.get('frv_pf', 10)
    f_pr = stats.get('fv_pr', 50)
    frv_pr = stats.get('frv_pr', 10)

    def get_F(fv, frv):
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10

    F_sf = get_F(f_sf, frv_sf)
    F_pf = get_F(f_pf, frv_pf)
    F_pr = get_F(f_pr, frv_pr)
    
    if F_pf <= 0: F_pf = 0.32
    sigma = math.degrees(math.asin(min(1.0, math.sqrt((F_sf * F_pr) / F_pf))))
    
    w_eu = 2500 - (2500 * sigma / 90)
    return sigma, w_eu, (w_eu / 2500) * 100

# --- ANALITIČNA FUNKCIJA (BREZ LIST_MODELS) ---
def run_direct_analysis(all_text, No, api_key):
    genai.configure(api_key=api_key)
    
    # Poskusimo neposredno s stabilnim imenom
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        model = genai.GenerativeModel('gemini-pro')

    prompt = f"""
    Analyze these {No} responses based on Petrič (2025) model.
    Estimate frequencies for the entire sample:
    1. fv_sf: total frequency of stress factors.
    2. frv_sf: number of unique stress factors.
    3. fv_pf: total frequency of positive factors.
    4. frv_pf: unique positive factors.
    5. fv_pr: total frequency of suggestions.
    6. frv_pr: unique suggestions.
    7. distribution: At, St, So, PS, IP, HB in %.

    Data:
    {all_text}

    Return ONLY a JSON object:
    {{
      "fv_sf": int, "frv_sf": int,
      "fv_pf": int, "frv_pf": int,
      "fv_pr": int, "frv_pr": int,
      "enote": {{"At": %, "St": %, "So": %, "PS": %, "IP": %, "HB": %}}
    }}
    """
    
    response = model.generate_content(prompt)
    match = re.search(r'\{.*\}', response.text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return None

# --- NALAGANJE ---
uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        data = [l.strip() for l in uploaded_file.read().decode("utf-8").splitlines() if len(l.strip()) > 5]

    if st.button("🚀 ZAŽENI BLISKAVICO"):
        if not api_key:
            st.error("API ključ!")
        else:
            with st.spinner("AI računa verjetnosti..."):
                # Omejimo besedilo na prvih 50.000 znakov za stabilnost
                combined_text = "\n".join(data)[:50000]
                try:
                    stats = run_direct_analysis(combined_text, len(data), api_key)
                    if stats:
                        sigma, we, et = calculate_petric_math(stats, len(data))
                        
                        st.balloons()
                        st.header(f"Rezultat: {sigma:.2f} °S")
                        
                        m1, m2 = st.columns(2)
                        m1.metric("Moč stresa (σ)", f"{sigma:.2f} °S")
                        m2.metric("Učinkovitost (η)", f"{et:.2f} %")
                        
                        enote_df = pd.DataFrame(stats['enote'].items(), columns=['Enota', '%'])
                        st.plotly_chart(px.bar(enote_df, x='Enota', y='%', color='%'))
                        st.write("### AI ocena frekvenc")
                        st.json(stats)
                    else:
                        st.error("AI ni vrnil JSON-a.")
                except Exception as e:
                    st.error(f"Sistemska napaka: {e}")
                    st.info("Če še vedno javlja 404, prosim ustvarite nov API ključ v Google AI Studio, saj je vaš trenutni očitno povezan z ukinjenim beta projektom.")
