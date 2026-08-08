import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. FUNKCIJA ZA RESET APLIKACIJE ---
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- 2. DEFINICIJA STOP-WORDS (MAŠIL) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bi", "bil", "bila", "bi", "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it", 
    "gre", "vse", "tudi", "nekaj", "pomanjkanje", "zaradi", "pod", "med", "tem", "vsem"
}

# --- 3. CELOTEN ZNANSTVENO RAZŠIRJEN KLASIFIKACIJSKI MODEL (VSE SPECIFIKE) ---
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem", "prostor", "pisarn", "ergonom", 
        "oprem", "tišin", "zrak", "prah", "gneč", "tehni", "akcij", "poškodb", "varna", "objekt", 
        "sodobn", "naprav", "urejenost", "etiket", "izolac", "barv", "rastlin", "vonjav", 
        "stol", "miz", "prezrač", "čistoč", "higien", "knjižn", "čitaln", "notranj", "opremljenost"
    ],
    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "čas", "administra", "birokra", 
        "obrazc", "poročil", "sestank", "postopk", "navodil", "znanj", "veščin", "hitenj", 
        "naglic", "stisk", "preobremen", "neizkušn", "strokov", "organizac", "učinkovit", 
        "biro", "togi", "rutin", "nujne", "izobraž", "usposab", "optimiz", "proces", 
        "poenostav", "inovac", "rešitev", "urnik", "ure", "izvajanj", "regula", "hrm", 
        "direktiv", "ukaluplj", "iskanj", "gradiv", "polic", "katalog", "orientac", 
        "podatkov", "fond", "isposoj", "šolanj", "mentor", "program", "naloga"
    ],
    "Individual Psychological unit": [
        "strah", "tesnob", "optimiz", "pozitiv", "samozav", "čustv", "stres", "frustr", 
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb", "napetos", "psih", "travm", 
        "osebno", "samopodob", "nasil", "negativ", "dušev", "žalost", "ogroženost", 
        "zaupan", "klima", "razmišlj", "nelagod", "zadovolj", "psihi", "tesnob", "nemir",
        "morast", "nesigurnost", "zaprtost", "identitet", "pripadnost"
    ],
    "Partial social unit": [
        "plač", "dohod", "denar", "finanč", "nagrad", "status", "priznan", "revšč", 
        "standar", "nepravič", "nestimul", "krivic", "dostojen", "zaposlit", "služb", 
        "karier", "napredov", "varnost", "staž", "benefic", "ekonom", "proračun", 
        "pokojnin", "sredstv", "zamudn", "opomin", "kazn", "plačev", "plačilo", "sredstva", "finančni"
    ],
    "Social unit": [
        "odnos", "mobing", "šikan", "sodelav", "šef", "vodstv", "nadrejen", "družin", 
        "prijatel", "komunik", "prepir", "zahrbt", "vzvišen", "nesram", "aroganc", 
        "egoiz", "podpor", "konflikt", "intrig", "neiskren", "rival", "polit", 
        "hierarh", "timsko", "druženj", "domače", "kader", "sodelov", "tovar", 
        "sovrašt", "grožn", "informac", "profesional", "uporabnik", "osebj", "človek", 
        "osebja", "ekipa", "prijaznost", "ekipno"
    ],
    "Health biological unit": [
        "zdrav", "bolniš", "bolezen", "šport", "aktiv", "prehran", "diet", "spanj", 
        "utrujen", "joga", "medit", "izčrpan", "sprošč", "počit", "dopust", "rekreac", 
        "hoja", "izlet", "narav", "masaž", "tek", "vrt", "nočno", "fizič", "higien", "čistoč"
    ]
}

# --- 4. POMOŽNE FUNKCIJE ---

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
        word_lower = word.lower()
        for cat, kw_list in CATEGORIES_MAP.items():
            if any(koren in word_lower for koren in kw_list):
                found_categories.append(cat)
    return found_categories

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
    
    # FORMULA PETRIČ (3. nivo): (C_o * Rho_o) / 10
    rho_o = fo / n_override
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr

# --- 5. STREAMLIT APLIKACIJA (UI IN LOGIKA) ---

def main():
    st.set_page_config(page_title="Stress Barometer Pro", page_icon="📊", layout="wide")
    
    # Sidebar nastavitve
    with st.sidebar:
        st.header("Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()
        st.subheader("Parametri raziskave")
        # N input za pravilno razmerje pri povzetkih
        n_input = st.number_input("Dejansko število respondentov (N):", min_value=1, value=210, 
                                  help="Tudi če naložite povzetek z 10 vrsticami, vnesite dejansko število ljudi (npr. 210), ki so odgovorili.")

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown("""
    Sistem analizira besedila respondentov, izloči mašila in razvrsti v **6 znanstvenih enot**.
    Izračun sledi Petričevemu barometru stresa.
    """)

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        try:
            df = pd.read_csv(uploaded_file, sep=sep, engine='python', on_bad_lines='skip')
            st.success(f"Datoteka uspešno naložena. Analiziramo na podlagi N = {n_input} respondentov.", icon="✅")
            
            target_cols = df.columns.tolist()
            results = {}
            fo_real_factors = {}

            # 1. SEKCIJA: KVALITATIVNA ANALIZA
            st.header("🔍 Kvalitativna analiza po sklopih")
            for col in target_cols[:3]:
                with st.expander(f"Podrobnosti za sklop: {col}", expanded=True):
                    # Priprava podatkov
                    df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
                    df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
                    
                    # Frekvenčna tabela
                    all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
                    unit_counts = Counter(all_units)
                    freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
                    
                    col_left, col_right = st.columns([2, 1])
                    with col_left:
                        st.caption("Klasificirani odgovori (prvih 10):")
                        st.dataframe(df[[col, f'units_{col}']].head(10), use_container_width=True)
                    with col_right:
                        st.caption("Znanstvena porazdelitev:")
                        st.table(freq_df)
                    
                    # Izračun realnega faktorja F_o
                    fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_input)
                    fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
                    results[col] = freq_df

            # 2. SEKCIJA: IZRAČUN STRESNE MOČI
            st.divider()
            st.header("📐 Izračun celokupne stresne moči (°S)")
            
            if len(target_cols) >= 3:
                # Faktorji: Pozitivni (PF), Stresni (SF), Predlogi (PR)
                f_pf = fo_real_factors[target_cols[0]]["val"]
                f_sf = fo_real_factors[target_cols[1]]["val"]
                f_pr = fo_real_factors[target_cols[2]]["val"]
                
                try:
                    # Formula Petrič: sigma = arcsin(sqrt((f_sf * f_pr) / f_pf))
                    argument = math.sqrt((f_sf * f_pr) / f_pf)
                    # Omejitev na 1.0 za arcsin
                    sigma_rad = math.asin(min(argument, 1.0))
                    sigma_deg = math.degrees(sigma_rad)
                    
                    with st.container(border=True):
                        res_c1, res_c2 = st.columns([1, 1.5])
                        with res_c1:
                            st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_deg:.2f} °S")
                            
                            # Interpretacija glede na Petričevo lestvico
                            if sigma_deg <= 15.0:
                                st.info("Stopnja: Zelo nizka")
                            elif sigma_deg <= 30.0:
                                st.success("Stopnja: Nizka (Značilno za knjižnico/urejena okolja)")
                            elif sigma_deg <= 45.0:
                                st.warning("Stopnja: Srednja")
                            else:
                                st.error("Stopnja: Visoka (Kritično območje)")
                        
                        with res_c2:
                            st.write(f"**Podatki izračuna za N = {n_input}:**")
                            st.markdown(f"""
                            * $F_{{oSF}}$ (Stresni faktor): **{f_sf:.4f}**
                            * $F_{{oPF}}$ (Pozitivni faktor): **{f_pf:.4f}**
                            * $F_{{oPR}}$ (Faktor predlogov): **{f_pr:.4f}**
                            """)
                            st.progress(min(sigma_deg / 90, 1.0))
                            st.caption("Psihosocialni barometer stresa (0°S do 90°S)")
                except Exception as e:
                    st.error(f"Napaka pri izračunu (preverite raznolikost podatkov): {e}")

            # 3. SEKCIJA: VIZUALIZACIJA
            st.divider()
            st.header("📈 Frekvenčna porazdelitev po enotah")
            tabs = st.tabs([f"📊 {target_cols[0]}", f"📊 {target_cols[1]}", f"📊 {target_cols[2]}"])
            for i, tab in enumerate(tabs):
                with tab:
                    st.bar_chart(results[target_cols[i]].set_index('Klasifikacijska enota'), color="#1C83E1")
                    
        except Exception as e:
            st.error(f"Napaka pri obdelavi datoteke: {e}")
    else:
        st.info("Naložite datoteko v stranskem meniju za začetek analize.", icon="ℹ️")

if __name__ == "__main__":
    main()



