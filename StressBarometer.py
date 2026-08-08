import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. FUNKCIJA ZA RESET APLIKACIJE ---
# Omogoča popoln izbris stanja in ponovni zagon aplikacije
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- 2. DEFINICIJA STOP-WORDS (MAŠIL) ---
# Seznam besed, ki nimajo pomena za analizo in jih sistem izloči
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bi", "bil", "bila", "bi", "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it", 
    "gre", "vse", "tudi", "nekaj", "pomanjkanje", "zaradi", "pod", "med", "tem", "vsem",
    "with", "some", "being", "able", "use", "make", "nice", "talk", "more", "family", "friends"
}

# --- 3. CELOTEN ZNANSTVENO RAZŠIRJEN KLASIFIKACIJSKI MODEL (SLO + ENG SPECIFIKE) ---
# Razvrščanje v 6 znanstvenih enot po Petričevi metodi
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem", "prostor", "pisarn", "ergonom", 
        "oprem", "tišin", "zrak", "prah", "gneč", "tehni", "akcij", "poškodb", "varna", "objekt", 
        "sodobn", "naprav", "urejenost", "etiket", "izolac", "barv", "rastlin", "vonjav", 
        "stol", "miz", "prezrač", "čistoč", "higien", "knjižn", "čitaln", "notranj", "location", 
        "environment", "hrupn", "svetloba"
    ],
    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "čas", "administra", "birokra", 
        "obrazc", "poročil", "sestank", "postopk", "navodil", "znanj", "veščin", "hitenj", 
        "naglic", "stisk", "preobremen", "neizkušn", "strokov", "organizac", "učinkovit", 
        "biro", "togi", "rutin", "nujne", "izobraž", "usposab", "optimiz", "proces", 
        "poenostav", "inovac", "rešitev", "urnik", "ure", "izvajanj", "regula", "hrm", 
        "direktiv", "ukaluplj", "iskanj", "gradiv", "polic", "katalog", "orientac", 
        "podatkov", "fond", "isposoj", "job", "balance", "goal", "cilj", "focus", "fokus", 
        "prioritet", "iskanje", "študij", "literature", "izvodi", "raziskav"
    ],
    "Individual Psychological unit": [
        "strah", "tesnob", "optimiz", "pozitiv", "samozav", "čustv", "stres", "frustr", 
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb", "napetos", "psih", "travm", 
        "osebno", "samopodob", "nasil", "negativ", "dušev", "žalost", "ogroženost", 
        "zaupan", "klima", "razmišlj", "nelagod", "zadovolj", "psihi", "tesnob", "nemir",
        "morast", "nesigurnost", "zaprtost", "identitet", "pripadnost", "choice", "life", 
        "memory", "spomin", "art", "umetnos", "irrational", "uncertain", "uncertainty", 
        "peace", "feeling", "emotion", "hope", "values", "vrednot", "ponižanj"
    ],
    "Partial social unit": [
        "plač", "dohod", "denar", "finanč", "nagrad", "status", "priznan", "revšč", 
        "standar", "nepravič", "nestimul", "krivic", "dostojen", "zaposlit", "služb", 
        "karier", "napredov", "varnost", "staž", "benefic", "ekonom", "proračun", 
        "pokojnin", "sredstv", "zamudn", "opomin", "kazn", "plačev", "plačilo", "money", 
        "salary", "financial", "budget", "stability"
    ],
    "Social unit": [
        "odnos", "mobing", "šikan", "sodelav", "šef", "vodstv", "nadrejen", "družin", 
        "prijatel", "komunik", "prepir", "zahrbt", "vzvišen", "nesram", "aroganc", 
        "egoiz", "podpor", "konflikt", "intrig", "neiskren", "rival", "polit", 
        "hierarh", "timsko", "druženj", "domače", "kader", "sodelov", "sovrašt", 
        "grožn", "informac", "profesional", "uporabnik", "osebj", "človek", "friend", 
        "family", "talk", "prijatelj", "družin", "pogovor", "pomoč", "osebja", "ekipa", 
        "prijaznost", "ekipno", "partner", "spouse"
    ],
    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "šport", "aktiv", "prehran", "diet", "spanj", 
        "utrujen", "joga", "medit", "izčrpan", "sprošč", "počit", "dopust", "rekreac", 
        "hoja", "izlet", "narav", "masaž", "tek", "vrt", "nočno", "fizič", "higien", 
        "čistoč", "yoga", "exercise", "sport", "relax", "dihan", "journey", "potovan", 
        "izlet", "sprehod", "plavanj", "kolo", "sleep", "rest"
    ]
}

# --- 4. POMOŽNE FUNKCIJE ---

# Čiščenje besedila: mala tiskana, brez ločil, izločitev mašil
def clean_and_tokenize(text):
    if not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    keywords = [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]
    return keywords

# Razvrščanje besed v kategorije na podlagi korenov besed
def classify_keywords(keywords):
    found_categories = []
    for word in keywords:
        word_lower = word.lower()
        for cat, kw_list in CATEGORIES_MAP.items():
            if any(koren in word_lower for koren in kw_list):
                found_categories.append(cat)
    return found_categories

# Izračun realnega faktorja Fo po Petričevi metodi
def calculate_fo_real(df, col, n_override):
    all_keywords_in_cat = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            kw_lower = kw.lower()
            for cat, kw_list in CATEGORIES_MAP.items():
                if any(koren in kw_lower for koren in kw_list): 
                    all_keywords_in_cat.append(kw)
                    break 
    
    fo = len(all_keywords_in_cat)
    fr = len(set(all_keywords_in_cat))
    if fr == 0 or n_override == 0: return 0.0001, fo, fr
    
    # Petrič Level 3 formula: (C_o * Rho_o) / 10
    rho_o = fo / n_override
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr

# --- 5. STREAMLIT APLIKACIJA (UI IN LOGIKA) ---

def main():
    # Nastavitev strani
    st.set_page_config(page_title="Stress Barometer Pro", page_icon="📊", layout="wide")
    
    # Stranski meni za nastavitve
    with st.sidebar:
        st.header("Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()
        st.subheader("Parametri raziskave")
        # Ročni vnos števila respondentov (N) za pravilno kalibracijo
        n_input = st.number_input("Dejansko število respondentov (N):", min_value=1, value=210, 
                                  help="Vpišite skupno število ljudi, ki so sodelovali v raziskavi.")

    # Glavni naslov
    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown(f"""
    Analiza besedilnih odgovorov za **N = {n_input}** respondentov. 
    Sistem razvršča odgovore v 6 znanstvenih enot in izračunava celokupno stresno moč v stopinjah (°S).
    """)

    # Nalaganje datoteke
    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        # Določitev separatorja
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        try:
            # Branju s Python engine-om za boljšo stabilnost
            df = pd.read_csv(uploaded_file, sep=sep, engine='python', on_bad_lines='skip')
            st.success(f"Datoteka uspešno naložena. Analiziramo {len(df)} vrstic podatkov.", icon="✅")
            
            target_cols = df.columns.tolist()
            results = {}
            fo_real_factors = {}

            # 1. SEKCIJA: KVALITATIVNA ANALIZA PO SKLOPIH
            st.header("🔍 Kvalitativna analiza po sklopih")
            for col in target_cols[:3]:
                with st.expander(f"Podrobnosti za sklop: {col}", expanded=True):
                    # Obdelava besed in klasifikacija
                    df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
                    df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
                    
                    # Agregacija zadetkov po enotah
                    all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
                    unit_counts = Counter(all_units)
                    freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
                    
                    # Prikaz tabele in klasifikacije
                    col_l, col_r = st.columns([2, 1])
                    with col_l:
                        st.caption("Primeri klasificiranih odgovorov:")
                        st.dataframe(df[[col, f'units_{col}']].head(15), use_container_width=True)
                    with col_r:
                        st.caption("Frekvence enot:")
                        st.table(freq_df)
                    
                    # Izračun Fo faktorja
                    fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_input)
                    fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
                    results[col] = freq_df

            # 2. SEKCIJA: IZRAČUN CELOKUPNE STRESNE MOČI (°S)
            st.divider()
            st.header("📐 Izračun celokupne stresne moči")
            
            if len(target_cols) >= 3:
                # Pozitivni faktor (PF), Stresni faktor (SF), Faktor predlogov (PR)
                f_pf = fo_real_factors[target_cols[0]]["val"]
                f_sf = fo_real_factors[target_cols[1]]["val"]
                f_pr = fo_real_factors[target_cols[2]]["val"]
                
                try:
                    # Glavna formula Petričeve metode
                    argument = math.sqrt((f_sf * f_pr) / f_pf)
                    # Omejitev za matematično stabilnost arcsin funkcije
                    sigma_rad = math.asin(min(argument, 1.0))
                    sigma_deg = math.degrees(sigma_rad)
                    
                    # Prikaz rezultata
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 1.5])
                        with c1:
                            st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_deg:.2f} °S")
                            
                            # Interpretacija stopenj
                            if sigma_deg <= 15.0:
                                st.info("Stopnja: Zelo nizka")
                            elif sigma_deg <= 30.0:
                                st.success("Stopnja: Nizka")
                            elif sigma_deg <= 45.0:
                                st.warning("Stopnja: Srednja")
                            else:
                                st.error("Stopnja: Visoka (Kritično)")
                        
                        with c2:
                            st.write(f"**Vrednosti faktorjev (N={n_input}):**")
                            st.markdown(f"""
                            - Pozitivni ($F_{{oPF}}$): **{f_pf:.4f}**
                            - Stresni ($F_{{oSF}}$): **{f_sf:.4f}**
                            - Predlogi ($F_{{oPR}}$): **{f_pr:.4f}**
                            """)
                            st.progress(min(sigma_deg / 90, 1.0))
                            st.caption("Psihosocialni barometer stresa (0°S do 90°S)")
                except Exception as e:
                    st.error(f"Napaka pri izračunu stresne moči: {e}")

            # 3. SEKCIJA: VIZUALIZACIJA PORAZDELITVE
            st.divider()
            st.header("📈 Vizualizacija enot")
            final_tabs = st.tabs([f"📊 {target_cols[0]}", f"📊 {target_cols[1]}", f"📊 {target_cols[2]}"])
            for i, tab in enumerate(final_tabs):
                with tab:
                    st.bar_chart(results[target_cols[i]].set_index('Klasifikacijska enota'), color="#1C83E1")
                    
        except Exception as e:
            st.error(f"Napaka pri obdelavi datoteke: {e}")
    else:
        st.info("Naložite datoteko v stranskem meniju za pričetek analize.", icon="ℹ️")

if __name__ == "__main__":
    main()



