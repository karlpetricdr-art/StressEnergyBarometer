import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import json
import re

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")
    st.info("Strategija: Vsi podatki hkrati (1 klic) zaradi omejitve 20/dan.")

def extract_json_from_text(text):
    try:
        # Poišče vsebino med oglatimi oklepaji [ ]
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

# --- MATEMATIČNI MODEL (Enačbe 12-39) ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    # Enačbe 12-23 (Gostota in Kompleksnost)
    rho_sf, Co_sf = fv_sf/No, (fv_sf/frv_sf if frv_sf > 0 else 1)
    rho_pf, Co_pf = fv_pf/No, (fv_pf/frv_pf if frv_pf > 0 else 1)
    rho_pr, Co_pr = fv_pr/No, (fv_pr/frv_pr if frv_pr > 0 else 1)
    
    # Enačbe 24-26 (Realni faktorji F, rhot=10, Ct=1)
    F_sf = (Co_sf * rho_sf) / 10
    F_pf = (Co_pf * rho_pf) / 10
    F_pr = (Co_pr * rho_pr) / 10
    
    if F_pf <= 0: F_pf = 0.32 # Konstanta iz članka, če ni dovolj podatkov
    
    # Enačba 27 (Stresna moč sigma)
    val = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    
    # Enačba 38-39 (Energija)
    W_I = 2500
    w_ls = (W_I * sigma) / 90
    w_eu = W_I - w_ls
    eta = (w_eu / W_I) * 100
    return sigma, w_eu, w_ls, eta

uploaded_file = st.file_uploader("Naložite datoteko z odgovori", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    # Branje datoteke
    if uploaded_file.name.endswith('.xlsx'):
        data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        data = pd.read_csv(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        data = [l.strip() for l in uploaded_file.read().decode("utf-8").splitlines() if len(l.strip()) > 2]

    st.success(f"Datoteka pripravljena: {len(data)} respondentov.")

    if st.button("🚀 POŠLJI VSE PODATKE NA ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ.")
        else:
            try:
                genai.configure(api_key=api_key)
                
                # DINAMIČNO ISKANJE MODELA (Rešitev za 404)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                if not available_models:
                    st.error("Vaš ključ nima dostopa do nobenega modela.")
                else:
                    # Izberemo najboljši model (flash ali pro)
                    target = "models/gemini-1.5-flash"
                    selected_model = target if target in available_models else available_models[0]
                    
                    st.info(f"Uporabljam model: `{selected_model}`")
                    model = genai.GenerativeModel(selected_model)
                    
                    # Priprava vseh podatkov v enem bloku
                    input_text = "\n".join([f"ID_{i+1}: {txt}" for i, txt in enumerate(data)])
                    
                    prompt = f"""
                    Instructions: Analyze all {len(data)} responses and extract ALL psychosocial factors (Stressors SF, Positive PF, Suggestions PR) based on the Petrič (2025) model.
                    Units for categorization: At, St, So, PS, IP, HB.
                    Format: Return ONLY a valid JSON list of objects for all data combined.
                    JSON Format Example: [ {{ "tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "short label" }} ]
                    
                    Data to analyze:
                    {input_text}
                    """
                    
                    with st.spinner("AI analizira celotno zbirko podatkov hkrati..."):
                        response = model.generate_content(prompt)
                        all_factors = extract_json_from_text(response.text)
                    
                    if all_factors:
                        f_df = pd.DataFrame(all_factors)
                        
                        def get_f(t):
                            sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                            return len(sub), max(1, sub['opis'].nunique())

                        fv_sf, frv_sf = get_f('SF')
                        fv_pf, frv_pf = get_f('PF')
                        fv_pr, frv_pr = get_f('PR')

                        s, we, wl, et = calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, len(data))

                        st.balloons()
                        st.header("Končni rezultati analize")
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                        col2.metric("Učinkovitost (η)", f"{et:.2f} %")
                        col3.metric("Izguba (W_LS)", f"{int(wl)} kcal")

                        st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group', title="Zaznani dejavniki po enotah"))
                        st.dataframe(f_df)
                    else:
                        st.error("AI ni vrnil podatkov v JSON formatu.")
                        st.text("Odgovor AI (Debug):")
                        st.write(response.text)
                        
            except Exception as e:
                st.error(f"Prišlo je do napake: {e}")
