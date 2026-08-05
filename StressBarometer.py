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
    st.info("Način: Single-Shot (vsi podatki hkrati)")

def extract_json_from_text(text):
    try:
        # Izlušči vsebino med oglatimi oklepaji
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

# --- MATEMATIČNI MODEL (Enačbe 12-39) ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    rho_sf, Co_sf = fv_sf/No, (fv_sf/frv_sf if frv_sf > 0 else 1)
    rho_pf, Co_pf = fv_pf/No, (fv_pf/frv_pf if frv_pf > 0 else 1)
    rho_pr, Co_pr = fv_pr/No, (fv_pr/frv_pr if frv_pr > 0 else 1)
    
    F_sf = (Co_sf * rho_sf) / 10
    F_pf = (Co_pf * rho_pf) / 10
    F_pr = (Co_pr * rho_pr) / 10
    
    if F_pf <= 0: F_pf = 0.32 # Default iz članka
    
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

    st.success(f"Pripravljeno: {len(data)} respondentov.")

    if st.button("🚀 ZAŽENI ENKRATNO ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                genai.configure(api_key=api_key)
                
                # FIKSNA IZBIRA MODELA - brez ugibanja
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Priprava besedila
                input_text = "\n".join([f"R{i+1}: {txt}" for i, txt in enumerate(data)])
                
                prompt = f"""
                Analyze all {len(data)} responses and extract ALL psychosocial factors (SF, PF, PR) 
                based on the Petrič (2025) model.
                Categories: At, St, So, PS, IP, HB.
                Return ONLY a JSON list of objects.
                Format: [ {{ "tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label" }} ]
                
                Data:
                {input_text}
                """
                
                with st.spinner("AI analizira... prosim počakajte na rezultate."):
                    response = model.generate_content(prompt)
                    all_factors = extract_json_from_text(response.text)
                
                if all_factors:
                    f_df = pd.DataFrame(all_factors)
                    
                    def get_f(t):
                        # Prilagodljivo iskanje tipa (SF, PF ali PR)
                        sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                        return len(sub), max(1, sub['opis'].nunique())

                    fv_sf, frv_sf = get_f('SF')
                    fv_pf, frv_pf = get_f('PF')
                    fv_pr, frv_pr = get_f('PR')

                    s, we, wl, et = calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, len(data))

                    st.balloons()
                    st.header("Končni rezultati")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                    c2.metric("Učinkovitost (η)", f"{et:.2f} %")
                    c3.metric("Izguba (W_LS)", f"{int(wl)} kcal")

                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                    st.dataframe(f_df)
                else:
                    st.error("AI ni vrnil JSON podatkov. Poskusite še enkrat.")
                    st.write("Debug (AI odgovor):", response.text[:500])
                        
            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
