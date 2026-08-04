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
    st.markdown("---")
    if st.button("⚙️ Kalibracija (Podatki iz članka)"):
        st.session_state.calibrated = True
    else:
        st.session_state.calibrated = False

def clean_ai_json(raw_text):
    try:
        text = re.sub(r'```json|```', '', raw_text).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match: return json.loads(match.group())
    except: pass
    return []

# --- FUNKCIJA ZA IZRAČUN PO ENAČBAH 12-39 ---
def calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, No):
    # Enačbe 12-23 (Gostota in Kompleksnost)
    rho_sf, Co_sf = fv_sf/No, fv_sf/frv_sf
    rho_pf, Co_pf = fv_pf/No, fv_pf/frv_pf
    rho_pr, Co_pr = fv_pr/No, fv_pr/frv_pr
    
    # Enačbe 24-26 (Realni faktorji F, rhot=10, Ct=1)
    F_sf = (Co_sf * rho_sf) / 10
    F_pf = (Co_pf * rho_pf) / 10
    F_pr = (Co_pr * rho_pr) / 10
    
    # Enačba 27 (Stresna moč sigma)
    val = (F_sf * F_pr) / F_pf
    sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    
    # Enačba 38-39 (Energija in učinkovitost)
    W_I = 2500
    w_ls = (W_I * sigma) / 90
    w_eu = W_I - w_ls
    eta = (w_eu / W_I) * 100
    
    return sigma, w_eu, w_ls, eta

# --- KALIBRACIJSKI PRIKAZ ---
if st.session_state.calibrated:
    st.info("Uporabljeni so uradni podatki iz članka (Table 2, 3, 4).")
    # Podatki s strani 35, 36, 37 vašega PDF
    s, we, wl, et = calculate_petric_model(543, 480, 531, 437, 446, 395, 200)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Umerjena moč (σ)", f"{s:.2f} °S")
    c2.metric("Umerjena učinkovitost (η)", f"{et:.2f} %")
    c3.metric("Izguba (W_LS)", f"{int(wl)} kcal")
    st.success("✅ Sistem je pravilno umerjen na rezultate Petrič (2025).")

# --- ANALIZA VAŠE DATOTEKE ---
uploaded_file = st.file_uploader("Naložite datoteko", type=['xlsx', 'csv', 'txt'])

if uploaded_file:
    # Branje datoteke...
    if uploaded_file.name.endswith('.xlsx'):
        text_data = pd.read_excel(uploaded_file).iloc[:, 0].dropna().astype(str).tolist()
    else:
        content = uploaded_file.read().decode("utf-8")
        text_data = [l.strip() for l in content.splitlines() if len(l.strip()) > 2]

    if st.button("🚀 ZAŽENI VARČNO ANALIZO (Veliki paketi)"):
        if not api_key: st.error("Vnesite API ključ.")
        else:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Povečan paket na 75, da porabimo le 3 zahtevi!
            batch_size = 75 
            extracted_data = []
            
            pb = st.progress(0)
            for i in range(0, len(text_data), batch_size):
                batch = text_data[i : i + batch_size]
                prompt = f"Extract ALL psychosocial factors (SF, PF, PR) as JSON list. Units: At, St, So, PS, IP, HB. Format: [{{'tip': 'SF/PF/PR', 'enota': '...', 'opis': '...'}}]. Data: {' | '.join(batch)}"
                
                try:
                    res = model.generate_content(prompt)
                    factors = clean_ai_json(res.text)
                    extracted_data.extend(factors)
                except Exception as e:
                    st.warning(f"Batch {i//batch_size + 1} failed: {e}")
                
                pb.progress(min(1.0, (i + batch_size) / len(text_data)))
                time.sleep(5) # Premor med 3 kliki

            f_df = pd.DataFrame(extracted_data)
            if not f_df.empty:
                # Izračun frekvenc iz vaših podatkov
                def get_f(t):
                    sub = f_df[f_df['tip'].str.contains(t, na=False, case=False)]
                    return len(sub), max(1, sub['opis'].nunique())

                fv_sf, frv_sf = get_f('SF')
                fv_pf, frv_pf = get_f('PF')
                fv_pr, frv_pr = get_f('PR')

                # Izračun
                s, we, wl, et = calculate_petric_model(fv_sf, frv_sf, fv_pf, frv_pf, fv_pr, frv_pr, len(text_data))

                st.header(f"Rezultat vaše datoteke: {len(f_df)} dejavnikov")
                m1, m2, m3 = st.columns(3)
                m1.metric("Moč stresa (σ)", f"{s:.2f} °S")
                m2.metric("Učinkovitost (η)", f"{et:.1f} %")
                m3.metric("Stresorjev (fv_sf)", fv_sf)
                st.plotly_chart(px.histogram(f_df, x='enota', color='tip', barmode='group'))
                st.dataframe(f_df)
