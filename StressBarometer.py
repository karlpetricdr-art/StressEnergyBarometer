import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. DEFINICIJA STOP-WORDS (MAŠIL) ---
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

# Funkcija za izračun realnega faktorja Fo po nivojih 1 in 2
def calculate_fo_real(df, col, n_o):
    all_keywords_in_cat = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            # Preverimo vsako besedo iz odgovora
            for cat, kw_list in CATEGORIES_MAP.items():
                # STROŽJE UJEMANJE: beseda se mora natančno ujemati 
                # ali pa biti koren besede (npr. 'družin' v 'družina')
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

# --- 4. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Stress Analysis Pro", layout="wide")
    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown("""
    Sistem analizira odgovore respondentov, odstrani mašila, izlušči udarne besede 
    ter jih klasificira v **6 znanstvenih kategorij** (Petrič, 2025).
    """)

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        if uploaded_file.name.endswith('.txt'):
            df = pd.read_csv(uploaded_file, sep='\t')
        else:
            df = pd.read_csv(uploaded_file)

        n_o = len(df)
        st.success(f"Uspešno naloženo: {n_o} vrstic.")
        
        with st.expander("Pregled surovih podatkov"):
            st.dataframe(df.head())

        target_cols = df.columns.tolist()
        results = {}
        fo_real_factors = {}

        # Analiza po kategorijah
        for col in target_cols:
            st.subheader(f"🔍 Analiza: {col}")
            
            df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
            df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
            
            all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
            unit_counts = Counter(all_units)
            
            freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca'])
            freq_df = freq_df.sort_values(by='Frekvenca', ascending=False)
            
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write("Klasificirani podatki po vrsticah:")
                st.dataframe(df[[col, f'keywords_{col}', f'units_{col}']].head(10))
            
            with c2:
                st.write("Tabela frekvenc enot:")
                st.table(freq_df)
            
            # Izračun realnega faktorja Fo za ta stolpec
            fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_o)
            fo_real_factors[col] = fo_real
            results[col] = freq_df

        # --- IZRAČUN CELOKUPNE STRESNE MOČI (°S) ---
        st.divider()
        st.header("📐 Izračun celokupne stresne moči (Third level)")
        
        # Preverimo, če imamo vse tri potrebne stolpce za enačbo 5
        if len(target_cols) >= 3:
            # Po vrstnem redu: 0=Pozitivni, 1=Stresni, 2=Predlogi
            f_pf = fo_real_factors[target_cols[0]]
            f_sf = fo_real_factors[target_cols[1]]
            f_pr = fo_real_factors[target_cols[2]]
            
            try:
                # Enačba: sigma = arcsin( sqrt( (F_sf * F_pr) / F_pf ) )
                argument = math.sqrt((f_sf * f_pr) / f_pf)
                # Omejitev argumenta na max 1.0 za arcsin funkcijo
                sigma_rad = math.asin(min(argument, 1.0))
                sigma_deg = math.degrees(sigma_rad)
                
                # Izpis rezultatov
                res_c1, res_c2 = st.columns(2)
                with res_c1:
                    st.metric("CELOKUPNA STRESNA MOČ", f"{sigma_deg:.2f} °S")
                    if 30.0 <= sigma_deg <= 39.0:
                        st.success("Rezultat je v realnem razponu (30-39 °S).")
                    else:
                        st.warning("Rezultat odstopa od pričakovanega razpona (30-39 °S). Preverite nabor ključnih besed.")
                
                with res_c2:
                    st.write("**Realni faktorji (Fo):**")
                    st.write(f"- Fo_SF (Stresni): {f_sf:.4f}")
                    st.write(f"- Fo_PF (Pozitivni): {f_pf:.4f}")
                    st.write(f"- Fo_PR (Predlogi): {f_pr:.4f}")
            except Exception as e:
                st.error(f"Napaka pri izračunu stresne moči: {e}")
        else:
            st.error("Za izračun stresne moči potrebujete 3 stolpce: Pozitivni, Stresni in Predlogi.")

        # --- CELOKUPNI VPOGLED ---
        st.divider()
        st.header("📈 Skupni frekvenčni pregled")
        
        final_tabs = st.tabs(target_cols)
        for i, tab in enumerate(final_tabs):
            with tab:
                col_name = target_cols[i]
                st.bar_chart(results[col_name].set_index('Klasifikacijska enota'))

    else:
        st.info("Prosim, naložite datoteko na levi strani, da pričnemo z analizo.")

if __name__ == "__main__":
    main()



