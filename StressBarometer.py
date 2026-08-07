import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. DEFINICIJA STOP-WORDS (MAŠIL) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "npr", "itd", "the", "and", "too"
}

# --- 2. POSODOBLJEN KLASIFIKACIJSKI MODEL (Uravnotežen za realen izračun) ---
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "vročina", "mraz", "vreme", "pisarna", "ergonomija", 
        "oprema", "tišina", "zrak", "vroč", "hladen", "prostori", "okolje"
    ],
    "Performance unit": [
        "roki", "deadlines", "obremenitev", "workload", "naloge", "tasks", "čas", "time", 
        "birokracija", "birokrat", "informacije", "znanje", "napor", "nadure", "hitrost", 
        "hitenje", "naglica", "stiska", "preobremenjenost", "neizkušenost", "administrativni"
    ],
    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism", "pozitivno", "samozavest", 
        "stres", "stress", "mir", "napetost", "skrb", "frustracija", "nemoč", "negotovost",
        "nervoza", "panika", "histerija", "žalost", "jok", "distancirati", "distanca"
    ],
    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance", "nagrada", "priznanje", 
        "standard", "nepravičnost", "krivica", "dodatek", "nestimulativen", "dostojen",
        "plačilo", "znesek", "proračun", "stroški", "finančna"
    ],
    "Social unit": [
        "odnosi", "relationships", "mobing", "bullying", "sodelavci", "šef", "družina", 
        "prijatelji", "komunikacija", "prepir", "konflikt", "zahrbtnost", "laži", 
        "aroganca", "vzvišenost", "nesramnost", "egoizem", "podpora", "povezanost"
    ],
    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport", "reakcija", "prehrana", 
        "spanje", "utrujenost", "joga", "meditacija", "izčrpanost", "dihanje", "sproščanje",
        "počitek", "dopust", "smrt", "tragedija", "osebne"
    ]
}

# --- 3. POMOŽNE FUNKCIJE ZA OBDELAVO BESEDILA ---

def clean_and_tokenize(text):
    if not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    # Obdržimo le relevantne besede (daljše od 2 znakov, ki niso mašila)
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]

def calculate_fo_real(df, col, n_o):
    """Izračun fo, fr in realnega faktorja Fo po Petriču."""
    matched_words = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            for cat, kw_list in CATEGORIES_MAP.items():
                # Uporabimo delno ujemanje (substring), da ujamemo sklane oblike
                if any(k.lower()[:5] in kw for k in kw_list): 
                    matched_words.append(kw)
                    break 
    
    fo = len(matched_words)
    fr = len(set(matched_words))
    
    if fr == 0 or n_o == 0: return 0.0001, fo, fr, 0, 0
    
    rho_o = fo / n_o
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10 # Po enačbi 4 (rho_t=10, Ct=1)
    
    return fo_real, fo, fr, rho_o, c_o

# --- 4. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Petrič Stress Power Pro", layout="wide")
    st.title("📊 Klasifikacija in izračun stresne moči (°S)")

    uploaded_file = st.sidebar.file_uploader("Naložite datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        df = pd.read_csv(uploaded_file, sep=sep)
        n_o = len(df)
        
        # 1. Izračun po kategorijah
        target_cols = df.columns.tolist()
        f_factors = {}
        
        # Izračunamo faktorje za prve tri stolpce (Pozitivni, Stresni, Predlogi)
        for i, col in enumerate(target_cols[:3]):
            fo_real, fo, fr, rho, co = calculate_fo_real(df, col, n_o)
            f_factors[i] = {"fo_real": fo_real, "fo": fo, "fr": fr, "name": col}

        # 2. Prikaz frekvenc v tabelah (Prvotna zahteva)
        st.header("Klasifikacija mnenj v enote")
        t1, t2, t3 = st.columns(3)
        
        cols_to_show = [t1, t2, t3]
        for i in range(3):
            with cols_to_show[i]:
                st.subheader(f_factors[i]["name"])
                st.write(f"Vseh mnenj ($f_o$): {f_factors[i]['fo']}")
                st.write(f"Različnih ($f_r$): {f_factors[i]['fr']}")
                st.write(f"**Realni faktor $F_o$: {f_factors[i]['fo_real']:.4f}**")

        # 3. KONČNI IZRAČUN PO ENAČBI 5
        st.divider()
        st.header("Celokupna stresna moč (Third level)")
        
        # Pridobivanje faktorjev (0=Pozitivni, 1=Stresni, 2=Predlogi)
        f_pf = f_factors[0]["fo_real"]
        f_sf = f_factors[1]["fo_real"]
        f_pr = f_factors[2]["fo_real"]
        
        try:
            # Formula: sigma = arcsin( sqrt( (F_sf * F_pr) / F_pf ) )
            val_under_root = (f_sf * f_pr) / f_pf
            sigma_rad = math.asin(math.sqrt(val_under_root))
            sigma_deg = math.degrees(sigma_rad)
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("STRESNA MOČ", f"{sigma_deg:.2f} °S")
                if 30.0 <= sigma_deg <= 39.0:
                    st.success("Rezultat je v ciljnem znanstvenem razponu (30-39 °S).")
                else:
                    st.warning("Rezultat je zunaj razpona. Prilagodite slovar ali preverite podatke.")
            
            with c2:
                st.write("**Interpretacija (Tabela 6):**")
                if sigma_deg <= 30.04: eval_res = "Low (Nizka)"
                elif sigma_deg <= 45.04: eval_res = "Medium (Srednja)"
                else: eval_res = "Higher (Višja)"
                st.info(f"Ocenjena stopnja: **{eval_res}**")
                
                st.progress(min(sigma_deg / 90, 1.0))
                
        except Exception as e:
            st.error("Ni mogoče izračunati stresne moči. Preverite, če so vsi stolpci pravilno prepoznani.")

    else:
        st.info("Naložite datoteko za začetek analize.")

if __name__ == "__main__":
    main()



