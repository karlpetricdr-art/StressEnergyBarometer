import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. STOP-WORDS (MAŠILA) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "tisti", "nekaj", "včasih", "npr", "itd"
}

# --- 2. KATEGORIJE PO ČLANKU (Petrič, 2025) ---
CATEGORIES_MAP = {
    "Attentive (physical) unit": ["hrup", "noise", "svetloba", "vreme", "pisarna", "tišina", "mraz", "vročina"],
    "Performance unit": ["roki", "obremenitev", "naloge", "čas", "birokracija", "informacije", "napor"],
    "Individual Psychological unit": ["strah", "anxiety", "stres", "mir", "samozavest", "tesnoba", "skrb"],
    "Partial social unit": ["plača", "denar", "finance", "nagrada", "priznanje", "krivica", "standard"],
    "Social unit": ["odnosi", "mobing", "sodelavci", "družina", "komunikacija", "prepir", "konflikt"],
    "Health biological unit": ["zdravje", "šport", "prehrana", "spanje", "joga", "bolezen", "utrujenost"]
}

# --- 3. POMOŽNE FUNKCIJE ---
def clean_text(text):
    if not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return [w for w in text.split() if w not in SLO_STOPWORDS and len(w) > 2]

def get_classification_stats(df, col):
    """Vrne fo (vsa mnenja) in fr (različna mnenja) za določen sklop."""
    all_hits = []
    for row in df[col].dropna():
        tokens = clean_text(row)
        for t in tokens:
            for cat, kws in CATEGORIES_MAP.items():
                if any(kw in t for kw in kws):
                    all_hits.append(cat)
    
    fo = len(all_hits)
    fr = len(set(all_hits))
    return fo, fr, Counter(all_hits)

# --- 4. STREAMLIT APLIKACIJA ---
def main():
    st.set_page_config(page_title="Stress Analysis Petrič", layout="wide")
    st.title("📊 Klasifikacija in izračun celokupne stresne moči")

    uploaded_file = st.sidebar.file_uploader("Naložite datoteko (.txt ali .csv)", type=['txt', 'csv'])
    
    if uploaded_file:
        # Branje datoteke
        if uploaded_file.name.endswith('.txt'):
            df = pd.read_csv(uploaded_file, sep='\t')
        else:
            df = pd.read_csv(uploaded_file)

        # Preverimo če imamo prave stolpce (Pozitivni, Stresni, Predlogi)
        if len(df.columns) >= 3:
            col_pf, col_sf, col_pr = df.columns[0], df.columns[1], df.columns[2]
            n_o = len(df) # Število respondentov
            
            st.sidebar.success(f"Naloženo {n_o} odgovorov.")

            # --- KLASIFIKACIJA IN TABELE ---
            st.header("1. Pregled klasifikacije po kategorijah")
            
            # Izračuni fo in fr za vse tri sklope
            fo_pf, fr_pf, counts_pf = get_classification_stats(df, col_pf)
            fo_sf, fr_sf, counts_sf = get_classification_stats(df, col_sf)
            fo_pr, fr_pr, counts_pr = get_classification_stats(df, col_pr)

            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.subheader("Pozitivni dejavniki")
                df_pf = pd.DataFrame(counts_pf.items(), columns=['Enota', 'Frekvenca']).sort_values('Frekvenca', ascending=False)
                st.table(df_pf)
            
            with c2:
                st.subheader("Stresni dejavniki")
                df_sf = pd.DataFrame(counts_sf.items(), columns=['Enota', 'Frekvenca']).sort_values('Frekvenca', ascending=False)
                st.table(df_sf)
                
            with c3:
                st.subheader("Predlogi za redukcijo")
                df_pr = pd.DataFrame(counts_pr.items(), columns=['Enota', 'Frekvenca']).sort_values('Frekvenca', ascending=False)
                st.table(df_pr)

            # --- IZRAČUN STRESNE MOČI (°S) ---
            st.divider()
            st.header("2. Izračun celokupne stresne moči")

            # Parametri po članku
            rho_t = 10
            c_t = 1

            # Funkcija za izračun realnega faktorja Fo (Nivo 1 & 2)
            def calc_f_real(fo, fr, n):
                if fr == 0 or n == 0: return 0
                rho = fo / n
                c = fo / fr
                return (c * rho) / (rho_t * c_t)

            f_sf_real = calc_f_real(fo_sf, fr_sf, n_o)
            f_pf_real = calc_f_real(fo_pf, fr_pf, n_o)
            f_pr_real = calc_f_real(fo_pr, fr_pr, n_o)

            # Enačba 27: sigma = arcsin( sqrt( (F_sf * F_pr) / F_pf ) )
            sigma_deg = 0
            if f_pf_real > 0:
                try:
                    argument = math.sqrt((f_sf_real * f_pr_real) / f_pf_real)
                    # Argument ne sme presegati 1 za arcsin
                    sigma_rad = math.asin(min(argument, 1.0))
                    sigma_deg = math.degrees(sigma_rad)
                except:
                    sigma_deg = 0

            # Prikaz rezultata
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.metric("Izračunana celokupna moč", f"{sigma_deg:.2f} °S")
                
                # Preverjanje realnosti rezultata (vaša zahteva 30-39)
                if 30.0 <= sigma_deg <= 39.0:
                    st.success("Rezultat je znotraj realnih znanstvenih meja (30-39 °S).")
                else:
                    st.warning("Opozorilo: Rezultat odstopa od pričakovanih meja (30-39 °S). Preverite nabor ključnih besed.")

            with res_col2:
                # Interpretacija po Tabeli 6
                if sigma_deg <= 30.04: status = "Nizka (Low)"
                elif sigma_deg <= 45.04: status = "Srednja (Medium)"
                else: status = "Visoka (High)"
                st.info(f"Psihosocialna ocena: **{status}**")

            # Tabela parametrov za preverjanje
            st.write("**Povzetek parametrov izračuna:**")
            summary_df = pd.DataFrame({
                "Sklop": ["Stresni (SF)", "Pozitivni (PF)", "Predlogi (PR)"],
                "fo (vsa mnenja)": [fo_sf, fo_pf, fo_pr],
                "fr (različna)": [fr_sf, fr_pf, fr_pr],
                "Fo (Realni faktor)": [round(f_sf_real, 4), round(f_pf_real, 4), round(f_pr_real, 4)]
            })
            st.dataframe(summary_df)

        else:
            st.error("Datoteka mora imeti vsaj 3 stolpce: Pozitivni dejavniki, Stresni dejavniki, Predlogi.")
    else:
        st.info("Naložite datoteko za začetek analize.")

if __name__ == "__main__":
    main()



