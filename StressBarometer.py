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
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "lightning", "vročina", "mraz", "cold", "weather", 
        "vreme", "prostori", "office", "pisarna", "ergonomija", "equipment", "oprema", "tišina", "silence", "zrak"
    ],
    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload", "naloge", "tasks", "čas", "time", "administration", 
        "birokracija", "birokrat", "informacije", "information", "skills", "znanje", "delovni čas", "urgency",
        "hitenje", "naglica", "stiska", "preobremenjenost", "neizkušenost", "administrativni"
    ],
    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism", "pozitivno", "self-confidence", "samozavest", 
        "emotions", "čustva", "stres", "stress", "frustracija", "frustration", "peace", "mir",
        "negotovost", "nervoza", "panika", "nemoč", "skrb", "napetost"
    ],
    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance", "nagrada", "reward", "status", "recognition", 
        "priznanje", "poverty", "revščina", "standard", "inequality", "nepravičnost", "nestimulativen",
        "krivica", "dostojen", "plačilo", "finančna"
    ],
    "Social unit": [
        "odnosi", "relationships", "mobing", "mobbing", "bullying", "harassment", "sodelavci", "colleagues", 
        "šef", "boss", "družina", "family", "prijatelji", "friends", "komunikacija", "communication", "prepir",
        "zahrbtnost", "vzvišenost", "nesramnost", "aroganca", "egoizem", "podpora"
    ],
    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport", "sports", "exercise", "prehrana", "diet", 
        "spanje", "sleep", "utrujenost", "tiredness", "joga", "yoga", "meditacija", "meditation",
        "izčrpanost", "dihanje", "sproščanje", "počitek", "dopust"
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
    all_keywords_in_cat = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            for cat, kw_list in CATEGORIES_MAP.items():
                if any(kw.startswith(k.lower()[:5]) for k in kw_list): 
                    all_keywords_in_cat.append(kw)
                    break 
    
    fo = len(all_keywords_in_cat)
    fr = len(set(all_keywords_in_cat))
    if fr == 0 or n_o == 0: return 0.0001, fo, fr
    
    rho_o = fo / n_o
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr

# --- 5. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Stress Analysis Pro", page_icon="📊", layout="wide")
    
    # Reset gumb v sidebarju
    with st.sidebar:
        st.header("Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown("""
    Sistem analizira odgovore respondentov, izloči mašila in klasificira v **6 znanstvenih kategorij**.
    Izračun stresne moči sledi **3. nivoju Petričeve metode**.
    """)

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        df = pd.read_csv(uploaded_file, sep=sep)
        n_o = len(df)
        st.success(f"Datoteka uspešno naložena. Analiziramo odgovore za **{n_o}** respondentov.", icon="✅")
        
        target_cols = df.columns.tolist()
        results = {}
        fo_real_factors = {}

        # 1. ANALIZA PO KATEGORIJAH
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
                    st.caption("Klasificirani podatki (prvih 10 vrstic):")
                    st.dataframe(df[[col, f'units_{col}']].head(10), use_container_width=True)
                with c2:
                    st.caption("Frekvence znanstvenih enot:")
                    st.table(freq_df)
                
                fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_o)
                fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
                results[col] = freq_df

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
                
                # Estetski prikaz rezultata
                with st.container(border=True):
                    res_c1, res_c2 = st.columns([1, 1.5])
                    with res_c1:
                        st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_deg:.2f} °S")
                        
                        # Interpretacija stopnje
                        if sigma_deg <= 15.04:
                            st.info("Stopnja: Zelo nizka (Very low)")
                        elif sigma_deg <= 30.04:
                            st.info("Stopnja: Nizka (Low)")
                        elif sigma_deg <= 45.04:
                            st.warning("Stopnja: Srednja (Medium)")
                        else:
                            st.error("Stopnja: Višja / Visoka (High)")

                        if 30.0 <= sigma_deg <= 39.0:
                            st.success("Rezultat je znotraj realnega znanstvenega razpona.", icon="🎯")
                    
                    with res_c2:
                        st.write("**Realni faktorji ($F_o$):**")
                        st.markdown(f"""
                        - $F_{{oSF}}$ (Stresni): **{f_sf:.4f}** <small>(zadetkov: {fo_real_factors[target_cols[1]]['fo']})</small>
                        - $F_{{oPF}}$ (Pozitivni): **{f_pf:.4f}** <small>(zadetkov: {fo_real_factors[target_cols[0]]['fo']})</small>
                        - $F_{{oPR}}$ (Predlogi): **{f_pr:.4f}** <small>(zadetkov: {fo_real_factors[target_cols[2]]['fo']})</small>
                        """, unsafe_allow_html=True)
                        st.progress(min(sigma_deg / 90, 1.0))
                        st.caption("Psihosocialni barometer stresa (0°S - 90°S)")
            except Exception as e:
                st.error(f"Napaka pri matematičnem izračunu: {e}")

        # 3. GRAFIČNI PRIKAZ
        st.divider()
        st.header("📈 Frekvenčna porazdelitev")
        final_tabs = st.tabs([f"📊 {target_cols[0]}", f"📊 {target_cols[1]}", f"📊 {target_cols[2]}"])
        for i, tab in enumerate(final_tabs):
            with tab:
                st.bar_chart(results[target_cols[i]].set_index('Klasifikacijska enota'), color="#1C83E1")
    else:
        st.info("Naložite datoteko v stranskem meniju za začetek analize.", icon="ℹ️")

if __name__ == "__main__":
    main()



