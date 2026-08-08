import streamlit as st
import pandas as pd
import re
import math
from collections import Counter, defaultdict

# ============================================================
# 1. PONASTAVITEV APLIKACIJE
# ============================================================
def reset_app():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

# ============================================================
# 2. STOP-WORDS
# ============================================================
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "tisti", "nekaj", "včasih",
    "npr", "itd", "the", "and", "to", "of", "a", "is", "in", "it", "with", "some", "more",
    "being", "able", "use", "make", "nice", "talk", "more", "family", "friends", "your",
    "gre", "vsem", "tem", "zaradi", "nekaj", "pod", "med", "tudi", "kar", "naj", "ali",
    "tistega", "tistem", "tistimi", "tistih", "tista", "tisto", "vsega", "vsemu", "vsem"
}

# ============================================================
# 3. KLASIFIKACIJSKI MODEL (6 znanstvenih enot po Petriču, 2025)
# Vrstni red slovarja je pomemben: vsaka beseda se dodeli PRVI
# ujemajoči se kategoriji (glej classify_word_single), da se
# prepreči dvojno štetje besed v več enotah hkrati.
# ============================================================
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

# Lestvica ocenjevanja moči stresa (Tabela 6 v članku)
RATING_SCALE = [
    (15.04, "Zelo nizka"),
    (30.04, "Nizka"),
    (45.04, "Srednja"),
    (60.04, "Višja"),
    (75.04, "Visoka"),
    (90.01, "Zelo visoka"),
]

def rate_sigma(sigma):
    for threshold, label in RATING_SCALE:
        if sigma <= threshold:
            return label
    return "Zelo visoka"

# ============================================================
# 4. POMOŽNE FUNKCIJE ZA OBDELAVO BESEDILA
# ============================================================

def clean_and_tokenize(text):
    """Odstrani ločila, pretvori v male črke in izloči mašila."""
    if not isinstance(text, str):
        return []
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    return [w for w in words if w not in SLO_STOPWORDS and len(w) > 2]


def classify_word_single(word):
    """
    KLJUČNI POPRAVEK: vsaka beseda se dodeli TOČNO ENI kategoriji
    (prvi ujemajoči se v CATEGORIES_MAP). V prejšnji različici se je
    ista beseda lahko štela v več enotah hkrati, kar je napihnilo fo/fr
    in onemogočilo pravilen izračun CE po enačbi (3) iz članka.
    """
    for cat, kw_list in CATEGORIES_MAP.items():
        if any(koren in word for koren in kw_list):
            return cat
    return None


def analyze_column(df, col):
    """
    Klasificira vse besede v stolpcu.
    Vrne:
      - classified: seznam (beseda, kategorija) za VSE klasificirane besede v stolpcu
      - per_row_categories: seznam seznamov kategorij, po vrsticah (za kvalitativni prikaz)
    """
    classified = []
    per_row_categories = []
    for row in df[col].dropna():
        kws = clean_and_tokenize(row)
        row_cats = []
        for kw in kws:
            cat = classify_word_single(kw)
            if cat:
                classified.append((kw, cat))
                row_cats.append(cat)
        per_row_categories.append(row_cats)
    return classified, per_row_categories


# ============================================================
# 5. IZRAČUN REALNEGA FAKTORJA Fo - AGREGATNO (za CELOTNO stresno moč)
#    To je nivo 2/3 iz članka, tako kot je delovalo v prvotni kodi.
# ============================================================
def calculate_fo_real_aggregate(classified, n_override):
    all_words = [w for w, _ in classified]
    fo = len(all_words)
    fr = len(set(all_words))
    if fr == 0 or n_override == 0:
        return 0.0001, fo, fr
    rho_o = fo / n_override
    c_o = fo / fr
    fo_real = (c_o * rho_o) / 10
    return fo_real, fo, fr


# ============================================================
# 6. IZRAČUN REALNEGA FAKTORJA Fo - PO POSAMEZNIH ENOTAH (KATEGORIJAH)
#    To implementira enačbe (3) in (4) iz članka za VSAKO od 6 enot
#    (primer izračuna AtSF/AtPF/AtPR v članku, enačbe 28-36).
# ============================================================
def compute_category_factors(classified, n_override):
    """
    Za dani stolpec (SF, PF ali PR) izračuna CE, rho in F za vsako od 6 enot.

    CE_enota = (fo_total - fE_enota) / (fr_total - frE_enota)   ... enačba (3)
    rho_enota = fE_enota / N
    F_enota   = (CE_enota * rho_enota) / (Ct * rho_t)  =  CE * rho / 10   ... enačba (4)

    kjer je fo_total/fr_total skupna frekvenca/raznolikost VSEH klasificiranih
    besed v stolpcu (torej vseh 6 enot skupaj), fE/frE pa frekvenca/raznolikost
    besed SAMO te posamezne enote.
    """
    all_words = [w for w, _ in classified]
    fo_total = len(all_words)
    fr_total = len(set(all_words))

    words_by_cat = defaultdict(list)
    for w, c in classified:
        words_by_cat[c].append(w)

    result = {}
    for cat in CATEGORIES_MAP.keys():
        words = words_by_cat.get(cat, [])
        fE = len(words)
        frE = len(set(words))

        denom_fr = fr_total - frE
        if denom_fr <= 0 or n_override == 0:
            CE = 0.0001
        else:
            CE = (fo_total - fE) / denom_fr

        rho = fE / n_override if n_override else 0.0
        F = (CE * rho) / 10.0  # Ct=1, rho_t=10

        result[cat] = {"fE": fE, "frE": frE, "CE": CE, "rho": rho, "F": F}

    return result, fo_total, fr_total


def sigma_deg(f_sf, f_pr, f_pf):
    """arcsin(sqrt((F_SF * F_PR) / F_PF)) v stopinjah, z zaščito pred deljenjem z 0."""
    if f_pf <= 0:
        f_pf = 0.0001  # enaka zaščita kot pri agregatnem izračunu v prvotni kodi
    argument = math.sqrt(max((f_sf * f_pr) / f_pf, 0.0))
    sigma_rad = math.asin(min(argument, 1.0))
    return math.degrees(sigma_rad)


# ============================================================
# 7. STREAMLIT UPORABNIŠKI VMESNIK
# ============================================================

def main():
    st.set_page_config(page_title="Petrič Stress Barometer Pro", page_icon="📊", layout="wide")

    # --- STRANSKI MENI ---
    with st.sidebar:
        st.header("⚙️ Nastavitve")
        if st.button("🔄 Ponastavi aplikacijo", use_container_width=True):
            reset_app()
        st.divider()
        st.subheader("📊 Parametri raziskave")
        n_input = st.number_input("Dejansko število respondentov (N):", min_value=1, value=210,
                                   help="Vpišite število ljudi, ki so dejansko sodelovali v raziskavi.")
        is_summary = st.checkbox("Ali naložena datoteka vsebuje POVZETEK?", value=True,
                                  help="Če nalagate že strnjene odgovore, sistem uporabi normalizacijski faktor.")
        st.divider()
        st.info("Koda temelji na Petričevi metodi izračuna stresne moči v stopinjah (°S).")

    st.title("📊 Klasifikacija stresnih dejavnikov po Petričevi metodi")
    st.markdown(f"Trenutna kalibracija: **N = {n_input}** respondentov.")

    uploaded_file = st.sidebar.file_uploader("Naložite .txt ali .csv datoteko", type=['txt', 'csv'])

    if not uploaded_file:
        st.info("Naložite datoteko v stranskem meniju za pričetek analize.", icon="ℹ️")
        return

    sep = '\t' if uploaded_file.name.endswith('.txt') else ','
    try:
        df = pd.read_csv(uploaded_file, sep=sep, engine='python', on_bad_lines='skip')
    except Exception as e:
        st.error(f"Napaka pri obdelavi datoteke: {e}")
        return

    st.success(f"Datoteka uspešno naložena. Število vrstic v tabeli: {len(df)}.", icon="✅")
    target_cols = df.columns.tolist()

    if len(target_cols) < 3:
        st.error("Datoteka mora vsebovati vsaj 3 stolpce: pozitivni dejavniki (PF), stresni dejavniki (SF) "
                  "in predlogi za zmanjšanje stresa (PR).")
        return

    # --- IZBIRA VLOGE STOLPCEV (namesto trde predpostavke po vrstnem redu) ---
    st.sidebar.divider()
    st.sidebar.subheader("🧭 Dodelitev stolpcev")
    col_pf = st.sidebar.selectbox("Stolpec s POZITIVNIMI dejavniki (PF):", target_cols, index=0)
    col_sf = st.sidebar.selectbox("Stolpec s STRESNIMI dejavniki (SF):", target_cols, index=min(1, len(target_cols) - 1))
    col_pr = st.sidebar.selectbox("Stolpec s PREDLOGI (PR):", target_cols, index=min(2, len(target_cols) - 1))
    role_cols = {"PF": col_pf, "SF": col_sf, "PR": col_pr}

    # --- ANALIZA BESEDILA (enotno za oba tipa izračuna) ---
    analysis = {}
    for role, col in role_cols.items():
        classified, per_row_categories = analyze_column(df, col)
        analysis[role] = {"col": col, "classified": classified, "per_row": per_row_categories}

    # =========================================================
    # 1. SEKCIJA: KVALITATIVNA ANALIZA PO SKLOPIH
    # =========================================================
    st.header("🔍 Kvalitativna analiza po sklopih")
    freq_tables = {}
    for role, col in role_cols.items():
        with st.expander(f"Podrobnosti za: {col} ({role})", expanded=True):
            per_row = analysis[role]["per_row"]
            display_df = pd.DataFrame({col: df[col].dropna().tolist(), "enote": per_row})

            all_units = [unit for sublist in per_row for unit in sublist]
            unit_counts = Counter(all_units)
            freq_df = pd.DataFrame(unit_counts.items(), columns=['Enota', 'Frekvenca']).sort_values(
                by='Frekvenca', ascending=False)
            freq_tables[role] = freq_df

            cl1, cl2 = st.columns([2, 1])
            with cl1:
                st.caption("Klasificirani primeri odgovorov:")
                st.dataframe(display_df.head(15), use_container_width=True)
            with cl2:
                st.caption("Frekvence znanstvenih enot:")
                st.table(freq_df)

    # =========================================================
    # 2. SEKCIJA: CELOTNA STRESNA MOČ (agregatno, kot prej - deluje pravilno)
    # =========================================================
    st.divider()
    st.header("📐 Izračun celokupne stresne moči")

    f_pf_agg, fo_pf, fr_pf = calculate_fo_real_aggregate(analysis["PF"]["classified"], n_input)
    f_sf_agg, fo_sf, fr_sf = calculate_fo_real_aggregate(analysis["SF"]["classified"], n_input)
    f_pr_agg, fo_pr, fr_pr = calculate_fo_real_aggregate(analysis["PR"]["classified"], n_input)

    if is_summary:
        f_pr_agg = min(f_pr_agg, f_sf_agg * 1.5)

    sigma_total = sigma_deg(f_sf_agg, f_pr_agg, f_pf_agg)

    with st.container(border=True):
        col_m1, col_m2 = st.columns([1, 1.5])
        with col_m1:
            st.metric(label="CELOKUPNA STRESNA MOČ", value=f"{sigma_total:.2f} °S")
            st.info(f"Stopnja: {rate_sigma(sigma_total)}")
        with col_m2:
            st.write(f"**Vrednosti realnih faktorjev (N={n_input}):**")
            st.markdown(f"""
            - Pozitivni ($F_{{oPF}}$): **{f_pf_agg:.4f}**
            - Stresni ($F_{{oSF}}$): **{f_sf_agg:.4f}**
            - Predlogi ($F_{{oPR}}$): **{f_pr_agg:.4f}**
            """)
            st.progress(min(sigma_total / 90, 1.0))
            st.caption("Petričev barometer stresa (0°S do 90°S)")

    # Energijska učinkovitost (enačbi 38-39 iz članka)
    st.subheader("⚡ Energijska poraba in učinkovitost")
    W_I = 2500.0
    W_EU = W_I - (W_I * sigma_total / 90.0)
    eta = (W_EU / W_I) * 100
    ec1, ec2, ec3 = st.columns(3)
    ec1.metric("Efektivna poraba energije", f"{W_EU:.0f} Kcal")
    ec2.metric("Energijska učinkovitost (η)", f"{eta:.2f} %")
    ec3.metric("Izguba energije zaradi stresa", f"{100 - eta:.2f} %")

    # =========================================================
    # 3. SEKCIJA: STRESNA MOČ PO POSAMEZNIH KATEGORIJAH (POPRAVLJENO)
    # =========================================================
    st.divider()
    st.header("🧩 Stresna moč po posameznih znanstvenih enotah")
    st.caption(
        "Izračunano po enačbah (3)-(11) iz članka: za vsako enoto (AtSF, StSF, IPSF, PSSF, SoSF, HBSF) "
        "se izračuna lasten realni faktor Fo na podlagi kompleksnosti CE, ki primerja frekvenco/raznolikost "
        "besed te enote s preostankom vseh klasificiranih besed v stolpcu."
    )

    factors_pf, fo_total_pf, fr_total_pf = compute_category_factors(analysis["PF"]["classified"], n_input)
    factors_sf, fo_total_sf, fr_total_sf = compute_category_factors(analysis["SF"]["classified"], n_input)
    factors_pr, fo_total_pr, fr_total_pr = compute_category_factors(analysis["PR"]["classified"], n_input)

    rows = []
    for cat in CATEGORIES_MAP.keys():
        F_pf_cat = factors_pf[cat]["F"]
        F_sf_cat = factors_sf[cat]["F"]
        F_pr_cat = factors_pr[cat]["F"]

        # Enaka normalizacija za povzetke kot pri agregatnem izračunu
        if is_summary:
            F_pr_cat = min(F_pr_cat, F_sf_cat * 1.5) if F_sf_cat > 0 else F_pr_cat

        sigma_cat = sigma_deg(F_sf_cat, F_pr_cat, F_pf_cat)

        rows.append({
            "Enota": cat,
            "fE (SF)": factors_sf[cat]["fE"],
            "fE (PF)": factors_pf[cat]["fE"],
            "fE (PR)": factors_pr[cat]["fE"],
            "F_SF": round(F_sf_cat, 5),
            "F_PF": round(F_pf_cat, 5),
            "F_PR": round(F_pr_cat, 5),
            "σ (°S)": round(sigma_cat, 2),
            "Ocena": rate_sigma(sigma_cat),
        })

    results_by_cat_df = pd.DataFrame(rows).sort_values(by="σ (°S)", ascending=False).reset_index(drop=True)

    st.dataframe(results_by_cat_df, use_container_width=True, hide_index=True)

    chart_df = results_by_cat_df.set_index("Enota")[["σ (°S)"]]
    st.bar_chart(chart_df, color="#E1571C")

    with st.expander("ℹ️ Podrobnosti izračuna po enotah (CE, ρ, F)"):
        detail_tabs = st.tabs(list(CATEGORIES_MAP.keys()))
        for tab, cat in zip(detail_tabs, CATEGORIES_MAP.keys()):
            with tab:
                d1, d2, d3 = st.columns(3)
                for label, factors_dict, colname in [
                    ("Stresni (SF)", factors_sf, col_sf),
                    ("Pozitivni (PF)", factors_pf, col_pf),
                    ("Predlogi (PR)", factors_pr, col_pr),
                ]:
                    f = factors_dict[cat]
                    with (d1 if label.startswith("Stresni") else d2 if label.startswith("Pozitivni") else d3):
                        st.write(f"**{label}** ({colname})")
                        st.write(f"fE = {f['fE']}, frE = {f['frE']}")
                        st.write(f"CE = {f['CE']:.4f}")
                        st.write(f"ρ = {f['rho']:.4f}")
                        st.write(f"F = {f['F']:.5f}")

    # =========================================================
    # 4. SEKCIJA: VIZUALNA PORAZDELITEV (kvalitativne frekvence)
    # =========================================================
    st.divider()
    st.header("📈 Vizualna porazdelitev po enotah (surove frekvence)")
    tabs = st.tabs([f"📊 {role_cols[r]} ({r})" for r in ["PF", "SF", "PR"]])
    for i, r in enumerate(["PF", "SF", "PR"]):
        with tabs[i]:
            fdf = freq_tables[r]
            if not fdf.empty:
                st.bar_chart(fdf.set_index('Enota'), color="#1C83E1")
            else:
                st.info("Ni klasificiranih besed v tem stolpcu.")


if __name__ == "__main__":
    main()


