import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re
import time

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

def calculate_metrics(factors_df, No):
    def get_F(type_code):
        subset = factors_df[factors_df['tip'].str.contains(type_code, na=False, case=False)]
        fv = len(subset)
        frv = subset['opis'].nunique()
        if fv == 0: return 0.05
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10

    F_sf = get_F('SF')
    F_pf = get_F('PF')
    F_pr = get_F('PR')
    if F_pf <= 0: F_pf = 0.32
    
    sigma = math.degrees(math.asin(min(1.0, math.sqrt((F_sf * F_pr) / F_pf))))
    w_eu = 2500 - (2500 * sigma / 90)
    return sigma, w_eu, (w_eu / 2500) * 100

uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                all_extracted = []
                # Obdelava v paketih po 30, da AI ne pozabi na dolge stavke
                batch_size = 30
                pb = st.progress(0)
                
                for i in range(0, len(data), batch_size):
                    batch = data[i : i + batch_size]
                    batch_text = "\n".join([f"- {t}" for t in batch])
                    
                    # PROMPT, ki prisili AI v ekstrakcijo VEČ dejavnikov iz enega stavka
                    prompt = f"""
                    Analiziraj spodnje izjave. Iz VSAKEGA stavka izlušči VSE psychosocialne dejavnike.
                    Če respondent v enem stavku omenja več težav, jih izlušči ločeno.
                    Model: Petrič (2025). Tipi: SF, PF, PR. Enotne kategorije: At, St, So, PS, IP, HB.
                    Vrni IZKLJUČNO JSON seznam.
                    Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "standardizirana labela"}} ]
                    
                    Izjave:
                    {batch_text}
                    """
                    
                    response = model.generate_content(prompt)
                    res_json = extract_json(response.text)
                    all_extracted.extend(res_json)
                    
                    pb.progress(min(1.0, (i + batch_size) / len(data)))
                    time.sleep(2)

                if all_extracted:
                    f_df = pd.DataFrame(all_extracted)
                    sigma, we, et = calculate_metrics(f_df, len(data))

                    st.balloons()
                    st.metric("Moč stresa (σ)", f"{sigma:.2f} °S")
                    st.metric("Učinkovitost (η)", f"{et:.2f} %")
                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                    st.dataframe(f_df)
                else:
                    st.error("AI ni našel dejavnikov.")

            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
