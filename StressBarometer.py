import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

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

# --- FUNKCIJE ZA IZRAČUNE (Po vašem članku) ---
def izracunaj_energijo(sigma_m, W_I=2500, sigma_w=90):
    # Enačba 38: W_EU = W_I - (W_I * sigma_m / sigma_w)
    # Poenostavljeno: W_EU = 2500 - (2500 * sigma_m / 90)
    w_ls = (W_I * sigma_m) / sigma_w
    w_eu = W_I - w_ls
    return w_eu, w_ls

# --- GLAVNI DEL: NALAGANJE PODATKOV ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    # Branje datoteke (predvidevamo, da je besedilo v prvem stolpcu)
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        content = uploaded_file.read().decode("utf-8")
        df = pd.DataFrame(content.splitlines(), columns=["Odgovor"])

    st.write("Naloženih odgovorov:", len(df))
    st.dataframe(df.head())

    if st.button("Zaženi analizo z LLM"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            with st.spinner("LLM razvršča odgovore..."):
                # Tukaj bi prišla zanka, ki pokliče Gemini za vsako vrstico
                # Zaenkrat samo simuliramo rezultat za vizualizacijo
                st.info("Simulacija rezultatov na podlagi Tabel iz članka...")
                
                # TESTNI PODATKI IZ VAŠE TABELE 5 (stran 42)
                results = {
                    'Faktor': ['Attentive', 'Individual Psych.', 'Partial Social', 'Social', 'Performance', 'Health Bio.'],
                    'sigma_v': [3.49, 12.82, 12.82, 18.26, 14.21, 6.38]
                }
                res_df = pd.DataFrame(results)
                
                # Izračun skupne stresne moči (npr. 32.76 iz članka)
                skupna_sigma = 32.76
                w_eu, w_ls = izracunaj_energijo(skupna_sigma)

                # --- VIZUALIZACIJA ---
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Stresna moč po kategorijah (°S)")
                    fig = px.bar(res_df, x='Faktor', y='sigma_v', color='sigma_v', color_continuous_scale='Reds')
                    st.plotly_chart(fig)
                
                with col2:
                    st.subheader("Energetska bilanca (Enačba 38)")
                    st.metric("Skupna stresna moč", f"{skupna_sigma} °S")
                    st.metric("Dejansko porabljena energija (W_EU)", f"{int(w_eu)} kcal")
                    st.metric("Izguba zaradi stresa (W_LS)", f"{int(w_ls)} kcal", delta_color="inverse")
                    
                    izkoristek = (w_eu / 2500) * 100
                    st.write(f"**Učinkovitost energije (η):** {izkoristek:.2f} %")
