import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import re

# Nastavitve strani
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Sistem zdaj izlušči več dejavnikov iz enega stavka (npr. 'hrup in konflikti' -> 2 dejavnika).")

# --- MATEMATIČNE FUNKCIJE ---
def calc_Fo(df_factors, No):
    # fv: vsi zaznani dejavniki v tej kategoriji (SF, PF ali PR)
    fv = len(df_factors)
    # frv: število unikatnih opisov/mnenj
    frv = df_factors['opis'].nunique()
    
    if fv == 0: return 0.1
    
    rho = fv / No # Gostota (Enačba 12)
    Co = fv / frv if frv > 0 else 1 # Kompleksnost (Enačba 18)
    
    return (Co * rho) / 10 # Realni faktor Fo

# --- ANALITIČNA FUNKCIJA ---
def run_deep_analysis(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    all_extracted_factors = []
    progress_bar = st.progress(0)
    
    for i, text in enumerate(text_list):
        # Izboljšan prompt za ekstrakcijo VSEH dejavnikov
        prompt = f"""
        Analiziraj spodnjo izjavo respondenta po modelu Petrič (2025). 
        Iz besedila izlušči VSE omenjene dejavnike (stresne, pozitivne ali predloge).
        
        Za vsak dejavnik določi:
        1. TIP: SF (stresor), PF (pozitiven), PR (predlog).
        2. ENOTO: At, St, So, PS, IP, HB.
        3. OPIS: kratek povzetek (1-3 besede).

        Izjava: "{text}"
        
        Vrni v formatu: TIP | ENOTA | OPIS (vsak dejavnik v svoji vrstici).
        Primer:
        SF | At | hrup
        SF | So | konflikti
        """
        try:
            response = model.generate_content(prompt)
            lines = response.text.strip().split('\n')
            for line in lines:
                parts = line.split('|')
                if len(parts) == 3:
                    all_extracted_factors.append({
                        'tip': parts[0].strip(),
                        'enota': parts[1].strip(),
                        'opis': parts[2].strip()
                    })
        except:
            continue
        
        progress_bar.progress((i + 1) / len(text_list))
        if (i+1) % 15 == 0: time.sleep(1)
            
    return pd.DataFrame(all_extracted_factors)

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        df_raw = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        content = uploaded_file.read().decode("utf-8")
        df_raw = pd.DataFrame(content.splitlines(), columns=["Odgovor"])

    if df_raw.columns[0] != "Odgovor":
        df_raw.rename(columns={df_raw.columns[0]: "Odgovor"}, inplace=True)

    No = len(df_raw)
    st.write(f"Naloženih respondentov ($N_o$): {No}")

    if st.button("ZAŽENI REALNO ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            with st.spinner("AI razčlenjuje stavke na posamezne dejavnike..."):
                factors_df = run_deep_analysis(df_raw["Odgovor"].tolist(), api_key)
            
            if not factors_df.empty:
                # Izračun realnih faktorjev Fo
                Fo_SF = calc_Fo(factors_df[factors_df['tip'] == 'SF'], No)
                Fo_PF = calc_Fo(factors_df[factors_df['tip'] == 'PF'], No)
                Fo_PR = calc_Fo(factors_df[factors_df['tip'] == 'PR'], No)
                
                if Fo_PF <= 0: Fo_PF = 0.32 # Varovalka
                
                # Enačba 27: Stresna moč
                val = (Fo_SF * Fo_PR) / Fo_PF
                sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
                
                # Energija
                w_ls = (2500 * sigma_m) / 90
                w_eu = 2500 - w_ls
                eta = (w_eu / 2500) * 100

                # --- PRIKAZ ---
                st.header("Končni rezultati analize")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Moč stresa (σ)", f"{sigma_m:.2f} °S")
                c2.metric("Učinkovitost (η)", f"{eta:.2f} %")
                c3.metric("Število dejavnikov", len(factors_df))

                # Vizualizacija
                st.subheader("Struktura dejavnikov v organizaciji")
                fig = px.histogram(factors_df, x='enota', color='tip', barmode='group',
                                   category_orders={"enota": ["At", "St", "So", "PS", "IP", "HB"]},
                                   color_discrete_map={'SF':'red', 'PF':'green', 'PR':'blue'})
                st.plotly_chart(fig)
                
                st.write("### Seznam vseh izluščenih dejavnikov:")
                st.dataframe(factors_df)
            else:
                st.error("AI ni uspel izluščiti dejavnikov. Poskusite ponovno.")
