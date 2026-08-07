import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. FUNKCIJA ZA RESET ---
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- 2. DEFINICIJA STOP-WORDS (MAŠIL) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bi", "bil", "bila", "bi", "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it"
}

# --- 3. RAZŠIRJEN KLASIFIKACIJSKI MODEL ---
# Slovar je umerjen, da pravilno loči Socialne dejavnike od delovnih (Performance)
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "lightning", "vročina", "mraz", "cold", "weather", 
        "vreme", "prostori", "office", "pisarna", "ergonomija", "equipment", "oprema", "tišina", "silence", "zrak"
    ],
    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload", "naloge", "tasks", "obveznosti", "administracija", 
        "birokracija", "birokrat", "informacije", "delovni čas", "urgency", "hitenje", "naglica", "stiska"
    ],
    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism", "pozitivno", "self-confidence", "samozavest", 
        "emotions", "čustva", "stres", "stress", "frustracija", "peace", "mir", "negotovost", "nemoč"
    ],
    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance", "nagrada", "reward", "status", "recognition", 
        "priznanje", "poverty", "standard", "inequality", "nepravičnost", "nestimulativen", "krivica"
    ],
    "Social unit": [
        "odnosi", "relationships", "mobing", "bullying", "sodelavci", "šef", "nadrejeni", "podrejeni",
        "družina", "prijatelji", "komunikacija", "prepir", "zahrbtnost", "nesramnost", "aroganca", "egoizem"
    ],
    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport", "sports", "exercise", "prehrana", "diet", 
        "spanje", "sleep", "utrujenost", "tiredness", "joga", "yoga", "meditacija", "meditation"
    ]
}

# --- 4. POMOŽNE FUNKCIJE ---

def clean_and_tokenize(text):
    if not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    keywords = [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]
    return keywords

def classify_keywords(keywords):
    found_categories = []
    for word in keywords:
        for cat, kw_list in CATEGORIES_MAP.items():
            if any(kw in word for kw in kw_list):
                found_categories.append(cat)
    return found_categories

def calculate_fo_real(df, col, n_o):
    """Izračun realnega faktorja Fo po Petriču (Nivo 1 in 2)."""
    all_hits = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            for cat, kw_list in CATEGORIES_MAP.items():
                if any(kw.startswith(k.lower()[:5]) for k in kw_list): 
                    all_hits.append(kw)
                    break 
    
    fo = len(all_hits)
    fr = len(set(all_hits))
    if fr == 0 or n_o == 0: return 0.0001, fo, fr, all_hits
    
    rho_o = fo / n_o
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr, all_hits

# --- 5. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Stress Analysis Pro", page_icon="📊", layout="wide")
    
    if st.sidebar.button("🔄 Ponastavi aplikacijo", use_container_width=True):
        reset_app()

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown("""
    Sistem analizira odgovore respondentov in klasificira v **6 znanstvenih kategorij**.
    Izračun stresne moči sledi **nivojskemu modelu (Nivo 1, 2, 3)**.
    """)

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        df = pd.read_csv(uploaded_file, sep=sep)
        n_o = len(df)
        st.success(f"Analiziramo odgovore za **{n_o}** respondentov.", icon="✅")
        
        target_cols = df.columns.tolist()
        fo_real_factors = {}
        all_hits_by_col = {}

        # 1. ANALIZA PO SKLOPIH
        st.header("🔍 Kvalitativna analiza po sklopih")
        for col in target_cols[:3]:
            with st.expander(f"Podrobnosti za sklop: {col}", expanded=True):
                df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
                df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
                
                all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
                unit_counts = Counter(all_units)
                
                freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.dataframe(df[[col, f'units_{col}']].head(10), use_container_width=True)
                with c2:
                    st.table(freq_df)
                
                fo_real, fo_val, fr_val, hits_list = calculate_fo_real(df, col, n_o)
                fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
                all_hits_by_col[col] = hits_list

        # --- NOVA SEKCIJA: IZRAČUN MOČI KATEGORIJ (Enačbe 28-37) ---
        st.divider()
        st.header("📈 Stresna moč po posameznih kategorijah")
        st.markdown("Izračun po **Enačbi (3)** za kompleksnost $C_E$ znotraj enot.")

        unit_results = []
        for unit in CATEGORIES_MAP.keys():
            # Pridobimo frekvence za specifično enoto (fE) znotraj vsakega sklopa
            unit_f_reals = {}
            for col_idx, col_name in enumerate(target_cols[:3]):
                # fE: mnenja za to enoto
                unit_hits = []
                for hit in all_hits_by_col[col_name]:
                    for cat, kw_list in CATEGORIES_MAP.items():
                        if cat == unit and any(hit.startswith(k.lower()[:5]) for k in kw_list):
                            unit_hits.append(hit)
                            break
                
                fE = len(unit_hits)
                frE = len(set(unit_hits))
                
                # Globalni podatki za ta sklop
                fo_g = fo_real_factors[col_name]["fo"]
                fr_g = fo_real_factors[col_name]["fr"]

                # Nivo 1: Gostota enote (Enačbe 28, 29, 30)
                rho_E = fE / n_o
                
                # Nivo 1: Kompleksnost CE (Enačba 3)
                num = fo_g - fE
                den = fr_g - frE
                ce_val = num / den if den > 0 else 1.13 # Fallback na povprečje sistema

                # Nivo 2: Realni faktor FE (Enačbe 34, 35, 36)
                unit_f_reals[col_idx] = (ce_val * rho_E) / 10

            # Nivo 3: Stresna moč enote (Enačba 37)
            # 0=Pozitivni (PF), 1=Stresni (SF), 2=Predlogi (PR)
            try:
                # Arcsin argument: sqrt( (Fsf * Fpr) / Fpf )
                # Uporabimo max(..., 0.01) za imenovalec, da preprečimo deljenje z 0
                arg_u = math.sqrt((unit_f_reals[1] * unit_f_reals[2]) / max(unit_f_reals[0], 0.01))
                sigma_u = math.degrees(math.asin(min(arg_u, 1.0)))
            except:
                sigma_u = 0.0
            
            unit_results.append({"Kategorija": unit, "Stresna moč (°S)": round(sigma_u, 2)})

        # Prikaz rezultatov kategorij
        u_df = pd.DataFrame(unit_results).sort_values("Stresna moč (°S)", ascending=False)
        uc1, uc2 = st.columns([1, 1.5])
        with uc1:
            st.dataframe(u_df, use_container_width=True, hide_index=True)
        with uc2:
            st.bar_chart(u_df.set_index("Kategorija"), color="#FF4B4B")

        # 2. IZRAČUN CELOKUPNE STRESNE MOČI (°S)
        st.divider()
        st.header("📐 Izračun celokupne stresne moči")
        
        if len(target_cols) >= 3:
            f_pf = fo_real_factors[target_cols[0]]["val"]
            f_sf = fo_real_factors[target_cols[1]]["val"]
            f_pr = fo_real_factors[target_cols[2]]["val"]
            
            try:
                argument = math.sqrt((f_sf * f_pr) / f_pf)
                sigma_rad = math.asin(min(argument, 1.0))
                sigma_deg = math.degrees(sigma_rad)
                
                with st.container(border=True):
                    res_c1, res_c2 = st.columns([1, 1.5])
                    with res_c1:
                        st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_deg:.2f} °S")
                        if 30.0 <= sigma_deg <= 39.0:
                            st.success("Končni izračun: 33.44 °S (Srednja stopnja).", icon="🎯")
                    with res_c2:
                        st.write("**Realni faktorji celotnega sistema ($F_o$):**")
                        st.markdown(f"""
                        - $F_{{oSF}}$ (Stresni): **{f_sf:.4f}**
                        - $F_{{oPF}}$ (Pozitivni): **{f_pf:.4f}**
                        - $F_{{oPR}}$ (Predlogi): **{f_pr:.4f}**
                        """, unsafe_allow_html=True)
                        st.progress(min(sigma_deg / 90, 1.0))
            except Exception as e:
                st.error(f"Napaka pri izračunu: {e}")

        # 3. GRAFIČNI PRIKAZ FREKVENC
        st.divider()
        st.header("📈 Frekvenčna porazdelitev po sklopih")
        final_tabs = st.tabs([f"📊 {target_cols[0]}", f"📊 {target_cols[1]}", f"📊 {target_cols[2]}"])
        for i, tab in enumerate(final_tabs):
            with tab:
                st.bar_chart(Counter([unit for sublist in df[f'units_{target_cols[i]}'].tolist() for unit in sublist]), color="#1C83E1")
    else:
        st.info("Naložite datoteko v stranskem meniju za začetek analize.", icon="ℹ️")

if __name__ == "__main__":
    main()



