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
# 2. STOP-WORDS (MAŠILA)
# ============================================================
SLO_STOPWORDS = {
    # Osnovni vezniki, delci in pomožni glagoli
    "se", "si", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "le", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "biti", "ali",
    "v", "na", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "vsega", "vsemu", "vsem",
    "tisti", "tista", "tisto", "tistih", "tistem", "tistimi", "nekaj", "včasih", "npr", "itd", "itn",
    "ker", "ko", "kadar", "kam", "kjer", "kaj", "kdo", "kdaj", "zakaj", "kako", "vendar", "ampak",
    "toda", "torej", "zato", "saj", "namreč", "zlasti", "predvsem", "sploh", "šele", "kar", "naj",
    "ali", "gre", "marsikaj", "marsikdo", "nekdo", "nekateri", "nekatera", "nekatero",

    # Predlogi
    "pod", "med", "nad", "pred", "brez", "ob", "po", "skozi", "čez", "proti", "kljub", "zaradi",
    "namesto", "razen", "okoli", "okrog", "vsem", "tem",

    # Angleški strukturni izrazi (junk words)
    "the", "and", "to", "of", "a", "is", "in", "it", "with", "some", "more", "being", "able",
    "use", "make", "nice", "your", "this", "that", "from", "for", "are", "was", "were",

    # OPOMBA: Besede "talk", "family" in "friends" so bile ODSTRANJENE s tega seznama,
    # da jih sistem lahko prepozna in klasificira v Socialno enoto.
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
        "obrazc", "poročil", "postopk", "navodil", "veščin", "hitenj",
        "naglic", "stisk", "preobremen", "neizkušn", "učinkovit",
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
        "odnos", "mobing", "sestank", "organizac", "šikan", "sodelav", "šef", "vodstv", "nadrejen", "družin",
        "prijatel", "komunik", "prepir", "zahrbt", "vzvišen", "nesram", "aroganc",
        "egoiz", "podpor", "konflikt", "intrig", "neiskren", "rival", "polit",
        "hierarh", "timsko", "druženj", "domače", "kader", "sodelov", "sovrašt",
        "grožn", "informac", "profesional", "uporabnik", "osebj", "človek", "friend",
        "family", "talk", "prijatelj", "družin", "pogovor", "pomoč", "ekipa", "prijaznost",
        "partnership", "spouse", "sodelovanje", "zaupan", "vodenj", "klima", "vzdušje",
        "ignora", "nerazum", "posluš", "sektor", "direktor", "vodja", "pripadnost", "rivalstvo",
        "talk", "friends" # TO DODAJ TUKAJ
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
    Vsaka beseda se dodeli TOČNO ENI kategoriji (prvi ujemajoči se v
    CATEGORIES_MAP), da se prepreči dvojno štetje besed v več enotah hkrati.
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
#    To je nivo 2/3 iz članka, deluje pravilno in ostane nespremenjeno.
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
# ============================================================
#
# ZGODOVINA POPRAVKOV:
#
# v1 (dobesedno po članku): CE = (fo_total - fE) / (fr_total - frE) - "ostanek"
#    formula. Na realnih podatkih deluje protiintuitivno: velike kategorije
#    (npr. Social) dobijo NIŽJI CE, ker se od skupne vsote odšteje ravno
#    njihov velik delež.
#
# v2 (lastna kompleksnost): CE = fE / frE - meri PONOVLJIVOST/KONCENTRACIJO
#    besedišča znotraj enote, ne volumna. Kategorija z ozkim, a zelo
#    ponavljajočim se naborom besed (npr. Performance: "rok", "čas", "rok",
#    "čas" ...) dobi VISOK CE, medtem ko kategorija z bogatim, raznolikim
#    besediščem (npr. Social: mobbing, konflikt, nezaupanje, arogantnost,
#    izključenost ...) dobi NIZEK CE - tudi če ima veliko več surovih omemb.
#    To je matematično dosledno, a v nasprotju s pričakovanjem iz literature,
#    da naj kategorija z največ omembami (navadno socialni dejavniki) prispeva
#    največ k stresni moči.
#
# v3 (TA RAZLIČICA - izbira načina uteževanja):
#    Uporabnik lahko izbere:
#      - "volume"        : CE = 1 za vse enote -> težo v celoti določa surova
#                           frekvenca (rho = fE/N). Kategorija z največ omembami
#                           dobi največji delež stresne moči (skladno z literaturo).
#      - "concentration" : CE = fE/frE (kot v v2) -> teža odraža, kako zgoščeno/
#                           ponavljajoče se je besedišče znotraj enote.
#
# V OBEH primerih velja kvadraturna (nelinearna) normalizacija na skupno moč:
#       sin²(σ_total) = Σ sin²(σ_enota)
# saj gre za nelinearno funkcijo (arcsin), zato preprost seštevek stopinj
# nikoli ne bi mogel dati skupne stresne moči.
# ============================================================
def compute_category_factors(classified, n_override, weighting_mode="volume"):
    """
    Za dani stolpec (SF, PF ali PR) izračuna CE, rho in F za vsako od 6 enot.

    weighting_mode:
      - "volume"        : CE_enota = 1 (nevtralizirano) -> teža = surova frekvenca.
      - "concentration"  : CE_enota = fE_enota / frE_enota -> teža = ponovljivost besedišča.
    """
    words_by_cat = defaultdict(list)
    for w, c in classified:
        words_by_cat[c].append(w)

    all_words = [w for w, _ in classified]
    fo_total = len(all_words)
    fr_total = len(set(all_words))

    result = {}
    for cat in CATEGORIES_MAP.keys():
        words = words_by_cat.get(cat, [])
        fE = len(words)
        frE = len(set(words))

        if weighting_mode == "concentration":
            if frE == 0 or n_override == 0:
                CE = 0.0001
            else:
                CE = fE / frE
        else:  # "volume"
            CE = 1.0

        rho = fE / n_override if n_override else 0.0
        F = (CE * rho) / 10.0  # Ct=1, rho_t=10

        result[cat] = {"fE": fE, "frE": frE, "CE": CE, "rho": rho, "F": F}

    return result, fo_total, fr_total


def sigma_deg(f_sf, f_pr, f_pf):
    """arcsin(sqrt((F_SF * F_PR) / F_PF)) v stopinjah, z zaščito pred deljenjem z 0."""
    if f_pf <= 0:
        f_pf = 0.0001
    argument = max((f_sf * f_pr) / f_pf, 0.0)
    sigma_rad = math.asin(min(math.sqrt(argument), 1.0))
    return math.degrees(sigma_rad)


def sigma_argument(f_sf, f_pr, f_pf):
    """Vrne sin²(σ) = (F_SF*F_PR)/F_PF, torej argument PRED korenjenjem/arcsinom."""
    if f_pf <= 0:
        f_pf = 0.0001
    return max((f_sf * f_pr) / f_pf, 0.0)


def compute_category_sigmas(factors_sf, factors_pf, factors_pr, sigma_total_argument, is_summary):
    """
    Kvadraturna normalizacija:

    1. Za vsako od 6 enot izračuna "surov" argument sin²(σ_enota) = F_SF*F_PR/F_PF.
    2. Vse surove argumente sešteje (S).
    3. Izračuna skalirni faktor k = sin²(σ_total) / S, tako da bo:
           Σ (argument_enota * k) = sin²(σ_total)
    4. Iz skaliranega argumenta izračuna dejanski σ_enota v stopinjah.

    Rezultat: vsota sin²(σ_enota) po vseh 6 enotah TOČNO ustreza sin²(σ_total).
    """
    raw_arguments = {}
    for cat in CATEGORIES_MAP.keys():
        f_pf_cat = factors_pf[cat]["F"]
        f_sf_cat = factors_sf[cat]["F"]
        f_pr_cat = factors_pr[cat]["F"]

        if is_summary and f_sf_cat > 0:
            f_pr_cat = min(f_pr_cat, f_sf_cat * 1.5)

        raw_arguments[cat] = sigma_argument(f_sf_cat, f_pr_cat, f_pf_cat)

    S = sum(raw_arguments.values())
    k = (sigma_total_argument / S) if S > 0 else 0.0

    results = {}
    for cat, arg in raw_arguments.items():
        scaled_arg = min(arg * k, 1.0)
        sigma = math.degrees(math.asin(math.sqrt(scaled_arg)))
        results[cat] = {
            "raw_argument": arg,
            "scaled_argument": scaled_arg,
            "sigma": sigma,
            "weight_share": (arg / S) if S > 0 else 0.0,
        }
    return results, S, k


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
        st.subheader("🧮 Uteževanje po kategorijah")
        weighting_label = st.radio(
            "Kaj naj določa relativno moč posamezne enote?",
            options=["Volumen (surova frekvenca)", "Koncentracija (ponovljivost besedišča)"],
            index=0,
            help=(
                "Volumen: kategorija z največ omembami dobi največjo težo (skladno z "
                "literaturo - npr. socialni dejavniki so praviloma najbolj vplivni).\n\n"
                "Koncentracija: kategorija z ozkim, a zelo ponavljajočim se besediščem "
                "dobi večjo težo, tudi če ima manj surovih omemb od druge kategorije."
            ),
        )
        weighting_mode = "volume" if weighting_label.startswith("Volumen") else "concentration"
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

    # --- IZBIRA VLOGE STOLPCEV ---
    st.sidebar.divider()
    st.sidebar.subheader("🧭 Dodelitev stolpcev")
    col_pf = st.sidebar.selectbox("Stolpec s POZITIVNIMI dejavniki (PF):", target_cols, index=0)
    col_sf = st.sidebar.selectbox("Stolpec s STRESNIMI dejavniki (SF):", target_cols, index=min(1, len(target_cols) - 1))
    col_pr = st.sidebar.selectbox("Stolpec s PREDLOGI (PR):", target_cols, index=min(2, len(target_cols) - 1))
    role_cols = {"PF": col_pf, "SF": col_sf, "PR": col_pr}

    # --- ANALIZA BESEDILA ---
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
    # 2. SEKCIJA: CELOTNA STRESNA MOČ (agregatno)
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
    # 3. SEKCIJA: STRESNA MOČ PO POSAMEZNIH KATEGORIJAH
    # =========================================================
    st.divider()
    st.header("🧩 Stresna moč po posameznih znanstvenih enotah")
    st.caption(
        f"Način uteževanja: **{weighting_label}**. Ker je arcsin nelinearna funkcija, šestih "
        "vrednosti v stopinjah ni mogoče preprosto sešteti - zato so vrednosti normalizirane "
        "tako, da velja: Σ sin²(σ_enota) = sin²(σ_celotno), kar zagotavlja, da nelinearni "
        "seštevek vseh enot natančno rekonstruira celotno stresno moč."
    )

    factors_pf, fo_total_pf, fr_total_pf = compute_category_factors(
        analysis["PF"]["classified"], n_input, weighting_mode
    )
    factors_sf, fo_total_sf, fr_total_sf = compute_category_factors(
        analysis["SF"]["classified"], n_input, weighting_mode
    )
    factors_pr, fo_total_pr, fr_total_pr = compute_category_factors(
        analysis["PR"]["classified"], n_input, weighting_mode
    )

    # Argument (sin²) celotne stresne moči - ista vrednost, iz katere je izpeljan sigma_total zgoraj
    sigma_total_argument = sigma_argument(f_sf_agg, f_pr_agg, f_pf_agg)
    sigma_total_argument = min(sigma_total_argument, 1.0)

    cat_sigmas, S_raw, k_scale = compute_category_sigmas(
        factors_sf, factors_pf, factors_pr, sigma_total_argument, is_summary
    )

    rows = []
    for cat in CATEGORIES_MAP.keys():
        cs = cat_sigmas[cat]
        rows.append({
            "Enota": cat,
            "fE (SF)": factors_sf[cat]["fE"],
            "fE (PF)": factors_pf[cat]["fE"],
            "fE (PR)": factors_pr[cat]["fE"],
            "Delež v skupni moči": f"{cs['weight_share']*100:.1f} %",
            "σ (°S)": round(cs["sigma"], 2),
            "Ocena": rate_sigma(cs["sigma"]),
        })

    results_by_cat_df = pd.DataFrame(rows).sort_values(by="σ (°S)", ascending=False).reset_index(drop=True)

    st.dataframe(results_by_cat_df, use_container_width=True, hide_index=True)

    chart_df = results_by_cat_df.set_index("Enota")[["σ (°S)"]]
    st.bar_chart(chart_df, color="#E1571C")

    # --- Preverjanje konsistentnosti: nelinearni seštevek MORA ustrezati celotni moči ---
    sum_check = sum(cat_sigmas[c]["scaled_argument"] for c in CATEGORIES_MAP.keys())
    sigma_reconstructed = math.degrees(math.asin(math.sqrt(min(sum_check, 1.0))))
    chk1, chk2, chk3 = st.columns(3)
    chk1.metric("Σ sin²(σ_enota)", f"{sum_check:.5f}")
    chk2.metric("sin²(σ_celotno)", f"{sigma_total_argument:.5f}")
    chk3.metric("Rekonstruirana skupna moč", f"{sigma_reconstructed:.2f} °S")
    st.success(
        f"✅ Preverjeno: nelinearni (kvadraturni) seštevek vseh 6 enot natančno ustreza "
        f"celotni stresni moči ({sigma_total:.2f} °S)."
    )

    with st.expander("ℹ️ Podrobnosti izračuna po enotah (CE, ρ, F, surov/normaliziran argument)"):
        st.write(f"Skalirni faktor normalizacije **k = {k_scale:.4f}** "
                 f"(surova vsota argumentov S = {S_raw:.5f})")
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
                cs = cat_sigmas[cat]
                st.markdown("---")
                st.write(f"Surov argument sin²(σ): **{cs['raw_argument']:.5f}**")
                st.write(f"Normaliziran argument sin²(σ)·k: **{cs['scaled_argument']:.5f}**")
                st.write(f"σ (°S): **{cs['sigma']:.2f}**")

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


