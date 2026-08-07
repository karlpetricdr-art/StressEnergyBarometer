import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. STOP-WORDS (MAŠILA) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "tisti", "nekaj", "včasih"
}

# --- 2. ZNANSTVENE KATEGORIJE (6 ENOT) ---
# Razširjen nabor ključnih besed za boljšo detekcijo fo in fr
CATEGORIES_MAP = {
    "Attentive (physical) unit": ["hrup", "svetloba", "vreme", "pisarna", "tišina", "mraz", "vročina", "noise", "light"],
    "Performance unit": ["roki", "obremenitev", "naloge", "čas", "birokracija", "informacije", "napor", "deadlines", "workload"],
    "Individual Psychological unit": ["strah", "stres", "mir", "samozavest", "tesnoba", "skrb", "anxiety", "fear"],
    "Partial social unit": ["plača", "denar", "finance", "nagrada", "priznanje", "krivica", "standard", "money", "salary"],
    "Social unit": ["odnosi", "mobing", "sodelavci", "družina", "komunikacija", "prepir", "konflikt", "mobbing", "family"],
    "Health biological unit": ["zdravje", "šport", "prehrana", "spanje", "joga", "bolezen", "utrujenost", "health", "illness"]
}

# --- 3. FUNKCIJE ZA OBDELAVO BESEDILA ---

def get_fo_fr(series):
    """
    fo = vsa najdena mnenja (vse besede, ki ustrezajo kategorijam)
    fr = različna mnenja (unikatne besede, ki ustrezajo kategorijam)
    """
    all_matched_words = []
    
    for row in series.dropna():
        # Čiščenje vrstice
        text = str(row).lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = [w for w in text.split() if w not in SLO_STOPWORDS and len(w) > 2]
        
        for word in words:
            # Preverimo, če beseda ustreza katerikoli kategoriji
            for cat, keywords in CATEGORIES_MAP.items():
                if any(kw in word for kw in keywords):
                    all_matched_words.append(word)
                    break
    
    fo = len(all_matched_words)
    fr = len(set(all_matched_words)) # Število unikatnih relevantnih besed
    
    return fo, fr, Counter(all_matched_words)

# --- 4. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Petrič Stress Power Index", layout="wide")
    st.title("📊 Izračun stresne moči po Petričevi metodi (2025)")

    uploaded_file = st.sidebar.file_uploader("Naložite datoteko (.txt ali .csv)", type=['txt', 'csv'])
    
    if uploaded_file:
        # Nalaganje podatkov
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        df = pd.read_csv(uploaded_file, sep=sep)
        
        # Preverjanje stolpcev
        if len(df.columns) >= 3:
            # Predvidevamo vrstni red: Pozitivni, Stresni, Predlogi
            col_pf = df.columns[0] # Pozitivni
            col_sf = df.columns[1] # Stresni
            col_pr = df.columns[2] # Predlogi
            
            N_o = len(df) # Sample size
            
            # --- NIVO 1: fo in fr ---
            fo_pf, fr_pf, _ = get_fo_fr(df[col_pf])
            fo_sf, fr_sf, _ = get_fo_fr(df[col_sf])
            fo_pr, fr_pr, _ = get_fo_fr(df[col_pr])

            # Parametri za izračun (Theoretical constants)
            rho_t = 10
            c_t = 1

            # --- NIVO 2: Realni faktorji Fo ---
            def calculate_fo_real(fo, fr, n):
                if fr == 0 or n == 0: return 0.0001 # Preprečitev deljenja z 0
                rho_o = fo / n
                c_o = fo / fr
                return (c_o * rho_o) / (c_t * rho_t)

            F_pf = calculate_fo_real(fo_pf, fr_pf, N_o)
            F_sf = calculate_fo_real(fo_sf, fr_sf, N_o)
            F_pr = calculate_fo_real(fo_pr, fr_pr, N_o)

            # --- NIVO 3: Končni izračun stopinj ---
            # Formula: sigma = arcsin( sqrt( (F_sf * F_pr) / F_pf ) )
            try:
                # Izračun vrednosti pod korenom
                under_root = (F_sf * F_pr) / F_pf
                sqrt_val = math.sqrt(under_root)
                
                # Arcsin izračun (rezultat v radianih, zato pretvorba v stopinje)
                # math.asin sprejme vrednost med -1 in 1
                sigma_rad = math.asin(min(sqrt_val, 1.0))
                sigma_deg = math.degrees(sigma_rad)
            except Exception as e:
                sigma_deg = 0
                st.error(f"Napaka pri matematičnem izračunu: {e}")

            # --- PRIKAZ REZULTATOV ---
            st.header("Končni znanstveni izračun")
            
            res_c1, res_c2 = st.columns(2)
            with res_c1:
                st.metric("CELOKUPNA STRESNA MOČ", f"{sigma_deg:.2f} °S")
                if 30.0 <= sigma_deg <= 39.0:
                    st.success("Rezultat je v pričakovanem znanstvenem razponu (30-39 °S).")
                else:
                    st.warning("Rezultat je izven razpona 30-39 °S. Preverite bazo ključnih besed.")

            with res_c2:
                # Vizualni barometer
                st.write("Psihosocialni barometer")
                st.progress(min(sigma_deg / 90, 1.0))

            # Tabela s parametri po Petriču
            st.divider()
            st.subheader("Podrobna tabela parametrov")
            
            data = {
                "Kategorija": ["Stresni dejavniki (SF)", "Pozitivni dejavniki (PF)", "Predlogi (PR)"],
                "fo (vsa mnenja)": [fo_sf, fo_pf, fo_pr],
                "fr (različna)": [fr_sf, fr_pf, fr_pr],
                "rho_o (Gostota)": [round(fo_sf/N_o, 3), round(fo_pf/N_o, 3), round(fo_pr/N_o, 3)],
                "Co (Kompleksnost)": [round(fo_sf/fr_sf, 3) if fr_sf > 0 else 0, 
                                      round(fo_pf/fr_pf, 3) if fr_pf > 0 else 0, 
                                      round(fo_pr/fr_pr, 3) if fr_pr > 0 else 0],
                "Fo (Realni faktor)": [round(F_sf, 4), round(F_pf, 4), round(F_pr, 4)]
            }
            st.table(pd.DataFrame(data))

            # Izpis po nivojih za kontrolo
            with st.expander("Poglej matematični postopek (Nivoji)"):
                st.write(f"**Nivo 1:** Identificiranih {fo_sf + fo_pf + fo_pr} relevantnih enot pri {N_o} respondentih.")
                st.write(f"**Nivo 2:** Izračunani realni faktorji: SF={F_sf:.4f}, PF={F_pf:.4f}, PR={F_pr:.4f}")
                st.latex(r"\sigma = \arcsin\sqrt{\frac{" + f"{F_sf:.4f} \cdot {F_pr:.4f}" + r"}{" + f"{F_pf:.4f}" + r"}}")

        else:
            st.error("Napačna struktura datoteke. Potrebni so 3 stolpci.")
    else:
        st.info("Naložite datoteko za izračun.")

if __name__ == "__main__":
    main()



