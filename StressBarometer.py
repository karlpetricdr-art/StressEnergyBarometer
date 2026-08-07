import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. KONSTANTE IN PARAMETRI PO ČLANKU (Petrič, 2025) ---
RHO_T = 10    # Teoretična gostota (rho_t) - stran 39
C_T = 1       # Teoretična kompleksnost (C_t) - stran 39
SIGMA_W = 90  # Maksimalna moč v stopinjah za normalizacijo

# --- 2. DEFINICIJA STOP-WORDS (MAŠIL) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bi", "bil", "bila", "bi", "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it",
    "tudi", "zelo", "bolj", "tako", "lahko", "ali", "sem", "smo", "toda"
}

# --- 3. KLASIFIKACIJSKI MODEL (6 ENOT) ---
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "lightning", "vročina", "mraz", "vreme", 
        "prostori", "office", "pisarna", "tišina", "zrak", "prezračevanje", "hladen"
    ],
    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload", "naloge", "tasks", "čas", "time", 
        "birokracija", "informacije", "znanje", "delovni čas", "napor", "nadure", "hitrost"
    ],
    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism", "samozavest", "stres", 
        "mir", "napetost", "negativizem", "skrb", "frustracija", "osamljenost", "nemoč"
    ],
    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance", "nagrada", "priznanje", 
        "standard", "nepravičnost", "krivica", "dodatek", "izguba", "revščina"
    ],
    "Social unit": [
        "odnosi", "relationships", "mobing", "bullying", "sodelavci", "šef", "družina", 
        "prijatelji", "komunikacija", "prepir", "konflikt", "nezaupanje", "aroganca"
    ],
    "Health biological unit": [
        "zdravje", "health", "bolezen", "šport", "reakcija", "prehrana", "spanje", 
        "utrujenost", "joga", "meditacija", "izčrpanost", "diagnoza", "zdravnik"
    ]
}

# --- 4. FUNKCIJE ZA OBDELAVO IN MATEMATIKO ---

def clean_and_tokenize(text):
    """Očisti besedilo in izloči ključne besede."""
    if not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]

def get_detailed_stats(df, col_name, n_o):
    """
    Izračuna parametre po 1. in 2. nivoju Petričeve metode:
    fo = frekvenca vseh mnenj
    fr = frekvenca različnih mnenj
    rho_o = gostota mnenj na osebo
    c_o = kompleksnost
    f_o_real = realni faktor
    """
    all_hits = []
    for row in df[col_name].dropna():
        tokens = clean_and_tokenize(row)
        for t in tokens:
            for cat, kws in CATEGORIES_MAP.items():
                if any(kw in t for kw in kws):
                    all_hits.append(cat)
    
    f_o = len(all_hits)
    f_r = len(set(all_hits))
    
    # Preprečevanje deljenja z nič
    if n_o == 0: return 0, 0, 0, 0, 0
    if f_r == 0: f_r = 1 
    
    rho_o = f_o / n_o
    c_o = f_o / f_r
    f_o_real = (c_o * rho_o) / (C_T * RHO_T)
    
    return f_o, f_r, rho_o, c_o, f_o_real

# --- 5. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Stress Analysis Petrič Method", layout="wide")
    
    st.title("📊 Celovita analiza stresa po metodi Petrič (2025)")
    st.markdown("Analiza vključuje čiščenje besedila, klasifikacijo v 6 enot in izračun stresne moči v stopinjah (°S).")

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        # Nalaganje
        if uploaded_file.name.endswith('.txt'):
            df = pd.read_csv(uploaded_file, sep='\t')
        else:
            df = pd.read_csv(uploaded_file)

        n_o = len(df) # Število respondentov (sample size)
        st.sidebar.info(f"Število respondentov (No): {n_o}")

        # Identifikacija stolpcev
        cols = df.columns.tolist()
        col_pf = cols[0] if len(cols) > 0 else "" # Pozitivni
        col_sf = cols[1] if len(cols) > 1 else "" # Stresni (Negativni)
        col_pr = cols[2] if len(cols) > 2 else "" # Predlogi

        # 1. DEL: KLASIFIKACIJA IN FREKVENCE
        st.header("1. Klasifikacija in frekvenčna analiza")
        
        col_stats = {}
        tabs = st.tabs(["Stresni dejavniki", "Pozitivni dejavniki", "Predlogi za redukcijo"])
        
        mapping = {
            "Stresni dejavniki": col_sf,
            "Pozitivni dejavniki": col_pf,
            "Predlogi za redukcijo": col_pr
        }

        for i, (tab_name, real_col) in enumerate(mapping.items()):
            with tabs[i]:
                f_o, f_r, rho_o, c_o, f_o_real = get_detailed_stats(df, real_col, n_o)
                col_stats[tab_name] = {
                    "fo": f_o, "fr": f_r, "rho": rho_o, "co": c_o, "fo_real": f_o_real
                }
                
                st.subheader(f"Rezultati za: {real_col}")
                
                # Prikaz izračunanih parametrov
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Vsa mnenja (fo)", f_o)
                m2.metric("Različna (fr)", f_r)
                m3.metric("Gostota (ρo)", round(rho_o, 3))
                m4.metric("Realni faktor (Fo)", round(f_o_real, 3))

                # Tabela besed po enotah
                unit_hits = []
                for row in df[real_col].dropna():
                    tokens = clean_and_tokenize(row)
                    row_units = []
                    for t in tokens:
                        for cat, kws in CATEGORIES_MAP.items():
                            if any(kw in t for kw in kws): row_units.append(cat)
                    unit_hits.extend(row_units)
                
                counts = Counter(unit_hits)
                freq_df = pd.DataFrame(counts.items(), columns=['Klasifikacijska enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
                st.table(freq_df)

        # 2. DEL: IZRAČUN CELOKUPNE STRESNE MOČI (°S)
        st.divider()
        st.header("2. Izračun celokupne stresne moči")

        # Pridobivanje realnih faktorjev (F_sf, F_pf, F_pr)
        f_sf = col_stats["Stresni dejavniki"]["fo_real"]
        f_pf = col_stats["Pozitivni dejavniki"]["fo_real"]
        f_pr = col_stats["Predlogi za redukcijo"]["fo_real"]

        if f_pf > 0:
            # FORMULA (Equation 27): arcsin( sqrt( (F_sf * F_pr) / F_pf ) )
            try:
                inner_sqrt = math.sqrt((f_sf * f_pr) / f_pf)
                # Vrednost v arcsin ne sme biti večja od 1
                inner_val = min(inner_sqrt, 1.0)
                sigma_rad = math.asin(inner_val)
                sigma_deg = math.degrees(sigma_rad)
            except Exception as e:
                sigma_deg = 0
                st.warning(f"Napaka pri izračunu: {e}")
        else:
            sigma_deg = 0

        # Prikaz rezultata
        c_left, c_right = st.columns([1, 2])
        
        with c_left:
            st.metric("Celokupna stresna moč", f"{round(sigma_deg, 2)} °S")
            
            # Interpretacija po Tabeli 6
            if sigma_deg <= 15.04: eval_st = "Zelo nizka (Very low)"
            elif sigma_deg <= 30.04: eval_st = "Nizka (Low)"
            elif sigma_deg <= 45.04: eval_st = "Srednja (Medium)"
            elif sigma_deg <= 60.04: eval_st = "Višja (Higher)"
            elif sigma_deg <= 75.04: eval_st = "Visoka (High)"
            else: eval_st = "Zelo visoka (Very high)"
            
            st.subheader(f"Ocena: {eval_st}")

        with c_right:
            # Vizualni prikaz s progresno vrstico
            st.write("Psihosocialni barometer (0°S - 90°S)")
            st.progress(min(sigma_deg / 90, 1.0))
            
            # Tabela realnih faktorjev za povzetek
            summary_data = {
                "Parameter": ["Realni faktor SF (Negativni)", "Realni faktor PF (Pozitivni)", "Realni faktor PR (Predlogi)"],
                "Vrednost (Fo)": [round(f_sf, 4), round(f_pf, 4), round(f_pr, 4)]
            }
            st.table(pd.DataFrame(summary_data))

        # 3. DEL: POVZETEK PO KATEGORIJAH (Frekvence)
        st.divider()
        st.subheader("Skupni grafični prikaz frekvenc po enotah")
        
        # Priprava podatkov za graf
        all_data_frames = []
        for cat_name, col_real in mapping.items():
            unit_hits = []
            for row in df[col_real].dropna():
                tokens = clean_and_tokenize(row)
                for t in tokens:
                    for cat, kws in CATEGORIES_MAP.items():
                        if any(kw in t for kw in kws): unit_hits.append(cat)
            
            temp_df = pd.DataFrame(Counter(unit_hits).items(), columns=['Enota', 'Frekvenca'])
            temp_df['Tip'] = cat_name
            all_data_frames.append(temp_df)
        
        combined_df = pd.concat(all_data_frames)
        pivot_df = combined_df.pivot(index='Enota', columns='Tip', values='Frekvenca').fillna(0)
        st.bar_chart(pivot_df)

    else:
        st.info("Naložite datoteko z odgovori (stolpci morajo biti v vrstnem redu: Pozitivni, Stresni, Predlogi).")

if __name__ == "__main__":
    main()



