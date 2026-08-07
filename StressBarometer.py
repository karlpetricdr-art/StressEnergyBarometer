import streamlit as st
import pandas as pd
import re
from collections import Counter

# --- 1. DEFINICIJA STOP-WORDS (MAŠIL) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bi", "bil", "bila", "bi", "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it"
}

# --- 2. KLASIFIKACIJSKI MODEL PO ČLANKU (Petrič, 2025) ---
# Mapiranje ključnih besed v 6 znanstvenih kategorij
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
    """Očisti besedilo, odstrani mašila in vrne ključne besede."""
    if not isinstance(text, str): return []
    # Čiščenje znakov in pretvorba v male črke
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    # Razbitje na besede
    words = text.split()
    # Filtriranje: odstrani stop-words in besede krajše od 3 znakov
    keywords = [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]
    return keywords

def classify_keywords(keywords):
    """Razvrsti ključne besede v 6 kategorij po Petričevi metodi."""
    found_categories = []
    for word in keywords:
        for cat, kw_list in CATEGORIES_MAP.items():
            if any(kw in word for kw in kw_list): # Delno ujemanje (koren besede)
                found_categories.append(cat)
    return found_categories

# --- 4. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Stress Analysis Pro", layout="wide")
    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown("""
    Sistem analizira odgovore respondentov, odstrani mašila, izlušči udarne besede 
    ter jih klasificira v **6 znanstvenih kategorij** (Petrič, 2025).
    """)

    # Nalaganje podatkov
    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        # Branje datoteke (prilagojeno vaši strukturi s tabulatorji)
        if uploaded_file.name.endswith('.txt'):
            df = pd.read_csv(uploaded_file, sep='\t')
        else:
            df = pd.read_csv(uploaded_file)

        st.success(f"Uspešno naloženo: {len(df)} vrstic.")
        
        # Prikaz surovih podatkov
        with st.expander("Pregled surovih podatkov"):
            st.dataframe(df.head())

        # Stolpci v vaši datoteki: "Pozitivni dejavniki", "Stresni dejavniki", "Predlogi za redukcijo stresa"
        target_cols = df.columns.tolist()
        
        # Analiza za vsako kategorijo posebej
        results = {}
        
        for col in target_cols:
            st.subheader(f"🔍 Analiza: {col}")
            
            # 1. Čiščenje in ekstrakcija ključnih besed
            df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
            
            # 2. Klasifikacija v Petričeve enote
            df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
            
            # 3. Izračun frekvenc za toplo tabelo
            all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
            unit_counts = Counter(all_units)
            
            # Priprava tabele s frekvencami
            freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca'])
            freq_df = freq_df.sort_values(by='Frekvenca', ascending=False)
            
            # Prikaz rezultatov v dveh stolpcih
            c1, c2 = st.columns([2, 1])
            with c1:
                st.write("Klasificirani podatki po vrsticah:")
                st.dataframe(df[[col, f'keywords_{col}', f'units_{col}']].head(10))
            
            with c2:
                st.write("Tabela frekvenc enot:")
                st.table(freq_df)
                
            # Shranjevanje za celokupni povzetek
            results[col] = freq_df

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




