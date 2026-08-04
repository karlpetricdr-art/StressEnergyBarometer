import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time

# Nastavitve strani
st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")

st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Pridobite ključ na [Google AI Studio](https://aistudio.google.com/app/apikey)")
    st.markdown("---")
    st.write("Avtor modela: Karl Petrič, 2025")

# --- MATEMATIČNE FUNKCIJE (Enačbe iz članka 1-39) ---
def calc_metrics(all_responses, category_list, No):
    # fv: frekvenca vseh mnenj v kategoriji
    fv = len(category_list)
    # frv: frekvenca različnih mnenj (unikatnih)
    frv = len(set(category_list))
    
    if fv == 0: return 0, 0, 0
    
    rho = fv / No # Gostota (Enačba 12)
    Co = fv / frv if frv > 0 else 1 # Kompleksnost (Enačba 18)
    
    # Realni faktor (Enačba 24, 25, 26) - Ct=1, rhot=10
    Fo = (Co * rho) / (1 * 10)
    return Fo, fv, frv

def run_classification(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, text in enumerate(text_list):
        if not text or len(str(text)) < 3: continue
        
        prompt = f"""
        Analiziraj izjavo respondenta in jo razvrsti v eno od 6 kategorij po Petrič (2025):
        - AtSF (Attentive physical): svetloba, hrup, klima, ergonomija.
        - StSF (Performance): pomanjkanje informacij, preveč truda, roki.
        - SoSF (Social): odnosi, mobing, konflikti.
        - PSSF (Partial social): kazni, pomanjkanje nagrad.
        - IPSF (Individual Psychological): strah, tesnoba, stres.
        - HBSF (Health biological): bolezni, higiena.
        
        Izjava: "{text}"
        Vrni samo kratico kategorije.
        """
        try:
            response = model.generate_content(prompt)
            results.append(response.text.strip())
        except:
            results.append("Neuvrščeno")
        
        # Posodobitev napredka
        prog = (i + 1) / len(text_list)
        progress_bar.progress(prog)
        status_text.text(f"Obdelava odgovora {i+1} od {len(text_list)}...")
        
        # Premor zaradi API omejitev (Free tier)
        if (i+1) % 10 == 0:
            time.sleep(1)
            
    return results

# --- NALAGANJE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        content = uploaded_file.read().decode("utf-8")
        df = pd.DataFrame(content.splitlines(), columns=["Odgovor"])

    No = len(df)
    st.write(f"Naloženih odgovorov ($N_o$): {No}")

    if st.button("ZAŽENI PRAVO ANALIZO"):
        if not api_key:
            st.error("Prosim vnesite API ključ v stransko vrstico!")
        else:
            # 1. Klasifikacija
            with st.spinner("AI razvršča odgovore..."):
                classifications = run_classification(df.iloc[:, 0].tolist(), api_key)
                df['Klasifikacija'] = classifications
            
            # 2. Izračuni
            # Za ta primer predvidevamo, da so vsi odgovori 'Stressors' (SF)
            # V realni aplikaciji bi ločili SF, PF in PR
            Fo_SF, fv_sf, frv_sf = calc_metrics(df.iloc[:, 0].tolist(), classifications, No)
            
            # Za demonstracijo vzemimo PF in PR faktorje kot konstante, če jih datoteka nima
            # V idealnem primeru bi AI klasificiral tudi te.
            Fo_PF = 0.32 # Table 25 v članku
            Fo_PR = 0.25 # Table 26 v članku
            
            # Izračun celotne stresne moči (Enačba 27)
            inside_sqrt = (Fo_SF * Fo_PR) / Fo_PF
            sigma_m = math.degrees(math.asin(math.sqrt(inside_sqrt)))
            
            # Energetska bilanca (Enačba 38)
            W_I = 2500
            w_ls = (W_I * sigma_m) / 90
            w_eu = W_I - w_ls
            eta = (w_eu / W_I) * 100

            # --- PRIKAZ REZULTATOV ---
            st.header("Dejanski rezultati na podlagi vaših podatkov")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Stresna moč po klasifikaciji AI")
                counts = df['Klasifikacija'].value_counts().reset_index()
                fig = px.bar(counts, x='Klasifikacija', y='count', color='Klasifikacija')
                st.plotly_chart(fig)
            
            with col2:
                st.metric("Izračunana stresna moč (σ)", f"{sigma_m:.2f} °S")
                st.metric("Dejanska poraba (W_EU)", f"{int(w_eu)} kcal")
                st.metric("Izguba energije (W_LS)", f"{int(w_ls)} kcal")
                st.metric("Učinkovitost (η)", f"{eta:.2f} %")
            
            st.write("### Razvrstitev vaših odgovorov:")
            st.dataframe(df)
