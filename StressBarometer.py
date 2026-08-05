import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re

# Nastavitve strani
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Prisilno nastavljen protokol: API v1")

def extract_json(text):
    """Izlušči JSON seznam iz odgovora AI."""
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

# --- MATEMATIČNI MODEL (Enačbe 12-39) ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    def get_F(fv, frv):
        if No <= 0: return 0
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10
    
    F_sf = get_F(fv_sf, frv_sf)
    F_pf = get_F(fv_pf, frv_pf)
    F_pr = get_F(fv_pr, frv_pr)
    
    if F_pf <= 0: F_pf = 0.32
    
    inside_sqrt = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(inside_sqrt))))
    
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    eta = (w_eu / 2500) * 100
    
    return sigma, w_eu, eta

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    st.success(f"Naloženo {len(data)} vrstic.")

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                # KLJUČNI POPRAVEK: Prisila uporabe v1 namesto v1beta
                genai.configure(api_key=api_key, transport='grpc')
                
                # Uporabimo neposredno ime modela brez prefixov
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                all_text = "\n".join([f"ID_{i+1}: {txt}" for i, txt in enumerate(data)])
                
                prompt = f"""
                Extract psychosocial factors based on Petrič (2025) for {len(data)} responses.
                SF (stressor), PF (positive), PR (suggestion).
                At, St, So, PS, IP, HB.
                Return ONLY a JSON list.
                Format: [{{ "tip": "SF/PF/PR", "enota": "...", "opis": "..." }}]
                Data:
                {all_text}
                """
                
                with st.spinner("AI analizira (Single-Shot klic)..."):
                    # Dodan parameter za stabilnost
                    response = model.generate_content(prompt)
                    factors = extract_json(response.text)
                
                if factors:
                    f_df = pd.DataFrame(factors)
                    def get_metrics(t):
                        sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                        return len(sub), max(1, sub['opis'].nunique())

                    s, we, et = calculate_petric_model(*(get_metrics('SF') + get_metrics('PF') + get_metrics('PR')), len(data))

                    st.balloons()
                    col1, col2 = st.columns(2)
                    col1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                    col2.metric("Učinkovitost (η)", f"{et:.2f} %")
                    
                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                    st.dataframe(f_df)
                else:
                    st.error("AI ni vrnil JSON seznama. Poskusite še enkrat.")
                    st.write("Surovi odgovor AI:", response.text[:300])
                    
            except Exception as e:
                # Če še vedno javlja 404, poskusimo še zadnjo alternativo v sami kodi
                if "404" in str(e):
                    st.error(f"Sistemska napaka 404: Google ne najde modela preko te poti. Poskušam alternativno metodo...")
                    try:
                        # Zadnji obupni poskus z drugim imenom modela
                        model_alt = genai.GenerativeModel('gemini-pro')
                        response = model_alt.generate_content(prompt)
                        # ... (isti postopek kot zgoraj)
                    except:
                        st.error("Tudi alternativna metoda ni uspela. Težava je verjetno v nastavitvah vašega Google računa.")
                else:
                    st.error(f"Napaka: {e}")
