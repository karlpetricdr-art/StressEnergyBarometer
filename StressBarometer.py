import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import math
import time
import json
import re

st.set_page_config(page_title="Psihosocialni Barometer", layout="wide")
st.title("📊 Psihosocialni Barometer (Petrič, 2025)")

# --- STRANSKA VRSTICA ---
with st.sidebar:
    st.header("Nastavitve")
    api_key = st.text_input("Vnesite Gemini API ključ:", type="password")

def clean_ai_json(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: return json.loads(match.group())
    except: pass
    return []

def get_best_model(api_key):
    """Poišče delujoč model na vašem API ključu."""
    genai.configure(api_key=api_key)
    try:
        # Seznam vseh modelov, ki podpirajo generiranje vsebine
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Poskusimo najti Flash verzijo, sicer vzamemo prvo dostopno
        flash_models = [m for m in models if 'flash' in m.lower()]
        selected = flash_models[0] if flash_models else models[0]
        return genai.GenerativeModel(selected)
    except Exception as e:
        st.error(f"Napaka pri dostopu do modelov: {e}")
        return None

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
    
    # Enačba 27 (Stresna moč sigma)
    # Varovalka: Fo_PF ne sme biti 0
    if F_pf <= 0: F_pf = 0.32
    
    val = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    
    # Enačba 38-39 (Energija)
    W_I = 2500
    w_ls = (W_I * sigma) / 90
    w_eu = W_I - w_ls
    eta = (w_eu / W_I) * 100
    
    return sigma, w_eu, w_ls, eta

# --- NALAGANJE IN ANALIZA ---
uploaded_file = st.file_uploader("Naložite datoteko (.xlsx, .csv, .txt)", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        text_data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith('.csv'):
        text_data = pd.read_csv(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    st.success(f"Zaznanih {len(text_data)} vrstic.")

    if st.button("🚀 ZAŽENI ANALIZO"):
        if not api_key:
            st.error("Vnesite API ključ v stransko vrstico.")
        else:
            model = get_best_model(api_key)
            if model:
                st.info(f"Uporabljam model: {model.model_name}")
                
                # Velik paket za preprečevanje "Quota Exceeded" napake
                batch_size = 100 
                extracted_data = []
                
                pb = st.progress(0)
                for i in range(0, len(text_data), batch_size):
                    batch = text_data[i : i + batch_size]
                    prompt = f"""
                    Extract ALL factors (SF, PF, PR) as JSON list. 
                    Units: At, St, So, PS, IP, HB. 
                    Format: [{{'tip': 'SF/PF/PR', 'enota': '...', 'opis': '...'}}]. 
                    Data: {' | '.join(batch)}
                    """
                    try:
                        res = model.generate_content(prompt)
                        factors = clean_ai_json(res.text)
                        extracted_data.extend(factors)
                    except Exception as e:
                        st.warning(f"Paket {i//batch_size + 1} ni uspel: {e}")
                    
                    pb.progress(min(1.0, (i + batch_size) / len(text_data)))
                    time.sleep(6) # Premor za stabilnost

                f_df = pd.DataFrame(extracted_data)
                if not f_df.empty:
                    # Izračun frekvenc
                    def get_f(t):
                        sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                        return len(sub), max(1, sub['opis'].nunique())

                    fv_sf, frv_sf = get_f('SF')
                    fv_pf, frv_pf = get_f('PF')
                    fv_pr, frv_pr = get_f('PR')

                    s, we, wl, et = calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, len(text_data))

                    st.balloons()
                    st.header(f"Rezultat analize: {len(f_df)} dejavnikov")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                    m2.metric("Učinkovitost (η)", f"{et:.1f} %")
                    m3.metric("Zaznanih stresorjev (fv_sf)", fv_sf)
                    
                    st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                    st.dataframe(f_df)
                else:
                    st.error("AI ni uspel izluščiti podatkov. Preverite vsebino datoteke.")
