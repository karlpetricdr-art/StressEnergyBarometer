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
def izracunaj_energijo(sigma_m, W_I=2500, sigma_w=90):
    w_ls = (W_I * sigma_m) / sigma_w
    w_eu = W_I - w_ls
    return w_eu, w_ls

def izracunaj_F_faktor(fv, frv, No):
    if No <= 0 or frv <= 0: return 0.1
    rho = fv / No
    co = fv / frv
    return (co * rho) / 10

# --- GLAVNI DEL: NALAGANJE PODATKOV ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        content = uploaded_file.read().decode("utf-8")
        df = pd.DataFrame(content.splitlines(), columns=["Odgovor"])

    vnosni_podatki = df.iloc[:, 0].dropna().astype(str).tolist()
    st.write(f"Naloženih odgovorov: {len(vnosni_podatki)}")

    if st.button("Zaženi analizo z LLM"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            try:
                # 1. KONFIGURACIJA IN REŠITEV ZA 404
                genai.configure(api_key=api_key)
                
                # Poiščemo prvi delujoč model, ki nam ga Google sploh dovoli
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                selected_model_name = next((m for m in available_models if "gemini-1.5-flash" in m), available_models[0])
                
                model = genai.GenerativeModel(selected_model_name)
                st.success(f"Povezava vzpostavljena preko: {selected_model_name}")

                # 2. PRIPRAVA PODATKOV (Single-Shot klic zaradi omejitve 20/dan)
                vsi_odgovori_text = "\n".join([f"R{i}: {txt}" for i, txt in enumerate(vnosni_podatki)])
                
                prompt = f"""
                Analiziraj spodnje izjave respondentov in izlušči VSE dejavnike po modelu Petrič (2025).
                Enotne kategorije: At, St, So, PS, IP, HB.
                Tipi dejavnikov: SF (stresor), PF (pozitiven faktor), PR (predlog).
                
                Vrni IZKLJUČNO JSON seznam objektov.
                Format: [ {{"tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "kratek_opis"}} ]
                
                Odgovori:
                {vsi_odgovori_text}
                """
                
                with st.spinner("AI obdeluje vse podatke hkrati (to lahko traja do 1 minute)..."):
                    response = model.generate_content(prompt)
                    
                    # Izluščimo JSON iz odgovora (varovalka za nepotrebno besedilo)
                    json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if json_match:
                        zaznani_dejavniki = json.loads(json_match.group())
                        f_df = pd.DataFrame(zaznani_dejavniki)
                        
                        # 3. STATISTIČNA OBDELAVA
                        def dobi_f(t):
                            sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                            return len(sub), max(1, sub['opis'].nunique())

                        fv_sf, frv_sf = dobi_f('SF')
                        fv_pf, frv_pf = dobi_f('PF')
                        fv_pr, frv_pr = dobi_f('PR')

                        # 4. IZRAČUN PO MODELU PETRIČ (2025)
                        F_sf = izracunaj_F_faktor(fv_sf, frv_sf, len(vnosni_podatki))
                        F_pf = izracunaj_F_faktor(fv_pf, frv_pf, len(vnosni_podatki))
                        F_pr = izracunaj_F_faktor(fv_pr, frv_pr, len(vnosni_podatki))
                        
                        if F_pf <= 0: F_pf = 0.32 # Konstanta iz članka kot varovalka
                        
                        # Enačba 27 (stresna moč)
                        razmerje = (F_sf * F_pr) / F_pf
                        skupna_sigma = math.degrees(math.asin(min(1.0, math.sqrt(razmerje))))
                        
                        # Izračun energije (Enačba 38)
                        w_eu, w_ls = izracunaj_energijo(skupna_sigma)
                        izkoristek = (w_eu / 2500) * 100

                        # --- VIZUALIZACIJA ---
                        st.balloons()
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Stresna moč po kategorijah")
                            fig = px.histogram(f_df, x='enota', color='tip', barmode='group',
                                               category_orders={"enota": ["At", "St", "So", "PS", "IP", "HB"]},
                                               color_discrete_map={'SF':'#EF553B', 'PF':'#00CC96', 'PR':'#636EFA'})
                            st.plotly_chart(fig)
                        
                        with col2:
                            st.subheader("Energetska bilanca (Enačba 38)")
                            st.metric("Skupna stresna moč (σ)", f"{skupna_sigma:.2f} °S")
                            st.metric("Dejansko porabljena energija (W_EU)", f"{int(w_eu)} kcal")
                            st.metric("Učinkovitost energije (η)", f"{izkoristek:.2f} %")
                            st.write(f"Zaznanih dejavnikov: {len(f_df)}")

                        st.subheader("Podrobna klasifikacija AI")
                        st.dataframe(f_df)
                    else:
                        st.error("AI ni vrnil pravilnega formata podatkov. Poskusite še enkrat.")

            except Exception as e:
                st.error(f"Prišlo je do napake: {e}")
                st.info("Če vidite napako 404, pomeni, da vaš ključ danes nima dostopa do tega modela. Poskusite z novim API ključem.")
