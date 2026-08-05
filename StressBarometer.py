import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re

# 1. Nastavitve strani
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Strategija: Real-time izračun (Single-Shot klic)")

def extract_json(text):
    """Varno izlušči JSON seznam iz odgovora AI."""
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

# --- MATEMATIČNI MODEL (Enačbe 12-39 iz članka) ---
def calculate_petric_model(factors_df, No):
    # Priprava tabel za SF, PF in PR
    def get_F_factor(type_code):
        subset = factors_df[factors_df['tip'].str.contains(type_code, na=False, case=False)]
        fv = len(subset) # fv (Enačba 12)
        frv = subset['opis'].nunique() # frv (Enačba 18)
        
        if fv == 0: return 0.05 # Minimalna vrednost, če ni podatkov
        
        rho = fv / No # Gostota (Enačba 12/14)
        Co = fv / frv if frv > 0 else 1 # Kompleksnost (Enačba 18/20)
        
        # Realni faktor Fo (Enačba 24/25/26) - Ct=1, rhot=10
        return (Co * rho) / 10

    F_sf = get_F_factor('SF')
    F_pf = get_F_factor('PF')
    F_pr = get_F_factor('PR')

    # Varovalka za deljenje z 0 (Enačba 27)
    if F_pf <= 0: F_pf = 0.32
    
    # Izračun celotne stresne moči sigma (Enačba 27)
    razmerje = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(razmerje))))
    
    # Poraba energije (Enačba 38-39)
    # WI = 2500 kcal
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    eta = (w_eu / 2500) * 100
    
    return sigma, w_eu, eta, F_sf, F_pf, F_pr

# --- NALAGANJE PODATKOV ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    st.success(f"Naloženih {len(data)} surovih odgovorov.")

    if st.button("🚀 ZAŽENI REALNI IZRAČUN"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                genai.configure(api_key=api_key)
                
                # Dinamično iskanje modela (Rešitev za 404 v1beta)
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = next((m for m in available if "1.5-flash" in m), available[0])
                
                st.write(f"Uporabljam model: `{model_name}`")
                model = genai.GenerativeModel(model_name)

                # Priprava besedila za AI (Single-Shot)
                all_text = "\n".join([f"ID_{i}: {txt}" for i, txt in enumerate(data)])
                
                prompt = f"""
                Analiziraj teh {len(data)} izjav po modelu Petrič (2025). 
                Iz vsake izjave izlušči VSE dejavnike in jih vrni kot EN JSON seznam.
                Tipi: SF (stresor), PF (pozitiven), PR (predlog).
                Enotne kategorije: At, St, So, PS, IP, HB.
                
                Vrni IZKLJUČNO JSON seznam.
                Format: [{{ "tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "standardizirana labela" }}]
                
                Podatki:
                {all_text}
                """
                
                with st.spinner("AI analizira vseh 215 odgovorov hkrati..."):
                    response = model.generate_content(prompt)
                    raw_factors = extract_json(response.text)
                
                if raw_factors:
                    f_df = pd.DataFrame(raw_factors)
                    
                    # IZRAČUN
                    sigma, we, et, f_sf, f_pf, f_pr = calculate_petric_model(f_df, len(data))

                    # PRIKAZ REZULTATOV
                    st.balloons()
                    st.header("Realni rezultati raziskave")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Izračunana moč stresa (σ)", f"{sigma:.2f} °S")
                    c2.metric("Učinkovitost energije (η)", f"{et:.2f} %")
                    c3.metric("Dejanska poraba (W_EU)", f"{int(we)} kcal")

                    # VIZUALIZACIJA
                    st.subheader("Struktura dejavnikov v organizaciji")
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        fig_hist = px.histogram(f_df, x='enota', color='tip', barmode='group',
                                               title="Število dejavnikov po enotah",
                                               category_orders={"enota": ["At", "St", "So", "PS", "IP", "HB"]},
                                               color_discrete_map={'SF':'#EF553B', 'PF':'#00CC96', 'PR':'#636EFA'})
                        st.plotly_chart(fig_hist)
                    
                    with col_right:
                        # Prikaz realnih faktorjev F_o
                        f_data = {'Tip': ['F_SF (Stresorji)', 'F_PF (Pozitivni)', 'F_PR (Predlogi)'],
                                  'Vrednost': [f_sf, f_pf, f_pr]}
                        fig_f = px.bar(f_data, x='Tip', y='Vrednost', title="Vrednosti realnih faktorjev (Fo)")
                        st.plotly_chart(fig_f)

                    st.subheader("Podroben seznam vseh izluščenih dejavnikov")
                    st.dataframe(f_df)
                else:
                    st.error("AI ni uspel vrniti strukturiranih podatkov. Poskusite ponovno čez 1 minuto.")
                    st.write("Debug (AI odgovor):", response.text[:500])

            except Exception as e:
                st.error(f"Sistemska napaka: {e}")
