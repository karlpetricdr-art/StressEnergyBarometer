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
# Razširjen seznam besed, ki jih sistem izloči, da ostanejo le vsebinski poudarki
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "tisti", "nekaj", "včasih",
    "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it", "with", "some", "more",
    "being", "able", "use", "make", "nice", "talk", "more", "family", "friends", "your",
    "gre", "vsem", "tem", "zaradi", "nekaj", "pod", "med", "tudi", "kar", "naj", "ali",
    "tistega", "tistem", "tistimi", "tistih", "tista", "tisto", "vsega", "vsemu", "vsem"
}

# --- 3. CELOTEN ZNANSTVENO RAZŠIRJEN KLASIFIKACIJSKI MODEL (SLO + ENG) ---
# Razvrščanje v 6 znanstvenih enot po Petričevi metodi (Karl Petrič, 2025)
# Opomba: Šport in aktivna rekreacija sta pod Performance, narava pod Psychological, 
# da Health biološka enota ostane nizka (le fiziološki simptomi).
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem", "prostor", "pisarn", "ergonom", 
        "oprem", "tišin", "zrak", "prah", "gneč", "tehni", "akcij", "poškodb", "varna", "objekt", 
        "sodobn", "naprav", "urejenost", "etiket", "izolac", "barv", "rastlin", "vonjav", 
        "stol", "miz", "prezrač", "notranj", "location", "environment", "lighting", "toplota",
        "hlad", "umazano", "onesnaž", "arhitekt", "opremljenost", "hrupn", "svetloba", "tišina"
    ],
    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "čas", "administra", "birokra", 
        "obrazc", "poročil", "sestank", "postopk", "navodil", "veščin", "hitenj", 
        "naglic", "stisk", "preobremen", "neizkušn", "organizac", "učinkovit", 
        "biro", "togi", "rutin", "nujne", "izobraž", "usposab", "optimiz", "proces", 
        "poenostav", "inovac", "rešitev", "urnik", "ure", "izvajanj", "regula", "hrm", 
        "direktiv", "ukaluplj", "iskanj", "gradiv", "polic", "katalog", "orientac", 
        "podatkov", "fond", "isposoj", "job", "balance", "goal", "cilj", "študij", 
        "literature", "izvodi", "raziskav", "iskanje", "tasks", "šport", "rekreac", 
        "tek", "joga", "aktiv", "plavanj", "kolo", "vrtnar", "hobi", "delovni", "program",
        "iskanja", "usposabljanja", "training", "exercise", "sport", "activities", "vodenje"
    ],
    "Individual Psychological unit": [
        "strah", "tesnob", "optimiz", "pozitiv", "samozav", "čustv", "stres", "frustr", 
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb", "napetos", "psih", "travm", 
        "osebno", "samopodob", "nasil", "negativ", "dušev", "žalost", "ogroženost", 
        "nelagod", "zadovolj", "psihi", "nemir", "choice", "life", "memory", 
        "spomin", "art", "umetnos", "irrational", "uncertain", "uncertainty", "peace", 
        "feeling", "hope", "values", "vrednot", "ponižanj", "identitet", "dopust", 
        "izlet", "potovan", "journey", "sprošč", "relax", "medit", "dihan", "pripadnost", 
        "narav", "spomini", "praznina", "osebnost", "samokontrol", "vera", "mirnost"
    ],
    "Partial social unit": [
        "plač", "dohod", "denar", "finanč", "nagrad", "status", "priznan", "revšč", 
        "standar", "nepravič", "nestimul", "krivic", "dostojen", "zaposlit", "služb", 
        "karier", "napredov", "varnost", "staž", "benefic", "ekonom", "proračun", 
        "pokojnin", "sredstv", "zamudn", "opomin", "kazn", "plačev", "plačilo", "money", 
        "salary", "financial", "budget", "stability", "sredstva", "znesek", "standard",
        "zavarov", "ekonomska", "preživetje", "neenakost", "nepravičnost"
    ],
    "Social unit": [
        "odnos", "mobing", "šikan", "sodelav", "šef", "vodstv", "nadrejen", "družin", 
        "prijatel", "komunik", "prepir", "zahrbt", "vzvišen", "nesram", "aroganc", 
        "egoiz", "podpor", "konflikt", "intrig", "neiskren", "rival", "polit", 
        "hierarh", "timsko", "druženj", "domače", "kader", "sodelov", "sovrašt", 
        "grožn", "informac", "profesional", "uporabnik", "osebj", "človek", "friend", 
        "family", "talk", "prijatelj", "družin", "pogovor", "pomoč", "ekipa", "prijaznost",
        "partnership", "spouse", "sodelovanje", "zaupan", "vodenj", "klima", "vzdušje",
        "ignora", "nerazum", "posluš", "sektor", "direktor", "vodja", "pripadnost", "rivalstvo"
    ],
    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "spanj", "utrujen", "izčrpan", "higien", 
        "čistoč", "sleep", "rest", "dihanje", "poškodb", "izčrpanost", "utrujenost", 
        "zdravje", "bolečina", "virus", "infekcij", "higiena", "prehran", "diet",
        "biološ", "fiziolo", "telo", "utrujena", "spanja", "telesno", "exhaustion"
    ]
}

# --- 4. POMOŽNE FUNKCIJE ZA OBDELAVO BESEDILA ---

def clean_and_tokenize(text):
    """Odstrani ločila, pretvori v male črke in izloči mašila."""
    if not isinstance(text, str): return []
    text = text.lower()
    # RegEx za odstranjevanje vsega, kar niso črke
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]

def classify_keywords(keywords):
    """Razvrsti očiščene besede v 6 znanstvenih kategorij na podlagi korenov."""
    found_categories = []
    for word in keywords:
        for cat, kw_list in CATEGORIES_MAP.items():
            # Išče koren besede znotraj tokena (stemming logika)
            if any(koren in word for koren in kw_list):
                found_categories.append(cat)
    return found_categories

def calculate_fo_real(df, col, n_override):
    """Izračun realnega faktorja Fo na podlagi 3. nivoja Petričeve metode."""
    all_keywords_in_cat = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            # Preverimo, če beseda sploh spada v katero koli kategorijo
            for cat, kw_list in CATEGORIES_MAP.items():
                if any(koren in kw for koren in kw_list): 
                    all_keywords_in_cat.append(kw)
                    break 
    
    fo = len(all_keywords_in_cat) # Frekvenca vseh zadetkov
    fr = len(set(all_keywords_in_cat)) # Frekvenca unikatnih zadetkov
    
    # Preprečevanje deljenja z nič
    if fr == 0 or n_override == 0: return 0.0001, fo, fr
    
    # Petričeva formula Level 3:
    # rho_o = povprečna frekvenca na respondenta
    # c_o = koeficient gostote (znanstvena teža)
    rho_o = fo / n_override
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr

# --- 5. STREAMLIT UPORABNIŠKI VMESNIK IN MATEMATIKA ---

def main():
    st.set_page_config(page_title="Petrič Stress Barometer Pro", page_icon="📊", layout="wide")
    
    # --- STRANSKI MENI (SIDEBAR) ---
    with st.sidebar:
        st.header("⚙️ Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()
        st.subheader("📊 Parametri raziskave")
        # Ključno za povzetke: Ročni vnos števila respondentov
        n_input = st.number_input("Dejansko število respondentov (N):", min_value=1, value=210, 
                                  help="Vpišite število ljudi, ki so dejansko sodelovali v raziskavi.")
        # Normalizacija za kondenzirane podatke
        is_summary = st.checkbox("Ali naložena datoteka vsebuje POVZETEK?", value=True,
                                 help="Če nalagate že strnjene odgovore, sistem uporabi normalizacijski faktor.")
        st.divider()
        st.info("Koda temelji na Petričevi metodi izračuna stresne moči v stopinjah (°S).")

    # --- GLAVNI DEL APLIKACIJE ---
    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown(f"Trenutna kalibracija: **N = {n_input}** respondentov.")

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        try:
            # Branje s Python engine-om za stabilnost pri napačnih tabulatorjih
            df = pd.read_csv(uploaded_file, sep=sep, engine='python', on_bad_lines='skip')
            st.success(f"Datoteka uspešno naložena. Število vrstic v tabeli: {len(df)}.", icon="✅")
            
            target_cols = df.columns.tolist()
            fo_real_factors = {}
            results = {}

            # --- 1. SEKCIJA: KVALITATIVNA ANALIZA PO SKLOPIH ---
            st.header("🔍 Kvalitativna analiza po sklopih")
            for col in target_cols[:3]:
                with st.expander(f"Podrobnosti za: {col}", expanded=True):
                    # Obdelava besed in klasifikacija po enotah
                    df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
                    df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
                    
                    # Preštevanje frekvenc zadetkov
                    all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
                    unit_counts = Counter(all_units)
                    freq_df = pd.DataFrame(unit_counts.items(), columns=['Enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
                    
                    # Prikaz v dveh stolpcih
                    cl1, cl2 = st.columns([2, 1])
                    with cl1:
                        st.caption("Klasificirani primeri odgovorov:")
                        st.dataframe(df[[col, f'units_{col}']].head(15), use_container_width=True)
                    with cl2:
                        st.caption("Frekvence znanstvenih enot:")
                        st.table(freq_df)
                    
                    # Izračun realnega faktorja Fo po Petričevi metodi
                    fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_input)
                    fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
                    results[col] = freq_df

            # --- 2. SEKCIJA: MATEMATIČNI IZRAČUN STRESNE MOČI (°S) ---
            st.divider()
            st.header("📐 Izračun celokupne stresne moči")
            
            if len(target_cols) >= 3:
                # Pozitivni faktor (PF), Stresni faktor (SF), Faktor predlogov (PR)
                f_pf = fo_real_factors[target_cols[0]]["val"]
                f_sf = fo_real_factors[target_cols[1]]["val"]
                f_pr = fo_real_factors[target_cols[2]]["val"]
                
                # Posebna normalizacija za povzetke: preprečuje umetno zvišanje zaradi predlogov
                if is_summary:
                    f_pr = min(f_pr, f_sf * 1.5)

                try:
                    # GLAVNA FORMULA: sigma = arcsin(sqrt((F_oSF * F_oPR) / F_oPF))
                    argument = math.sqrt((f_sf * f_pr) / f_pf)
                    # Omejitev za arcsin: argument mora biti med 0 in 1
                    sigma_rad = math.asin(min(argument, 1.0))
                    sigma_deg = math.degrees(sigma_rad)
                    
                    # Estetski prikaz rezultatov
                    with st.container(border=True):
                        col_m1, col_m2 = st.columns([1, 1.5])
                        with col_m1:
                            st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_deg:.2f} °S")
                            
                            # Interpretacija po Petričevi lestvici
                            if sigma_deg <= 15.0:
                                st.info("Stopnja: Zelo nizka")
                            elif sigma_deg <= 30.0:
                                st.success("Stopnja: Nizka (Stabilno okolje)")
                            elif sigma_deg <= 45.0:
                                st.warning("Stopnja: Srednja (Standard slovenske JU)")
                            else:
                                st.error("Stopnja: Visoka (Kritično območje)")
                        
                        with col_m2:
                            st.write(f"**Vrednosti realnih faktorjev (N={n_input}):**")
                            st.markdown(f"""
                            - Pozitivni ($F_{{oPF}}$): **{f_pf:.4f}**
                            - Stresni ($F_{{oSF}}$): **{f_sf:.4f}**
                            - Predlogi ($F_{{oPR}}$): **{f_pr:.4f}**
                            """)
                            st.progress(min(sigma_deg / 90, 1.0))
                            st.caption("Petričev barometer stresa (0°S do 90°S)")
                except Exception as e:
                    st.error(f"Napaka pri izračunu stresne moči: {e}")

            # --- 3. SEKCIJA: VIZUALIZACIJA PORAZDELITVE ---
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


