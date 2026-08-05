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

# --- MATEMATIČNE FUNKCIJE ---
def calc_Fo(df_subset, No):
    fv = len(df_subset)
    # frv: število unikatnih odgovorov v tej skupini
    frv = df_subset['Odgovor'].nunique()
    if fv == 0: return 0.1 # Default minimalna vrednost
    
    rho = fv / No # Gostota (Enačba 12)
    Co = fv / frv if frv > 0 else 1 # Kompleksnost (Enačba 18)
    
    # Realni faktor (Enačba 24, 25, 26)
    return (Co * rho) / 10

def run_smart_classification(text_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    types, categories = [], []
    progress_bar = st.progress(0)
    
    for i, text in enumerate(text_list):
        prompt = f"""
        Analiziraj izjavo respondenta po modelu Petrič (2025).
        1. Določi TIP: SF (stresor), PF (pozitiven dejavnik), PR (predlog).
        2. Določi ENOTO: At, St, So, PS, IP, HB.
        
        Izjava: "{text}"
        Vrni samo v formatu: TIP, ENOTA (npr: SF, So)
        """
        try:
            res = model.generate_content(prompt).text.strip().split(',')
            types.append(res[0].strip())
            categories.append(res[1].strip())
        except:
            types.append("SF")
            categories.append("IP")
        
        progress_bar.progress((i + 1) / len(text_list))
        if (i+1) % 15 == 0: 
            time.sleep(1)
            
    return types, categories

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

    # Zagotovimo, da imamo stolpec z imenom 'Odgovor'
    if df.columns[0] != "Odgovor":
        df.rename(columns={df.columns[0]: "Odgovor"}, inplace=True)

    No = len(df)
    st.write(f"Naloženih vrstic: {No}")

    # --- GUMB ZA ANALIZO ---
    if st.button("ZAŽENI PRAVO ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            with st.spinner("AI analizira vsebino in tipe dejavnikov..."):
                types, cats = run_smart_classification(df["Odgovor"].tolist(), api_key)
                df['Tip'], df['Enota'] = types, cats
            
            # Izračun realnih faktorjev iz podatkov
            Fo_SF = calc_Fo(df[df['Tip'] == 'SF'], No)
            Fo_PF = calc_Fo(df[df['Tip'] == 'PF'], No)
            Fo_PR = calc_Fo(df[df['Tip'] == 'PR'], No)
            
            # Varovalka: če ni podatkov, vzamemo povprečje iz članka
            if Fo_PF < 0.05: Fo_PF = 0.32
            if Fo_PR < 0.05: Fo_PR = 0.25

            # Enačba 27 (Stresna moč sigma)
            val = (Fo_SF * Fo_PR) / Fo_PF
            sigma_m = math.degrees(math.asin(min(1.0, math.sqrt(val))))
            
            # Energija (Enačba 38-39)
            W_I = 2500
            w_ls = (W_I * sigma_m) / 90
            w_eu = W_I - w_ls
            eta = (w_eu / W_I) * 100

            # --- PRIKAZ REZULTATOV ---
            st.header("Rezultati realne klasifikacije")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("### Porazdelitev po Enotah")
                st.plotly_chart(px.pie(df, names='Enota', hole=0.4))
                st.write("### Porazdelitev po Tipu (SF, PF, PR)")
                st.plotly_chart(px.bar(df['Tip'].value_counts()))
            
            with col2:
                st.metric("Stresna moč (σ)", f"{sigma_m:.2f} °S")
                st.metric("Učinkovitost (η)", f"{eta:.2f} %")
                st.metric("Izguba (W_LS)", f"{int(w_ls)} kcal")
                st.write(f"**Dejanska poraba (W_EU):** {int(w_eu)} kcal")
            
            st.write("### Razvrstitev vaših odgovorov:")
            st.dataframe(df)
