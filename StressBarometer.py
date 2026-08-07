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

# --- 3. RAZŠIRJEN KLASIFIKACIJSKI MODEL (Za rezultat > 30 °S) ---
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
                # Uporabimo startswith za natančnost in substrings za prožnost
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
    st.set_page_config(page_title="Stress Analysis Pro", layout="wide")
    
    # Reset gumb v sidebarju
    if st.sidebar.button("🔄 Ponastavi aplikacijo"):
        reset_app()

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown("""
    Sistem analizira odgovore respondentov, izloči mašila in klasificira v **6 znanstvenih kategorij**.
    Izračun stresne moči sledi 3. nivoju Petričeve metode.
    """)

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        df = pd.read_csv(uploaded_file, sep=sep)
        n_o = len(df)
        st.success(f"Uspešno naloženo: {n_o} vrstic.")
        
        target_cols = df.columns.tolist()
        results = {}
        fo_real_factors = {}

        # 1. ANALIZA PO KATEGORIJAH
        for col in target_cols[:3]:
            st.subheader(f"🔍 Analiza: {col}")
            
            df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
            df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
            
            all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
            unit_counts = Counter(all_units)
            
            freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write("Klasificirani podatki po vrsticah (top 10):")
                st.dataframe(df[[col, f'units_{col}']].head(10))
            with c2:
                st.write("Tabela frekvenc enot:")
                st.table(freq_df)
            
            fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_o)
            fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
            results[col] = freq_df

        # 2. IZRAČUN CELOKUPNE STRESNE MOČI (°S)
        st.divider()
        st.header("📐 Izračun celokupne stresne moči (Third level)")
        
        if len(target_cols) >= 3:
            f_pf = fo_real_factors[target_cols[0]]["val"]
            f_sf = fo_real_factors[target_cols[1]]["val"]
            f_pr = fo_real_factors[target_cols[2]]["val"]
            
            try:
                argument = math.sqrt((f_sf * f_pr) / f_pf)
                sigma_rad = math.asin(min(argument, 1.0))
                sigma_deg = math.degrees(sigma_rad)
                
                res_c1, res_c2 = st.columns(2)
                with res_c1:
                    st.metric("CELOKUPNA STRESNA MOČ", f"{sigma_deg:.2f} °S")
                    if 30.0 <= sigma_deg <= 39.0:
                        st.success("Rezultat je v realnem znanstvenem razponu (30-39 °S).")
                    else:
                        st.warning("Rezultat odstopa od razpona. Preverite slovar.")
                
                with res_c2:
                    st.write("**Realni faktorji ($F_o$):**")
                    st.write(f"- $F_{{oSF}}$ (Stresni): {f_sf:.4f} (mnenj: {fo_real_factors[target_cols[1]]['fo']})")
                    st.write(f"- $F_{{oPF}}$ (Pozitivni): {f_pf:.4f} (mnenj: {fo_real_factors[target_cols[0]]['fo']})")
                    st.write(f"- $F_{{oPR}}$ (Predlogi): {f_pr:.4f} (mnenj: {fo_real_factors[target_cols[2]]['fo']})")
                    st.progress(min(sigma_deg / 90, 1.0))
            except Exception as e:
                st.error(f"Napaka pri izračunu: {e}")

        # 3. GRAFIČNI PRIKAZ
        st.divider()
        st.header("📈 Skupni frekvenčni pregled")
        final_tabs = st.tabs(target_cols[:3])
        for i, tab in enumerate(final_tabs):
            with tab:
                st.bar_chart(results[target_cols[i]].set_index('Klasifikacijska enota'))
    else:
        st.info("Naložite datoteko za začetek.")

if __name__ == "__main__":
    main()



