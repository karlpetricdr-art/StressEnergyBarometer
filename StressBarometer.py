import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. DEFINICIJA STOP-WORDS (MAŠILA) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bi", "bil", "bila", "bi", "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it"
}

# --- 2. KLASIFIKACIJSKI MODEL PO ČLANKU (Petrič, 2025) ---
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "lightning", "vročina", "mraz", "cold", "weather", 
        "vreme", "prostori", "office", "pisarna", "ergonomija", "equipment", "oprema", "tišina", "silence"
    ],
    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload", "naloge", "tasks", "čas", "time", "administration", 
        "birokracija", "informacije", "information", "skills", "znanje", "delovni čas", "urgency"
    ],
    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism", "pozitivno", "self-confidence", "samozavest", 
        "emotions", "čustva", "stres", "stress", "frustracija", "frustration", "peace", "mir"
    ],
    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance", "nagrada", "reward", "status", "recognition", 
        "priznanje", "poverty", "revščina", "standard", "inequality", "nepravičnost"
    ],
    "Social unit": [
        "odnosi", "relationships", "mobing", "mobbing", "bullying", "harassment", "sodelavci", "colleagues", 
        "šef", "boss", "družina", "family", "prijatelji", "friends", "komunikacija", "communication", "prepir"
    ],
    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport", "sports", "exercise", "prehrana", "diet", 
        "spanje", "sleep", "utrujenost", "tiredness", "joga", "yoga", "meditacija", "meditation"
    ]
}

# --- 3. POMOŽNE FUNKCIJE ZA OBDELAVO BESEDILA ---

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

def calculate_fo_real_detailed(df, col, n_o):
    """Natančen izračun vseh parametrov za Nivo 1 in 2."""
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
    
    if fr == 0 or n_o == 0: 
        return {"fo_real": 0.0001, "fo": 0, "fr": 0, "rho": 0, "co": 0}
    
    rho_o = fo / n_o
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    
    return {
        "fo_real": fo_real,
        "fo": fo,
        "fr": fr,
        "rho": rho_o,
        "co": c_o
    }

# --- 4. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Stress Power Pro - Petrič Method", layout="wide")
    st.title("📊 Celovita analiza stresne moči po Petričevi metodi")
    
    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        df = pd.read_csv(uploaded_file, sep=sep)
        n_o = len(df)
        
        st.sidebar.success(f"Vzorec: {n_o} respondentov.")

        # --- NIVO 1 & 2: KLASIFIKACIJA IN REALNI FAKTORJI ---
        target_cols = df.columns.tolist()
        stats = {}

        st.header("1. Pregled klasifikacije in realnih faktorjev ($F_o$)")
        
        # Izračunamo vse parametre za prve tri stolpce
        for i, col in enumerate(target_cols[:3]):
            stats[i] = calculate_fo_real_detailed(df, col, n_o)
            stats[i]["name"] = col

        # Prikaz parametrov v kolonah
        c1, c2, c3 = st.columns(3)
        cols_ui = [c1, c2, c3]
        
        for i in range(3):
            with cols_ui[i]:
                st.subheader(stats[i]["name"])
                st.write(f"Skupaj mnenj ($f_o$): **{stats[i]['fo']}**")
                st.write(f"Različnih mnenj ($f_r$): **{stats[i]['fr']}**")
                st.write(f"Gostota ($\\rho_o$): **{stats[i]['rho']:.2f}**")
                st.write(f"Kompleksnost ($C_o$): **{stats[i]['co']:.2f}**")
                st.info(f"Realni faktor **$F_o$: {stats[i]['fo_real']:.4f}**")

        # --- NIVO 3: IZRAČUN STRESNE MOČI (°S) ---
        st.divider()
        st.header("2. Izračun celokupne stresne moči (Nivo 3)")
        
        if len(target_cols) >= 3:
            f_pf = stats[0]["fo_real"]
            f_sf = stats[1]["fo_real"]
            f_pr = stats[2]["fo_real"]
            
            try:
                # Enačba 5: sigma = arcsin( sqrt( (F_sf * F_pr) / F_pf ) )
                argument = math.sqrt((f_sf * f_pr) / f_pf)
                sigma_rad = math.asin(min(argument, 1.0))
                sigma_deg = math.degrees(sigma_rad)
                
                res_col1, res_col2 = st.columns([1, 2])
                with res_col1:
                    st.metric("CELOKUPNA STRESNA MOČ", f"{sigma_deg:.2f} °S")
                    
                    # Psihosocialni barometer (Tabela 6)
                    if sigma_deg <= 15.04: eval_st, color = "Zelo nizka", "green"
                    elif sigma_deg <= 30.04: eval_st, color = "Nizka", "blue"
                    elif sigma_deg <= 45.04: eval_st, color = "Srednja", "orange"
                    else: eval_st, color = "Visoka", "red"
                    
                    st.markdown(f"Ocena po Petriču: **:{color}[{eval_st}]**")
                    
                with res_col2:
                    st.write("Vizualni prikaz stopnje stresa (0°S - 90°S):")
                    st.progress(min(sigma_deg / 90, 1.0))
                    if 30.0 <= sigma_deg <= 39.0:
                        st.success("Rezultat je znotraj znanstveno realnega razpona.")
                    else:
                        st.warning("Rezultat odstopa od pričakovanega razpona (30-39 °S).")

            except Exception as e:
                st.error(f"Matematična napaka: {e}")

        # --- FREKVENČNE TABELE PO ENOTAH ---
        st.divider()
        st.header("3. Frekvenčna porazdelitev po enotah")
        
        unit_tabs = st.tabs([stats[0]["name"], stats[1]["name"], stats[2]["name"]])
        
        for i, tab in enumerate(unit_tabs):
            with tab:
                col_name = stats[i]["name"]
                df[f'units_{col_name}'] = df[col_name].apply(lambda x: classify_keywords(clean_and_tokenize(x)))
                
                all_units = [unit for sublist in df[f'units_{col_name}'].tolist() for unit in sublist]
                unit_counts = Counter(all_units)
                
                freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca']).sort_values('Frekvenca', ascending=False)
                
                c_left, c_right = st.columns([2, 1])
                with c_left:
                    st.bar_chart(freq_df.set_index('Klasifikacijska enota'))
                with c_right:
                    st.table(freq_df)

    else:
        st.info("Naložite datoteko na levi strani za začetek analize.")

if __name__ == "__main__":
    main()



