import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import json

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025) - Multi-faktor Analiza")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Model zdaj podpira ekstrakcijo več dejavnikov iz enega stavka.")

def run_multi_factor_analysis(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    extracted_data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, text in enumerate(text_list):
        # Prompt, ki zahteva ekstrakcijo vseh dejavnikov
        prompt = f"""
        Analiziraj izjavo respondenta po modelu Petrič (2025). 
        Iz besedila izlušči VSE omenjene dejavnike.
        Za vsak dejavnik določi:
        - TIP: SF (stresor), PF (pozitiven), PR (predlog).
        - ENOTO: At, St, So, PS, IP, HB.
        - POVZETEK: kratek opis dejavnika.

        Izjava: "{text}"

        Vrni izključno JSON seznam objektov, primer:
        [
          {{"tip": "SF", "enota": "At", "opis": "hrup"}},
          {{"tip": "SF", "enota": "So", "opis": "slab odnos"}}
        ]
        """
        try:
            response = model.generate_content(prompt)
            # Očistimo morebitne markdown oznake iz JSON-a
            clean_json = response.text.replace('```json', '').replace('```', '').strip()
            factors = json.loads(clean_json)
            for f in factors:
                f['respondent_id'] = i
                extracted_data.append(f)
        except:
            continue
        
        progress_bar.progress((i + 1) / len(text_list))
        status_text.text(f"Analiziram respondenta {i+1} od {len(text_list)}...")
        if (i+1) % 10 == 0: time.sleep(1)
            
    return pd.DataFrame(extracted_data)

uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'): df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
    else:
        content = uploaded_file.read().decode("utf-8")
        df = pd.DataFrame(content.splitlines(), columns=["Odgovor"])

    No = len(df)
    if st.button("ZAŽENI GLOBOKO ANALIzo"):
        if not api_key:
            st.error("Vnesite API ključ!")
        else:
            with st.spinner("AI razčlenjuje stavke na posamezne dejavnike..."):
                factors_df = run_multi_factor_analysis(df["Odgovor"].tolist(), api_key)
            
            # Izračun frekvenc po vašem modelu
            def get_metrics(type_code):
                subset = factors_df[factors_df['tip'] == type_code]
                fv = len(subset)
                frv = subset['opis'].nunique()
                # Enačba 12 & 18: rho in Co
                rho = fv / No
                Co = fv / frv if frv > 0 else 1
                return (Co * rho) / 10, fv, frv

            Fo_SF, fv_sf, frv_sf = get_metrics('SF')
            Fo_PF, fv_pf, frv_pf = get_metrics('PF')
            Fo_PR, fv_pr, frv_pr = get_metrics('PR')

            # Varovalke za minimalne vrednosti (Table 25, 26)
            if Fo_PF < 0.01: Fo_PF = 0.32
            if Fo_PR < 0.01: Fo_PR = 0.25

            # Izračun stresne moči (Enačba 27)
            val = (Fo_SF * Fo_PR) / Fo_PF
            sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
            
            # Energija
            w_ls = (2500 * sigma_m) / 90
            w_eu = 2500 - w_ls

            # PRIKAZ
            st.header(f"Rezultati analize ({len(factors_df)} zaznanih dejavnikov)")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Zaznanih Stresorjev (fv_sf)", fv_sf)
            c2.metric("Zaznanih Pozitivnih (fv_pf)", fv_pf)
            c3.metric("Zaznanih Predlogov (fv_pr)", fv_pr)

            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Moč stresa: " + f"{sigma_m:.2f} °S")
                # Vizualizacija Slope modela (Figure 1)
                fig_slope = px.line(x=[0, 90], y=[0, sigma_m], labels={'x':'Teoretični okvir', 'y':'Intenzivnost'})
                st.plotly_chart(fig_slope)
            
            with col_b:
                st.subheader("Energetska učinkovitost: " + f"{(w_eu/2500)*100:.1f}%")
                st.write(f"Izguba energije: **{int(w_ls)} kcal**")
                st.plotly_chart(px.pie(factors_df, names='enota', title="Porazdelitev po enotah"))

            st.write("### Seznam vseh izluščenih dejavnikov:")
            st.dataframe(factors_df)
