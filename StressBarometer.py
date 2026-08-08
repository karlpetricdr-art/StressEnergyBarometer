import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. FUNKCIJA ZA PONASTAVITEV APLIKACIJE ---
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- 2. DEFINICIJA STOP-WORDS (MAŠIL) ---
# Seznam besed, ki jih sistem ignorira pri analizi vsebinskih poudarkov
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "tisti", "nekaj", "včasih",
    "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it", "with", "some", "more",
    "being", "able", "use", "make", "nice", "talk", "more", "family", "friends", "your",
    "gre", "vsem", "tem", "zaradi", "nekaj", "pod", "med", "tudi", "kar", "naj"
}

# --- 3. REVIDIRAN ZNANSTVENI KLASIFIKACIJSKI MODEL (SLO + ENG) ---
# Razvrščanje v 6 znanstvenih enot po Petričevi metodi s poudarkom na MNZ/Policija/JU/Knjižnica
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem", "prostor", "pisarn", "ergonom", 
        "oprem", "tišin", "zrak", "prah", "gneč", "tehni", "akcij", "varna", "objekt", 
        "sodobn", "naprav", "urejenost", "etiket", "izolac", "barv", "rastlin", "vonjav", 
        "stol", "miz", "prezrač", "čistoč", "higien", "knjižn", "čitaln", "notranj", "location", 
        "environment", "lighting", "narav", "sonce", "vrt", "okolje", "tišina", "toplota"
    ],
    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "administra", "birokra", 
        "obrazc", "poročil", "sestank", "postopk", "navodil", "veščin", "hitenj", 
        "naglic", "stisk", "preobremen", "neizkušn", "organizac", "učinkovit", 
        "biro", "togi", "rutin", "nujne", "izobraž", "usposab", "optimiz", "proces", 
        "poenostav", "inovac", "rešitev", "urnik", "ure", "izvajanj", "regula", "hrm", 
        "direktiv", "ukaluplj", "iskanj", "gradiv", "polic", "katalog", "orientac", 
        "podatkov", "fond", "isposoj", "job", "balance", "goal", "cilj", "focus", "fokus",
        "prioritet", "študij", "literature", "izvodi", "raziskav", "iskanje", "tasks", "delovni"
    ],
    "Individual Psychological unit": [
        "strah", "tesnob", "optimiz", "pozitiv", "samozav", "čustv", "stres", "frustr", 
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb", "napetos", "psih", "travm", 
        "osebno", "samopodob", "nasil", "negativ", "dušev", "žalost", "ogroženost", 
        "nelagod", "zadovolj", "psihi", "nemir", "choice", "life", "memory", 
        "spomin", "art", "umetnos", "irrational", "uncertain", "uncertainty", "peace", 
        "feeling", "hope", "values", "vrednot", "ponižanj", "identitet", "dopust", 
        "izlet", "potovan", "journey", "sprošč", "relax", "medit", "dihan", "pripadnost"
    ],
    "Partial social unit": [
        "plač", "dohod", "denar", "finanč", "nagrad", "status", "priznan", "revšč", 
        "standar", "nepravič", "nestimul", "krivic", "dostojen", "zaposlit", "služb", 
        "karier", "napredov", "varnost", "staž", "benefic", "ekonom", "proračun", 
        "pokojnin", "sredstv", "zamudn", "opomin", "kazn", "plačev", "plačilo", "money", 
        "salary", "financial", "budget", "stability", "sredstva", "dohodek", "znesek"
    ],
    "Social unit": [
        "odnos", "mobing", "šikan", "sodelav", "šef", "vodstv", "nadrejen", "družin", 
        "prijatel", "komunik", "prepir", "zahrbt", "vzvišen", "nesram", "aroganc", 
        "egoiz", "podpor", "konflikt", "intrig", "neiskren", "rival", "polit", 
        "hierarh", "timsko", "druženj", "domače", "kader", "sodelov", "sovrašt", 
        "grožn", "informac", "profesional", "uporabnik", "osebj", "človek", "friend", 
        "family", "talk", "prijatelj", "družin", "pogovor", "pomoč", "ekipa", "prijaznost",
        "partnership", "spouse", "sodelovanje", "zaupan", "vodenj", "klima", "vzdušje",
        "ignora", "nerazum", "posluš", "sektor", "direktor", "vodja", "odnosi", "prijatelji"
    ],
    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "šport", "aktiv", "prehran", "diet", "spanj", 
        "utrujen", "joga", "izčrpan", "počit", "hoja", "masaž", "tek", "nočno", 
        "fizič", "higien", "čistoč", "yoga", "exercise", "sport", "sleep", "rest", 
        "dihanje", "poškodb", "izčrpanost", "utrujenost", "zdravje", "bolečina"
    ]
}

# --- 4. POMOŽNE FUNKCIJE OBDELAVE ---

def clean_and_tokenize(text):
    """Odstrani ločila, pretvori v male črke in izloči mašila."""
    if not isinstance(text, str): return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]

def classify_keywords(keywords):
    """Razvrsti očiščene besede v 6 znanstvenih kategorij."""
    found_categories = []
    for word in keywords:
        for cat, kw_list in CATEGORIES_MAP.items():
            if any(koren in word for koren in kw_list):
                found_categories.append(cat)
    return found_categories

def calculate_fo_real(df, col, n_override):
    """Izračuna realni faktor Fo (3. nivo Petričeve metode)."""
    all_keywords_in_cat = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            for cat, kw_list in CATEGORIES_MAP.items():
                if any(koren in kw for koren in kw_list): 
                    all_keywords_in_cat.append(kw)
                    break 
    
    fo = len(all_keywords_in_cat)
    fr = len(set(all_keywords_in_cat))
    
    if fr == 0 or n_override == 0: return 0.0001, fo, fr
    
    # rho_o: povprečna frekvenca na respondenta
    # c_o: koeficient znanstvene teže (gostota unikatnih izrazov)
    rho_o = fo / n_override
    c_o = fo / fr
    return (c_o * rho_o) / 10, fo, fr

# --- 5. STREAMLIT UPORABNIŠKI VMESNIK ---

def main():
    st.set_page_config(page_title="Petrič Stress Barometer Pro", page_icon="📊", layout="wide")
    
    # --- Sidebar Nastavitve ---
    with st.sidebar:
        st.header("Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()
        st.subheader("Kalibracija vzorca")
        # Ročni vnos dejanskega števila respondentov (N)
        n_input = st.number_input("Dejansko število respondentov (N):", min_value=1, value=210, 
                                  help="Vnesite dejansko število ljudi, ki so sodelovali v raziskavi.")
        # Možnost normalizacije za strnjene podatke (povzetke)
        is_summary = st.checkbox("Ali naložena datoteka vsebuje POVZETEK?", value=True,
                                 help="Vključite, če nalagate kondenzirane podatke namesto vseh surovih vrstic.")

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown(f"Analiza poteka za **N = {n_input}** respondentov. Sistem razvršča odgovore v 6 znanstvenih enot.")

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        try:
            # Branje datoteke s Python engine-om za boljšo stabilnost
            df = pd.read_csv(uploaded_file, sep=sep, engine='python', on_bad_lines='skip')
            st.success(f"Datoteka uspešno naložena. Število vrstic v tabeli: {len(df)}.", icon="✅")
            
            target_cols = df.columns.tolist()
            fo_real_factors = {}
            results = {}

            # --- 1. KVALITATIVNA ANALIZA ---
            st.header("🔍 Kvalitativna analiza po sklopih")
            for col in target_cols[:3]:
                with st.expander(f"Podrobnosti za: {col}", expanded=True):
                    # Procesiranje in klasifikacija
                    df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
                    df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
                    
                    # Agregacija frekvenc
                    all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
                    unit_counts = Counter(all_units)
                    freq_df = pd.DataFrame(unit_counts.items(), columns=['Enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
                    
                    # Prikaz dveh stolpcev: surovih primerov in tabele frekvenc
                    cl1, cl2 = st.columns([2, 1])
                    with cl1:
                        st.caption("Klasificirani primeri odgovorov:")
                        st.dataframe(df[[col, f'units_{col}']].head(12), use_container_width=True)
                    with cl2:
                        st.caption("Frekvence znanstvenih enot:")
                        st.table(freq_df)
                    
                    # Izračun realnega faktorja
                    fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_input)
                    fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
                    results[col] = freq_df

            # --- 2. IZRAČUN STRESNE MOČI (°S) ---
            st.divider()
            st.header("📐 Izračun celokupne stresne moči")
            
            if len(target_cols) >= 3:
                f_pf = fo_real_factors[target_cols[0]]["val"] # Pozitivni dejavniki
                f_sf = fo_real_factors[target_cols[1]]["val"] # Stresni dejavniki
                f_pr = fo_real_factors[target_cols[2]]["val"] # Predlogi
                
                # Normalizacija za povzetke: preprečuje, da bi predlogi umetno zvišali stopinje
                if is_summary:
                    f_pr = min(f_pr, f_sf * 1.5)

                try:
                    # GLAVNA FORMULA: sigma = arcsin(sqrt((F_oSF * F_oPR) / F_oPF))
                    argument = math.sqrt((f_sf * f_pr) / f_pf)
                    # Omejitev na 1.0 zaradi matematične stabilnosti funkcije arcsin
                    sigma_rad = math.asin(min(argument, 1.0))
                    sigma_deg = math.degrees(sigma_rad)
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 1.5])
                        with c1:
                            st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_deg:.2f} °S")
                            
                            # Interpretacija po Petričevi metodi
                            if sigma_deg <= 15.0:
                                st.info("Stopnja: Zelo nizka")
                            elif sigma_deg <= 30.0:
                                st.success("Stopnja: Nizka (Značilno za urejena okolja)")
                            elif sigma_deg <= 45.0:
                                st.warning("Stopnja: Srednja (Standard slovenske JU)")
                            else:
                                st.error("Stopnja: Visoka (Kritično območje - Policija/MNZ)")
                        
                        with c2:
                            st.write(f"**Vrednosti realnih faktorjev (za N={n_input}):**")
                            st.markdown(f"""
                            - Pozitivni ($F_{{oPF}}$): **{f_pf:.4f}**
                            - Stresni ($F_{{oSF}}$): **{f_sf:.4f}**
                            - Predlogi ($F_{{oPR}}$): **{f_pr:.4f}**
                            """)
                            st.progress(min(sigma_deg / 90, 1.0))
                            st.caption("Petričev barometer (0°S do 90°S)")
                except Exception as e:
                    st.error(f"Napaka pri izračunu stresne moči: {e}")

            # --- 3. GRAFIČNI PRIKAZ ---
            st.divider()
            st.header("📈 Vizualna porazdelitev po enotah")
            tabs = st.tabs([f"📊 {target_cols[0]}", f"📊 {target_cols[1]}", f"📊 {target_cols[2]}"])
            for i, tab in enumerate(tabs):
                with tab:
                    st.bar_chart(results[target_cols[i]].set_index('Enota'), color="#1C83E1")
                    
        except Exception as e:
            st.error(f"Napaka pri obdelavi datoteke: {e}")
    else:
        st.info("Naložite datoteko v stranskem meniju za pričetek analize.", icon="ℹ️")

if __name__ == "__main__":
    main()



