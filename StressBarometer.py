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
st.markdown("""
Aplikacija za klasifikacijo stresnih dejavnikov, izračun stresne moči ($\sigma$) 
in oceno porabe energije ($W_{EU}$) v kcal.
""")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Brez ključa klasifikacija ne bo delovala.")

# --- MATEMATIČNE FUNKCIJE (Po modelu Petrič, 2025) ---
def izracunaj_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    # Enačbe 12-23 (Gostota in Kompleksnost)
    def get_F_factor(fv, frv):
        if No <= 0 or frv <= 0: return 0.05
        rho = fv / No
        co = fv / frv
        return (co * rho) / 10

    F_sf = get_F_factor(fv_sf, frv_sf)
    F_pf = get_F_factor(fv_pf, frv_pf)
    F_pr = get_F_factor(fv_pr, frv_pr)
    
    # Varovalka: F_pf ne sme biti 0 (Enačba 27)
    if F_pf <= 0: F_pf = 0.32
    
    # Izračun stresne moči sigma (Enačba 27)
    inside_sqrt = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(inside_sqrt))))
    
    # Poraba energije (Enačba 38-39)
    w_ls = (2500 * sigma) / 90
    w_eu = 2500 - w_ls
    return sigma, w_eu, (w_eu / 2500) * 100

# --- GLAVNI DEL: NALAGANJE PODATKOV ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        df_input = pd.read_excel(uploaded_file)
        vnosni_podatki = df_input.iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        df_input = pd.read_csv(uploaded_file)
        vnosni_podatki = df_input.iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        vnosni_podatki = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    st.write(f"Naloženih odgovorov: {len(vnosni_podatki)}")

    if st.button("Zaženi pravo analizo z LLM"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                # 1. Konfiguracija (Prisiljen stabilen protokol)
                genai.configure(api_key=api_key)
                
                # Uporabimo stabilen model
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 2. Priprava prompta (Vsi podatki hkrati - Single Shot)
                vsi_odgovori_text = "\n".join([f"ID_{i}: {txt}" for i, txt in enumerate(vnosni_podatki)])
                
                prompt = f"""
                Deluj kot ekspert za psihologijo dela. Analiziraj spodnje izjave in izlušči VSE dejavnike po modelu Petrič (2025).
                Kategorije enot: At, St, So, PS, IP, HB.
                Tipi: SF (stresor), PF (pozitiven faktor), PR (predlog).
                
                Vrni IZKLJUČNO JSON seznam objektov.
                Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "kratek_opis"}} ]
                
                Izjave za analizo:
                {vsi_odgovori_text}
                """
                
                with st.spinner("AI klasificira odgovore in računa stresno moč..."):
                    response = model.generate_content(prompt)
                    
                    # Izluščimo JSON iz odgovora
                    json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if json_match:
                        zaznani_dejavniki = json.loads(json_match.group())
                        f_df = pd.DataFrame(zaznani_dejavniki)
                        
                        # 3. Izračun frekvenc fv in unikatnih mnenj frv
                        def dobi_statistiko(t):
                            sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                            return len(sub), max(1, sub['opis'].nunique())

                        fv_sf, frv_sf = dobi_statistiko('SF')
                        fv_pf, frv_pf = dobi_statistiko('PF')
                        fv_pr, frv_pr = dobi_statistiko('PR')

                        # 4. Klic matematičnega modela
                        skupna_sigma, w_eu, ucinkovitost = izracunaj_petric_model(
                            fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, len(vnosni_podatki)
                        )

                        # --- VIZUALIZACIJA REALNIH REZULTATOV ---
                        st.balloons()
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Stresna moč po enotah")
                            # Prikažemo histogram realnih dejavnikov
                            fig = px.histogram(f_df, x='enota', color='tip', barmode='group',
                                               category_orders={"enota": ["At", "St", "So", "PS", "IP", "HB"]},
                                               color_discrete_map={'SF':'red', 'PF':'green', 'PR':'blue'})
                            st.plotly_chart(fig)
                        
                        with col2:
                            st.subheader("Izračunani indikatorji")
                            st.metric("Dejanska stresna moč (σ)", f"{skupna_sigma:.2f} °S")
                            st.metric("Učinkovitost energije (η)", f"{ucinkovitost:.2f} %")
                            st.metric("Porabljena energija (W_EU)", f"{int(w_eu)} kcal")
                            st.write(f"Zaznanih dejavnikov skupaj: {len(f_df)}")
                        
                        with st.expander("Poglej podrobno tabelo klasifikacije"):
                            st.dataframe(f_df)

                    else:
                        st.error("AI ni vrnil pravilno strukturiranih podatkov. Poskusite ponovno.")
                        st.write("Surovi odgovor AI:", response.text[:500])

            except Exception as e:
                st.error(f"Prišlo je do napake: {e}")
                st.info("Če vidite napako 404, preverite API ključ v stranski vrstici.")
