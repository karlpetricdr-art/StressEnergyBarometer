import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. FUNKCIJA ZA RESET ---
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# --- 2. DEFINICIJA STOP-WORDS (MAŠIL) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "bi", "bil", "bila", "bi", "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi",
    "tisti", "nekaj", "včasih", "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it", "gre", "vse"
}

# --- 3. CELOTEN ZNANSTVENO RAZŠIRJEN KLASIFIKACIJSKI MODEL ---
# Vključuje MNZ, Policijo, JU in specifične knjižnične termine
CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "svetlob", "razsvetlj", "vroč", "mraz", "vrem", "prostor", "pisarn", "ergonom", 
        "oprem", "tišin", "zrak", "prah", "gneč", "tehni", "akcij", "poškodb", "varna", "objekt", 
        "sodobn", "naprav", "urejenost", "etiket", "izolac", "barv", "rastlin", "vonjav", 
        "stol", "miz", "prezrač", "čistoč", "higien"
    ],
    "Performance unit": [
        "rok", "deadline", "obremen", "nalog", "oprav", "čas", "administra", "birokra", 
        "obrazc", "poročil", "sestank", "postopk", "navodil", "znanj", "veščin", "hitenj", 
        "naglic", "stisk", "preobremen", "neizkušn", "strokov", "organizac", "učinkovit", 
        "biro", "togi", "rutin", "nujne", "izobraž", "usposab", "optimiz", "proces", 
        "poenostav", "inovac", "rešitev", "urnik", "ure", "izvajanj", "regula", "hrm", 
        "direktiv", "ukaluplj", "iskanj", "gradiv", "polic", "katalog", "orientac", "iskanj"
    ],
    "Individual Psychological unit": [
        "strah", "tesnob", "optimiz", "pozitiv", "samozav", "čustv", "stres", "frustr", 
        "mir", "negotov", "nervoz", "panik", "nemoč", "skrb", "napetos", "psih", "travm", 
        "osebno", "samopodob", "nasil", "negativ", "dušev", "žalost", "ogroženost", 
        "zaupan", "klima", "razmišlj", "nelagod", "zadovolj", "psihi", "tesnob"
    ],
    "Partial social unit": [
        "plač", "dohod", "denar", "finanč", "nagrad", "status", "priznan", "revšč", 
        "standar", "nepravič", "nestimul", "krivic", "dostojen", "zaposlit", "služb", 
        "karier", "napredov", "varnost", "staž", "benefic", "ekonom", "proračun", 
        "pokojnin", "sredstv", "zamudn", "opomin", "kazn", "plačev", "finanč"
    ],
    "Social unit": [
        "odnos", "mobing", "šikan", "sodelav", "šef", "vodstv", "nadrejen", "družin", 
        "prijatel", "komunik", "prepir", "zahrbt", "vzvišen", "nesram", "aroganc", 
        "egoiz", "podpor", "konflikt", "intrig", "neiskren", "rival", "polit", 
        "hierarh", "timsko", "druženj", "domače", "kader", "sodelov", "tovar", 
        "sovrašt", "grožn", "informac", "profesional", "uporabnik", "osebj", "človek"
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

def calculate_fo_real(df, col, n_o):
    all_keywords_in_cat = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        for kw in kws:
            kw_lower = kw.lower()
            found = False
            for cat, kw_list in CATEGORIES_MAP.items():
                if any(koren in kw_lower for koren in kw_list): 
                    all_keywords_in_cat.append(kw)
                    found = True
                    break 
    
    fo = len(all_keywords_in_cat)
    fr = len(set(all_keywords_in_cat))
    if fr == 0 or n_o == 0: return 0.0001, fo, fr
    
    rho_o = fo / n_o
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr

# --- 5. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Stress Analysis Pro", page_icon="📊", layout="wide")
    
    # Reset gumb v sidebarju
    with st.sidebar:
        st.header("Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown("""
    Sistem analizira odgovore respondentov, izloči mašila in klasificira v **6 znanstvenih kategorij**.
    Izračun stresne moči sledi **3. nivoju Petričeve metode**.
    """)

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])
    
    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        try:
            # Uporabimo engine='python' in on_bad_lines='skip' za stabilnost
            df = pd.read_csv(uploaded_file, sep=sep, engine='python', on_bad_lines='skip')
            n_o = len(df)
            st.success(f"Datoteka uspešno naložena. Analiziramo **{n_o}** respondentov.", icon="✅")
            
            target_cols = df.columns.tolist()
            results = {}
            fo_real_factors = {}

            # 1. ANALIZA PO KATEGORIJAH
            st.header("🔍 Kvalitativna analiza po sklopih")
            for col in target_cols[:3]:
                with st.expander(f"Podrobnosti za sklop: {col}", expanded=True):
                    df[f'keywords_{col}'] = df[col].apply(clean_and_tokenize)
                    df[f'units_{col}'] = df[f'keywords_{col}'].apply(classify_keywords)
                    
                    all_units = [unit for sublist in df[f'units_{col}'].tolist() for unit in sublist]
                    unit_counts = Counter(all_units)
                    
                    freq_df = pd.DataFrame(unit_counts.items(), columns=['Klasifikacijska enota', 'Frekvenca']).sort_values(by='Frekvenca', ascending=False)
                    
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.caption("Klasificirani podatki (prvih 10 vrstic):")
                        st.dataframe(df[[col, f'units_{col}']].head(10), use_container_width=True)
                    with c2:
                        st.caption("Frekvence znanstvenih enot:")
                        st.table(freq_df)
                    
                    fo_real, fo_val, fr_val = calculate_fo_real(df, col, n_o)
                    fo_real_factors[col] = {"val": fo_real, "fo": fo_val, "fr": fr_val}
                    results[col] = freq_df

            # 2. IZRAČUN CELOKUPNE STRESNE MOČI (°S)
            st.divider()
            st.header("📐 Izračun celokupne stresne moči")
            
            if len(target_cols) >= 3:
                f_pf = fo_real_factors[target_cols[0]]["val"]
                f_sf = fo_real_factors[target_cols[1]]["val"]
                f_pr = fo_real_factors[target_cols[2]]["val"]
                
                try:
                    # Petričeva formula: sqrt((F_oSF * F_oPR) / F_oPF)
                    argument = math.sqrt((f_sf * f_pr) / f_pf)
                    sigma_rad = math.asin(min(argument, 1.0))
                    sigma_deg = math.degrees(sigma_rad)
                    
                    with st.container(border=True):
                        res_c1, res_c2 = st.columns([1, 1.5])
                        with res_c1:
                            st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_deg:.2f} °S")
                            
                            if sigma_deg <= 15.04:
                                st.info("Stopnja: Zelo nizka")
                            elif sigma_deg <= 30.04:
                                st.info("Stopnja: Nizka")
                            elif sigma_deg <= 45.04:
                                st.warning("Stopnja: Srednja")
                            else:
                                st.error("Stopnja: Višja / Visoka")
                        
                        with res_c2:
                            st.write("**Realni faktorji ($F_o$):**")
                            st.markdown(f"""
                            - Stresni ($F_{{oSF}}$): **{f_sf:.4f}** <small>(zadetkov: {fo_real_factors[target_cols[1]]['fo']})</small>
                            - Pozitivni ($F_{{oPF}}$): **{f_pf:.4f}** <small>(zadetkov: {fo_real_factors[target_cols[0]]['fo']})</small>
                            - Predlogi ($F_{{oPR}}$): **{f_pr:.4f}** <small>(zadetkov: {fo_real_factors[target_cols[2]]['fo']})</small>
                            """, unsafe_allow_html=True)
                            st.progress(min(sigma_deg / 90, 1.0))
                            st.caption("Psihosocialni barometer stresa (0°S - 90°S)")
                except Exception as e:
                    st.error(f"Napaka pri izračunu: {e}")

            # 3. GRAFIČNI PRIKAZ
            st.divider()
            st.header("📈 Porazdelitev po enotah")
            final_tabs = st.tabs([f"📊 {target_cols[0]}", f"📊 {target_cols[1]}", f"📊 {target_cols[2]}"])
            for i, tab in enumerate(final_tabs):
                with tab:
                    st.bar_chart(results[target_cols[i]].set_index('Klasifikacijska enota'), color="#1C83E1")
        except Exception as e:
            st.error(f"Napaka pri obdelavi datoteke: {e}")
    else:
        st.info("Naložite datoteko za začetek analize.", icon="ℹ️")

if __name__ == "__main__":
    main()



