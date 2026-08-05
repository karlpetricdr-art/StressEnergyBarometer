import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import math
import re
import time
from google import genai

# ============================================================
# 1. KONFIGURACIJA IN VMESNIK
# ============================================================
st.set_page_config(page_title="Psihosocialni Barometer v4.0", layout="wide")

st.title("📊 Psihosocialni Barometer v4.0")
st.markdown("### Znanstveni model Petrič (2025/2026)")

with st.sidebar:
    st.header("⚙️ Nastavitve")
    api_key = st.text_input("Google API ključ:", type="password")
    model_choice = st.selectbox("Izberite model:", 
                                ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp", "gemma-2-9b-it"])
    
    st.divider()
    W_I_kcal = st.number_input("Vhodna energija W_I (kcal):", value=2500)
    st.divider()
    st.write("**Metodologija:**")
    st.write("- Batch extraction (50/call)")
    st.write("- Python frequency counting")
    st.write("- Equation 27 & 38 compliance")

# ============================================================
# 2. MATEMATIČNE FUNKCIJE (Enačbe 12-39)
# ============================================================
def calculate_petric_final(df_extracted, No, WI):
    # Priprava tabel za tipe
    def get_Fo(type_code):
        subset = df_extracted[df_extracted['tip'].str.contains(type_code, na=False, case=False)]
        fv = len(subset)
        frv = subset['opis'].nunique()
        
        if fv == 0 or No == 0: return 0.05, 0, 1
        
        rho = fv / No                         # Enačba 12
        Co = fv / frv if frv > 0 else 1       # Enačba 18
        Fo = (Co * rho) / 10                  # Enačba 24
        return Fo, fv, frv

    F_sf, fv_sf, frv_sf = get_Fo('SF')
    F_pf, fv_pf, frv_pf = get_F_pf_custom(df_extracted, No) # Posebna obravnava za zaščito
    F_pr, fv_pr, frv_pr = get_Fo('PR')

    # Varovalka po članku
    if F_pf <= 0: F_pf = 0.32
    if F_pr <= 0: F_pr = 0.25

    # Enačba 27: Stresna moč (sigma)
    try:
        val = (F_sf * F_pr) / F_pf
        sigma = math.degrees(math.asin(min(1.0, math.sqrt(val))))
    except:
        sigma = 0

    # Enačba 38: Energetski model (90 stopinj = 100% izguba)
    loss_kcal = (WI * sigma) / 90
    w_eu = WI - loss_kcal
    efficiency = (w_eu / WI) * 100

    return {
        "sigma": sigma, "w_eu": w_eu, "loss": loss_kcal, "eff": efficiency,
        "F_sf": F_sf, "F_pf": F_pf, "F_pr": F_pr,
        "fv_sf": fv_sf, "frv_sf": frv_sf,
        "fv_pf": fv_pf, "frv_pf": frv_pf,
        "fv_pr": fv_pr, "frv_pr": frv_pr
    }

def get_F_pf_custom(df, No):
    # Pozitivni dejavniki pogosto zahtevajo minimalno vrednost 0.32 po vašem članku
    subset = df[df['tip'].str.contains('PF', na=False, case=False)]
    fv = len(subset)
    frv = subset['opis'].nunique()
    if fv == 0: return 0.32, 0, 1
    rho = fv / No
    Co = fv / frv if frv > 0 else 1
    return (Co * rho) / 10, fv, frv

# ============================================================
# 3. PROCESIRANJE (Batch Extraction)
# ============================================================
def run_intelligent_analysis(data_list, api_key, model_name):
    client = genai.Client(api_key=api_key)
    all_extracted = []
    
    # Razdelimo na pakete po 50 za natančnost
    batch_size = 50
    pb = st.progress(0)
    status = st.empty()
    
    for i in range(0, len(data_list), batch_size):
        batch = data_list[i : i + batch_size]
        batch_text = "\n".join([f"- {t}" for t in batch])
        
        prompt = f"""
        Extract ALL psychosocial factors based on Petrič (2025) model from the text below.
        For each response, identify multiple factors if present.
        Format: Return ONLY a JSON list of objects. 
        Structure: [{{ "tip": "SF/PF/PR", "enota": "At/St/So/PS/IP/HB", "opis": "standardized short label" }}]
        
        Text:
        {batch_text}
        """
        
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            clean_text = re.sub(r'```json|```', '', response.text).strip()
            match = re.search(r'\[.*\]', clean_text, re.DOTALL)
            if match:
                all_extracted.extend(json.loads(match.group()))
        except Exception as e:
            st.warning(f"Paket {i//batch_size + 1} ni uspel: {e}")
        
        pb.progress(min(1.0, (i + batch_size) / len(data_list)))
        status.text(f"Analiziram: {min(len(data_list), i+batch_size)} / {len(data_list)}")
        time.sleep(1) # Varnostni premor
        
    return pd.DataFrame(all_extracted)

# ============================================================
# 4. GLAVNI PROGRAM
# ============================================================
uploaded_file = st.file_uploader("📂 Naložite odgovore (.txt, .xlsx, .csv)", type=["txt", "xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df_in = pd.read_excel(uploaded_file)
        text_data = df_in.iloc[:, 0].dropna().astype(str).tolist()
    elif uploaded_file.name.endswith(".csv"):
        df_in = pd.read_csv(uploaded_file)
        text_data = df_in.iloc[:, 0].dropna().astype(str).tolist()
    else:
        text_data = uploaded_file.read().decode("utf-8").splitlines()
        text_data = [l.strip() for l in text_data if len(l) > 5]

    No = len(text_data)
    st.success(f"Zaznanih {No} respondentov.")

    if st.button("🚀 ZAŽENI KOMPLETNO ANALIZO"):
        if not api_key:
            st.error("Manjka API ključ!")
        else:
            with st.spinner("AI ekstrahira dejavnike (to bo trajalo ~20-30s)..."):
                extracted_df = run_intelligent_analysis(text_data, api_key, model_choice)
            
            if not extracted_df.empty:
                # Izračun
                res = calculate_petric_final(extracted_df, No, W_I_kcal)
                
                # --- PRIKAZ REZULTATOV ---
                st.divider()
                st.balloons()
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Stresna moč (σ)", f"{res['sigma']:.2f} °S")
                col_m2.metric("Učinkovitost (η)", f"{res['eff']:.1f} %")
                col_m3.metric("Uporabna energija", f"{int(res['w_eu'])} kcal")
                col_m4.metric("Izguba energije", f"{int(res['loss'])} kcal")

                st.divider()
                c1, c2 = st.columns([2, 1])
                
                with c1:
                    st.subheader("Slope Model (Slikovni prikaz vašega modela)")
                    # Izris nagiba stresa (Figure 1 v članku)
                    fig_slope = go.Figure()
                    fig_slope.add_trace(go.Scatter(x=[0, 90], y=[0, res['sigma']], mode='lines+markers', 
                                                 name='Izmerjen nagib', line=dict(color='red', width=4)))
                    fig_slope.update_layout(xaxis_title="Teoretični okvir (°S)", yaxis_title="Intenzivnost stresa",
                                          xaxis=dict(range=[0, 90]), yaxis=dict(range=[0, 90]))
                    st.plotly_chart(fig_slope, use_container_width=True)
                
                with c2:
                    st.subheader("Statistika frekvenc")
                    st.write(f"- Stresorji ($f_v$): {res['fv_sf']}")
                    st.write(f"- Pozitivni ($f_v$): {res['fv_pf']}")
                    st.write(f"- Predlogi ($f_v$): {res['fv_pr']}")
                    st.write("---")
                    st.write(f"**Realni faktorji ($F_o$):**")
                    st.write(f"SF: `{res['F_sf']:.4f}`")
                    st.write(f"PF: `{res['F_pf']:.4f}`")
                    st.write(f"PR: `{res['F_pr']:.4f}`")

                st.subheader("Struktura dejavnikov po enotah")
                fig_bar = px.histogram(extracted_df, x='enota', color='tip', barmode='group',
                                      category_orders={"enota": ["At", "St", "So", "PS", "IP", "HB"]},
                                      color_discrete_map={'SF':'#EF553B', 'PF':'#00CC96', 'PR':'#636EFA'})
                st.plotly_chart(fig_bar, use_container_width=True)

                with st.expander("Poglej vse izluščene dejavnike"):
                    st.dataframe(extracted_df)
            else:
                st.error("AI ni uspel izluščiti dejavnikov. Preverite API ključ ali format datoteke.")




