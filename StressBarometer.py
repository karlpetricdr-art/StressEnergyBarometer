import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import re

# 1. Osnovne nastavitve
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("AI zdaj oceni vsak odgovor posebej in izlušči vse dejavnike.")

# --- MATEMATIČNA LOGIKA (Enačbe 12-39) ---
def calc_Fo(df_factors, No):
    fv = len(df_factors)
    # frv: število unikatnih opisov (AI standardizira opise, kar omogoča štetje frv)
    frv = df_factors['opis'].nunique()
    
    if fv == 0: return 0.05
    
    rho = fv / No # Gostota
    Co = fv / frv if frv > 0 else 1 # Kompleksnost
    return (Co * rho) / 10 # Realni faktor Fo

# --- ANALITIČNA FUNKCIJA (Obdelava enega po enega) ---
def run_respondent_analysis(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    all_factors = []
    progress_bar = st.progress(0)
    
    for i, text in enumerate(text_list):
        if not text or len(str(text)) < 3: continue
        
        # Enostaven prompt, ki zahteva seznam dejavnikov iz enega odgovora
        prompt = f"""
        Poglej spodnji odgovor respondenta. Po modelu Petrič (2025) iz njega izlušči VSE dejavnike.
        Če je v enem stavku več dejavnikov, jih zapiši vsakega v svojo vrstico.
        
        Format: TIP | ENOTA | OPIS
        TIP: SF (stresor), PF (pozitiven), PR (predlog)
        ENOTA: At, St, So, PS, IP, HB
        OPIS: kratek povzetek (npr. hrup, slabi odnosi, nizka plača)

        Odgovor: "{text}"
        """
        try:
            response = model.generate_content(prompt)
            # Razčlenimo vrstice (odstranimo prazne in neustrezne)
            lines = response.text.strip().split('\n')
            for line in lines:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) == 3:
                        all_factors.append({
                            'tip': parts[0].strip().upper(),
                            'enota': parts[1].strip(),
                            'opis': parts[2].strip().lower()
                        })
        except:
            continue
        
        progress_bar.progress((i + 1) / len(text_list))
        # Rate limit za brezplačni ključ (cca 15 RPM)
        if (i+1) % 10 == 0:
            time.sleep(1)
            
    return pd.DataFrame(all_factors)

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

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
    st.success(f"Naloženih respondentov ($N_o$): {No}")

    if st.button("🚀 ZAŽENI GLOBOKO ANALIzo"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            with st.spinner("AI analizira odgovore... to bo trajalo približno 1-2 minuti."):
                factors_df = run_respondent_analysis(df_raw["Odgovor"].tolist(), api_key)
            
            if not factors_df.empty:
                # 1. Izračun realnih faktorjev Fo
                # Filtriramo po tipu in preprečimo napake pri črkovanju (npr. SF, "SF", SF )
                Fo_SF = calc_Fo(factors_df[factors_df['tip'].str.contains('SF', na=False)], No)
                Fo_PF = calc_Fo(factors_df[factors_df['tip'].str.contains('PF', na=False)], No)
                Fo_PR = calc_Fo(factors_df[factors_df['tip'].str.contains('PR', na=False)], No)
                
                # Uporabimo konstanto iz članka, če pozitivnih dejavnikov ni dovolj
                if Fo_PF < 0.1: Fo_PF = 0.32 
                
                # 2. Enačba 27: Stresna moč
                ratio = (Fo_SF * Fo_PR) / Fo_PF
                sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(ratio))))
                
                # 3. Energija (vhod 2500 kcal)
                w_ls = (2500 * sigma_m) / 90
                w_eu = 2500 - w_ls
                eta = (w_eu / 2500) * 100

                # --- VIZUALIZACIJA ---
                st.balloons()
                st.header(f"Rezultat analize: {sigma_m:.2f} °S")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Moč stresa (σ)", f"{sigma_m:.2f} °S")
                c2.metric("Učinkovitost (η)", f"{eta:.2f} %")
                c3.metric("Zaznanih dejavnikov", len(factors_df))

                # Grafikon po enotah
                st.subheader("Struktura dejavnikov v organizaciji")
                fig = px.histogram(factors_df, x='enota', color='tip', barmode='group',
                                   category_orders={"enota": ["At", "St", "So", "PS", "IP", "HB"]},
                                   color_discrete_map={'SF':'#EF553B', 'PF':'#00CC96', 'PR':'#636EFA'})
                st.plotly_chart(fig)
                
                # Tabela za preverjanje
                st.write("### Podrobna klasifikacija (AI ocena):")
                st.dataframe(factors_df)
            else:
                st.error("AI ni uspel prepoznati dejavnikov. Poskusite ponovno.")
