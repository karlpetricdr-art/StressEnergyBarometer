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
    st.info("Način: Single-Shot (vsi podatki v enem klicu)")

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
    # Funkcija za izračun realnega faktorja F
    def get_F(fv, frv):
        if No <= 0: return 0
        rho = fv / No
        co = fv / frv if frv > 0 else 1
        return (co * rho) / 10
    
    F_sf = get_F(fv_sf, frv_sf)
    F_pf = get_F(fv_pf, frv_pf)
    F_pr = get_F(fv_pr, frv_pr)
    
    # Varovalka: Fo_PF ne sme biti 0 (Enačba 27)
    if F_pf <= 0: F_pf = 0.32
    
    # Stresna moč sigma
    inside_sqrt = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(inside_sqrt))))
    
    # Poraba energije (Enačba 38-39)
    # WI = 2500 kcal (vhodna energija)
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

    st.success(f"Naloženo {len(data)} vrstic z odgovori.")

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Prosim, vnesite API ključ v stransko vrstico.")
        else:
            try:
                # KONFIGURACIJA
                genai.configure(api_key=api_key)
                
                # Model 'gemini-1.5-flash' brez dodatnih poti (najbolj stabilno)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Priprava podatkov (Single-Shot)
                all_text = "\n".join([f"Vnos {i+1}: {txt}" for i, txt in enumerate(data)])
                
                prompt = f"""
                Analyze the following {len(data)} responses and extract ALL psychosocial factors based on Petrič (2025).
                For each mention, identify:
                - tip: SF (stressor), PF (positive factor), PR (suggestion/proposal).
                - enota: At (physical), St (performance), So (social), PS (partial social), IP (individual psych), HB (health).
                - opis: short standardized label.

                Return ONLY a valid JSON list.
                Format: [{{ "tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "label" }}]

                Data to analyze:
                {all_text}
                """
                
                with st.spinner("AI analizira celotno datoteko hkrati..."):
                    response = model.generate_content(prompt)
                    factors = extract_json(response.text)
                
                if factors:
                    f_df = pd.DataFrame(factors)
                    
                    # Izračun frekvenc fv in unikatnih mnenj frv
                    def get_metrics(t):
                        sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                        return len(sub), max(1, sub['opis'].nunique())

                    fv_sf, frv_sf = get_metrics('SF')
                    fv_pf, frv_pf = get_metrics('PF')
                    fv_pr, frv_pr = get_metrics('PR')

                    # Matematični izračun
                    s, we, et = calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, len(data))

                    # PRIKAZ REZULTATOV
                    st.balloons()
                    st.header("Končni izračun stresne moči")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                    c2.metric("Učinkovitost (η)", f"{et:.2f} %")
                    c3.metric("Dejanska poraba (W_EU)", f"{int(we)} kcal")

                    # Grafikon
                    st.subheader("Porazdelitev dejavnikov po enotah")
                    fig = px.histogram(f_df, x='enota', color='tip', barmode='group', 
                                       category_orders={"enota": ["At", "St", "So", "PS", "IP", "HB"]})
                    st.plotly_chart(fig)
                    
                    st.write("### Podroben seznam vseh zaznanih dejavnikov:")
                    st.dataframe(f_df)
                else:
                    st.error("AI ni uspel vrniti strukturiranih podatkov. Poskusite še enkrat.")
                    st.text("Surovi odgovor AI:")
                    st.write(response.text[:500])
                    
            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
                st.info("Če vidite napako 404, preverite, če je vaš API ključ pravilno aktiviran v Google AI Studio.")
