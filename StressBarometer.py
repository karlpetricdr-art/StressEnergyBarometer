import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import json
import re

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025) - Multi-faktor Analiza")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Sistem zdaj analizira vsako besedo in izlušči več dejavnikov hkrati.")

def run_multi_factor_analysis(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    extracted_data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, text in enumerate(text_list):
        if not text or len(str(text)) < 2: continue
        
        prompt = f"""
        Analiziraj izjavo respondenta po modelu Petrič (2025). 
        Iz besedila izlušči VSE omenjene dejavnike.
        Za vsak dejavnik določi:
        - tip: SF (stresor), PF (pozitiven), PR (predlog).
        - enota: At, St, So, PS, IP, HB.
        - opis: kratek standardiziran povzetek dejavnika (npr. 'hrup', 'roki', 'odnosi').

        Izjava: "{text}"

        Vrni izključno JSON seznam objektov brez dodatnega besedila!
        Primer formata:
        [
          {{"tip": "SF", "enota": "At", "opis": "hrup"}},
          {{"tip": "SF", "enota": "So", "opis": "slab odnos"}}
        ]
        """
        try:
            response = model.generate_content(prompt)
            # Čiščenje odgovora, da ostane samo JSON
            raw_text = response.text
            json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
            if json_match:
                factors = json.loads(json_match.group())
                for f in factors:
                    # Preverimo, če so vsi ključi prisotni
                    if all(k in f for k in ('tip', 'enota', 'opis')):
                        extracted_data.append(f)
        except Exception as e:
            continue
        
        progress_bar.progress((i + 1) / len(text_list))
        status_text.text(f"Analiziram respondenta {i+1} od {len(text_list)}...")
        if (i+1) % 12 == 0: time.sleep(1)
            
    if not extracted_data:
        return pd.DataFrame(columns=['tip', 'enota', 'opis'])
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
            
            if factors_df.empty or 'tip' not in factors_df.columns:
                st.error("AI ni uspel izluščiti nobenih dejavnikov. Preverite vsebino datoteke.")
            else:
                # Funkcija za izračun metrik
                def get_metrics(type_code):
                    subset = factors_df[factors_df['tip'] == type_code]
                    fv = len(subset)
                    frv = subset['opis'].nunique()
                    rho = fv / No
                    Co = fv / frv if frv > 0 else 1
                    return (Co * rho) / 10, fv, frv

                Fo_SF, fv_sf, frv_sf = get_metrics('SF')
                Fo_PF, fv_pf, frv_pf = get_metrics('PF')
                Fo_PR, fv_pr, frv_pr = get_metrics('PR')

                # Varovalke za minimalne vrednosti (da preprečimo deljenje z 0 ali math error)
                if Fo_PF <= 0: Fo_PF = 0.32
                if Fo_PR <= 0: Fo_PR = 0.25

                # Izračun stresne moči (Enačba 27)
                try:
                    val = (Fo_SF * Fo_PR) / Fo_PF
                    sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
                except:
                    sigma_m = 0

                # Energija
                w_ls = (2500 * sigma_m) / 90
                w_eu = 2500 - w_ls

                # PRIKAZ
                st.header(f"Rezultati analize ({len(factors_df)} zaznanih dejavnikov)")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Zaznanih Stresorjev", fv_sf)
                c2.metric("Zaznanih Pozitivnih", fv_pf)
                c3.metric("Zaznanih Predlogov", fv_pr)

                st.markdown("---")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader(f"Moč stresa: {sigma_m:.2f} °S")
                    fig_slope = px.line(x=[0, 90], y=[0, sigma_m], 
                                        labels={'x':'Teoretični okvir (°S)', 'y':'Intenzivnost'},
                                        range_x=[0,90], range_y=[0,90])
                    st.plotly_chart(fig_slope)
                
                with col_b:
                    st.subheader(f"Energetska učinkovitost: {(w_eu/2500)*100:.1f}%")
                    st.write(f"Izguba energije: **{int(w_ls)} kcal**")
                    if 'enota' in factors_df.columns:
                        st.plotly_chart(px.pie(factors_df, names='enota', title="Porazdelitev po enotah (At, St, So, ...)"))

                st.write("### Seznam vseh izluščenih dejavnikov:")
                st.dataframe(factors_df)
