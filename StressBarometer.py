import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# ============================================================
# STRESS ANALYSIS PRO
# Petrič – analiza več dejavnikov znotraj celotnega odgovora
# Brez atomizacije odgovorov
# ============================================================

# ============================================================
# 1. PETRIČEVE KLASIFIKACIJSKE ENOTE
# ============================================================

CATEGORIES_MAP = {
    "Attentive (physical) unit": [
        "hrup", "noise", "svetloba", "light", "vročina", "mraz",
        "cold", "weather", "vreme", "prostori", "office", "pisarna",
        "ergonomija", "equipment", "oprema", "tišina", "silence",
        "temperatura", "zrak", "hrupnost", "delovno okolje"
    ],

    "Performance unit": [
        "rok", "roki", "deadline", "deadlines", "obremenitev",
        "obremenjen", "obremenjena", "workload", "naloga", "naloge",
        "tasks", "čas", "time", "administracija", "administracija",
        "birokracija", "informacije", "information", "znanje",
        "delovni čas", "nadure", "overwork", "urgenca", "nujnost",
        "organizacija dela", "organizacija", "preveč dela",
        "premalo časa"
    ],

    "Individual Psychological unit": [
        "strah", "fear", "anxiety", "tesnoba", "optimism",
        "pozitivno", "samozavest", "self-confidence", "čustvo",
        "čustva", "stres", "stress", "frustracija", "frustration",
        "mir", "peace", "napetost", "napet", "skrbi", "skrb",
        "motivacija", "demotivacija", "nezadovoljstvo"
    ],

    "Partial social unit": [
        "plača", "salary", "denar", "money", "finance", "finan",
        "nagrada", "reward", "status", "recognition", "priznanje",
        "revščina", "poverty", "standard", "neenakost",
        "inequality", "nepravičnost", "krivičnost", "plačilo"
    ],

    "Social unit": [
        "odnos", "odnosi", "relationships", "mobing", "mobbing",
        "bullying", "harassment", "nadlegovanje", "sodelavec",
        "sodelavci", "colleagues", "šef", "boss", "vodja",
        "vodstvo", "družina", "family", "prijatelj", "prijatelji",
        "friends", "komunikacija", "communication", "prepir",
        "konflikt", "konflikti", "sodelovanje", "nespoštovanje"
    ],

    "Health biological unit": [
        "zdravje", "health", "bolezen", "illness", "šport",
        "sports", "exercise", "vadba", "prehrana", "diet",
        "spanje", "sleep", "utrujenost", "tiredness", "utrujen",
        "joga", "yoga", "meditacija", "meditation", "počitek",
        "rekreacija", "počivanje", "izčrpanost"
    ]
}


# ============================================================
# 2. SLOVENSKI IN ANGLEŠKI VZORCI
# ============================================================

POSITIVE_PATTERNS = [
    "šport",
    "vadba",
    "rekreacija",
    "meditacija",
    "joga",
    "počitek",
    "spanje",
    "dober spanec",
    "dobra komunikacija",
    "podpora",
    "podpora sodelavcev",
    "podpora vodstva",
    "dober odnos",
    "dobri odnosi",
    "sodelovanje",
    "priznanje",
    "nagrada",
    "fleksibilnost",
    "avtonomija",
    "samostojnost",
    "mir",
    "pozitivno okolje",
    "dobra organizacija",
    "dobra organizacija dela",
    "zdrava prehrana",
    "družina",
    "prijatelji",
    "family",
    "friends",
    "exercise",
    "meditation",
    "yoga",
    "support",
    "good communication",
    "good relationships",
    "autonomy",
    "flexibility",
    "rest",
    "sleep"
]

PROPOSAL_PATTERNS = [
    "predlagam",
    "predlagal",
    "predlagala",
    "predlagati",
    "potrebno je",
    "treba je",
    "morali bi",
    "morala bi",
    "moral bi",
    "naj se",
    "naj bi",
    "potrebujemo",
    "potrebna je",
    "potrebno bi bilo",
    "priporočam",
    "priporočljivo je",
    "rešitev je",
    "rešitve so",
    "uvesti",
    "izboljšati",
    "zmanjšati",
    "povečati",
    "odpraviti",
    "organizirati",
    "omogočiti",
    "zagotoviti",
    "več",
    "manj",
    "predlog",
    "proposal",
    "suggest",
    "should",
    "need to",
    "reduce",
    "increase",
    "improve"
]


# ============================================================
# 3. POMOŽNE FUNKCIJE
# ============================================================

def normalize_text(text):
    """
    Normalizira besedilo, vendar ga NE atomizira.
    Celoten odgovor ostane analitična enota.
    """
    if pd.isna(text):
        return ""

    text = str(text).strip().lower()

    # odstrani odvečne presledke
    text = re.sub(r"\s+", " ", text)

    return text


def split_sentences(text):
    """
    Razdeli odgovor samo na stavke zaradi lažjega iskanja
    različnih dejavnikov. To NI atomizacija na besede.
    """
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?;])\s+", text)

    return [
        s.strip()
        for s in sentences
        if s.strip()
    ]


def contains_phrase(text, phrase):
    """
    Varno preverjanje prisotnosti pojma v celotnem odgovoru.
    """
    text = normalize_text(text)
    phrase = normalize_text(phrase)

    if not phrase:
        return False

    return phrase in text


# ============================================================
# 4. KLASIFIKACIJA CELOTNEGA ODGOVORA
# ============================================================

def classify_response(text):
    """
    V celotnem odgovoru poišče VSE Petričeve klasifikacijske enote.
    En odgovor lahko vsebuje več različnih enot.
    """

    text = normalize_text(text)

    found_categories = []

    for category, keywords in CATEGORIES_MAP.items():

        for keyword in keywords:

            if contains_phrase(text, keyword):
                found_categories.append(category)
                break

    return found_categories


# ============================================================
# 5. ISKANJE VEČ STRESNIH DEJAVNIKOV
# ============================================================

def detect_stress_factors(text):
    """
    Poišče več različnih stresnih dejavnikov znotraj istega
    celotnega odgovora.

    Ne uporablja atomizacije posameznih besed.
    """

    text = normalize_text(text)

    found = []

    # Stresni izrazi po posameznih kategorijah
    stress_keywords = {

        "Attentive (physical) unit": [
            "hrup", "svetloba", "vročina", "mraz", "slabi prostori",
            "neustrezni prostori", "ergonomija", "oprema",
            "slabo delovno okolje", "hrupno okolje"
        ],

        "Performance unit": [
            "obremenitev", "preobremenitev", "preveč dela",
            "preveč nalog", "premalo časa", "roki", "kratki roki",
            "nadure", "delovni čas", "birokracija",
            "administracija", "nujnost", "organizacija dela",
            "slaba organizacija", "pomanjkanje časa"
        ],

        "Individual Psychological unit": [
            "stres", "strah", "tesnoba", "frustracija",
            "napetost", "skrb", "skrbi", "nezadovoljstvo",
            "izgorelost", "izčrpanost", "demotivacija"
        ],

        "Partial social unit": [
            "nizka plača", "prenizka plača", "slaba plača",
            "neustrezno plačilo", "finančna negotovost",
            "nepravičnost", "neenakost", "pomanjkanje priznanja"
        ],

        "Social unit": [
            "slabi odnosi", "konflikt", "konflikti", "prepir",
            "mobing", "nadlegovanje", "bullying", "slaba komunikacija",
            "nespoštovanje", "težave s šefom", "težave z vodstvom",
            "težave s sodelavci"
        ],

        "Health biological unit": [
            "pomanjkanje spanja", "slabo spanje", "nespečnost",
            "utrujenost", "izčrpanost", "bolezen",
            "zdravstvene težave", "premalo počitka"
        ]
    }

    for category, keywords in stress_keywords.items():

        for keyword in keywords:

            if contains_phrase(text, keyword):

                factor = {
                    "dejavnik": keyword,
                    "kategorija": category
                }

                if factor not in found:
                    found.append(factor)

    return found


# ============================================================
# 6. ISKANJE POZITIVNIH DEJAVNIKOV
# ============================================================

def detect_positive_factors(text):
    """
    Poišče več pozitivnih dejavnikov znotraj istega odgovora.
    """

    text = normalize_text(text)

    found = []

    for phrase in POSITIVE_PATTERNS:

        if contains_phrase(text, phrase):

            if phrase not in found:
                found.append(phrase)

    return found


# ============================================================
# 7. ISKANJE PREDLOGOV
# ============================================================

def detect_proposals(text):
    """
    Poišče predloge za zmanjšanje stresa.

    Predlog ni omejen na eno besedo.
    Sistem lahko zazna več predlogov v istem odgovoru.
    """

    text = normalize_text(text)

    sentences = split_sentences(text)

    proposals = []

    for sentence in sentences:

        is_proposal = False

        for pattern in PROPOSAL_PATTERNS:

            if pattern in sentence:
                is_proposal = True
                break

        if is_proposal:

            clean_sentence = sentence.strip()

            if clean_sentence and clean_sentence not in proposals:
                proposals.append(clean_sentence)

    return proposals


# ============================================================
# 8. OCENA INTENZIVNOSTI STRESNIH DEJAVNIKOV
# ============================================================

def estimate_intensity(text):
    """
    Hevristična ocena intenzivnosti 1–5.

    1 = zelo nizka
    2 = nizka
    3 = srednja
    4 = visoka
    5 = zelo visoka
    """

    text = normalize_text(text)

    very_high = [
        "izredno", "zelo močno", "popolnoma izčrpan",
        "izgorelost", "neznosno", "katastrofalno",
        "extreme", "extremely", "burnout"
    ]

    high = [
        "zelo", "močno", "veliko", "hudo", "preobremenjen",
        "preobremenitev", "stalno", "nenehno", "high"
    ]

    medium = [
        "pogosto", "večkrat", "problem", "težava",
        "stres", "frustracija", "medium"
    ]

    low = [
        "malo", "občasno", "rahlo", "manjša težava",
        "low"
    ]

    for phrase in very_high:
        if phrase in text:
            return 5

    for phrase in high:
        if phrase in text:
            return 4

    for phrase in medium:
        if phrase in text:
            return 3

    for phrase in low:
        if phrase in text:
            return 2

    return 3


# ============================================================
# 9. ANALIZA ENEGA CELOTNEGA ODGOVORA
# ============================================================

def analyze_response(text):

    text = normalize_text(text)

    if not text:
        return {
            "stresni_dejavniki": [],
            "pozitivni_dejavniki": [],
            "predlogi": [],
            "kategorije": [],
            "intenzivnost": 0,
            "SF_count": 0,
            "PF_count": 0,
            "PR_count": 0
        }

    stress_factors = detect_stress_factors(text)
    positive_factors = detect_positive_factors(text)
    proposals = detect_proposals(text)
    categories = classify_response(text)

    intensity = estimate_intensity(text)

    return {
        "stresni_dejavniki": stress_factors,
        "pozitivni_dejavniki": positive_factors,
        "predlogi": proposals,
        "kategorije": categories,
        "intenzivnost": intensity,
        "SF_count": len(stress_factors),
        "PF_count": len(positive_factors),
        "PR_count": len(proposals)
    }


# ============================================================
# 10. IZRAČUN STRESNE MOČI
# ============================================================

def calculate_stress_power(sf_weight, pf_weight, pr_weight):
    """
    Izračun stresne moči sigma v stresnih stopinjah.

    SF = stresni dejavniki
    PF = pozitivni dejavniki
    PR = predlogi

    Rezultat:
        0–50 stresnih stopinj
    """

    if sf_weight <= 0:
        return 0.0

    # Pozitivni dejavniki zmanjšujejo relativni stres
    stress_ratio = sf_weight / (pf_weight + 1.0)

    # Predlogi povečujejo potencial za zmanjšanje stresa
    recovery_factor = 1.0 + (pr_weight / 10.0)

    adjusted_ratio = stress_ratio / recovery_factor

    sigma = (
        math.log10(adjusted_ratio + 1.0) * 50.0
    )

    sigma = max(0.0, min(50.0, sigma))

    return round(sigma, 2)


# ============================================================
# 11. IZRAČUN ENERGIJE
# ============================================================

def calculate_energy(sigma):
    """
    Model energijske izgube pri osnovni razpoložljivi energiji
    2500 enot.
    """

    W_I = 2500.0

    energy_loss = W_I * sigma / 50.0

    useful_energy = W_I - energy_loss

    efficiency = (useful_energy / W_I) * 100.0

    return {
        "vhodna_energija": round(W_I, 2),
        "izguba_energije": round(energy_loss, 2),
        "uporabna_energija": round(useful_energy, 2),
        "ucinkovitost": round(efficiency, 2)
    }


# ============================================================
# 12. AGREGACIJA CELOTNEGA DATASETA
# ============================================================

def aggregate_results(results):

    total_sf = 0
    total_pf = 0
    total_pr = 0

    sf_weight = 0
    pf_weight = 0
    pr_weight = 0

    all_categories = []

    for result in results:

        sf = result["SF_count"]
        pf = result["PF_count"]
        pr = result["PR_count"]

        intensity = result["intenzivnost"]

        total_sf += sf
        total_pf += pf
        total_pr += pr

        # Stresni dejavniki so ponderirani z intenzivnostjo
        sf_weight += sf * intensity

        # Pozitivni dejavniki imajo nekoliko manjšo težo
        pf_weight += pf * 2

        # Predlog ima obnovitveni učinek
        pr_weight += pr * 2

        all_categories.extend(result["kategorije"])

    sigma = calculate_stress_power(
        sf_weight,
        pf_weight,
        pr_weight
    )

    energy = calculate_energy(sigma)

    return {
        "SF_count": total_sf,
        "PF_count": total_pf,
        "PR_count": total_pr,
        "SF_weight": sf_weight,
        "PF_weight": pf_weight,
        "PR_weight": pr_weight,
        "sigma": sigma,
        "energy": energy,
        "categories": Counter(all_categories)
    }


# ============================================================
# 13. GLAVNA STREAMLIT APLIKACIJA
# ============================================================

def main():

    st.set_page_config(
        page_title="Stress Analysis Pro",
        layout="wide"
    )

    st.title(
        "📊 Stress Analysis Pro – Petričeva analiza"
    )

    st.markdown(
        """
        Sistem analizira **celoten odgovor respondenta kot eno vsebinsko enoto**.

        Odgovor se ne atomizira na posamezne besede. Znotraj istega odgovora
        lahko sistem zazna **več stresnih dejavnikov, več pozitivnih dejavnikov
        in več predlogov**.

        Na podlagi rezultatov izračuna tudi **stresno moč σ v stresnih stopinjah
        (0–50)**.
        """
    )

    # ========================================================
    # DATOTEKA
    # ========================================================

    uploaded_file = st.sidebar.file_uploader(
        "Naložite .txt, .csv ali .xlsx datoteko",
        type=["txt", "csv", "xlsx"]
    )

    if uploaded_file is None:

        st.info(
            "Prosim, naložite podatkovno datoteko."
        )

        return

    # ========================================================
    # BRANJE DATOTEKE
    # ========================================================

    try:

        filename = uploaded_file.name.lower()

        if filename.endswith(".xlsx"):

            df = pd.read_excel(uploaded_file)

        elif filename.endswith(".txt"):

            try:
                df = pd.read_csv(
                    uploaded_file,
                    sep="\t"
                )
            except Exception:

                uploaded_file.seek(0)

                df = pd.read_csv(
                    uploaded_file,
                    sep=None,
                    engine="python"
                )

        else:

            df = pd.read_csv(uploaded_file)

    except Exception as e:

        st.error(
            f"Napaka pri branju datoteke: {e}"
        )

        return

    if df.empty:

        st.warning(
            "Datoteka ne vsebuje podatkov."
        )

        return

    st.success(
        f"Uspešno naloženo: {len(df)} vrstic."
    )

    # ========================================================
    # PREGLED PODATKOV
    # ========================================================

    with st.expander("👁️ Pregled surovih podatkov"):

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

    # ========================================================
    # IZBIRA STOLPCEV
    # ========================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "📌 Analizirani stolpci"
    )

    available_columns = df.columns.tolist()

    selected_columns = st.sidebar.multiselect(
        "Izberite stolpce za analizo",
        available_columns,
        default=available_columns
    )

    if not selected_columns:

        st.warning(
            "Izberite vsaj en stolpec."
        )

        return

    # ========================================================
    # ANALIZA
    # ========================================================

    all_analysis = []

    for column in selected_columns:

        st.divider()

        st.header(
            f"🔍 Analiza: {column}"
        )

        column_results = []

        for index, value in df[column].items():

            result = analyze_response(value)

            result["respondent"] = index + 1
            result["odgovor"] = value

            column_results.append(result)

            all_analysis.append(result)

        # ====================================================
        # TABELA POSAMEZNIH ODGOVOROV
        # ====================================================

        display_rows = []

        for result in column_results:

            stress_text = "; ".join(
                [
                    f"{x['dejavnik']} ({x['kategorija']})"
                    for x in result["stresni_dejavniki"]
                ]
            )

            positive_text = "; ".join(
                result["pozitivni_dejavniki"]
            )

            proposal_text = " | ".join(
                result["predlogi"]
            )

            category_text = "; ".join(
                result["kategorije"]
            )

            display_rows.append({
                "Respondent": result["respondent"],
                "Odgovor": result["odgovor"],
                "Stresni dejavniki": stress_text,
                "Pozitivni dejavniki": positive_text,
                "Predlogi": proposal_text,
                "Petričeve enote": category_text,
                "Intenzivnost": result["intenzivnost"],
                "SF": result["SF_count"],
                "PF": result["PF_count"],
                "PR": result["PR_count"]
            })

        result_df = pd.DataFrame(display_rows)

        st.dataframe(
            result_df,
            use_container_width=True,
            height=450
        )

        # ====================================================
        # AGREGACIJA TEGA STOLPCA
        # ====================================================

        aggregate = aggregate_results(
            column_results
        )

        # ====================================================
        # METRIKE
        # ====================================================

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Stresni dejavniki (SF)",
                aggregate["SF_count"]
            )

        with c2:
            st.metric(
                "Pozitivni dejavniki (PF)",
                aggregate["PF_count"]
            )

        with c3:
            st.metric(
                "Predlogi (PR)",
                aggregate["PR_count"]
            )

        with c4:
            st.metric(
                "Stresna moč σ",
                f"{aggregate['sigma']:.2f}°"
            )

        # ====================================================
        # STRESNA MOČ
        # ====================================================

        sigma = aggregate["sigma"]

        st.subheader(
            "🔥 Stresna moč"
        )

        st.progress(
            min(sigma / 50.0, 1.0)
        )

        if sigma < 10:

            st.success(
                f"Stresna moč: {sigma:.2f}° – zelo nizka"
            )

        elif sigma < 20:

            st.info(
                f"Stresna moč: {sigma:.2f}° – nizka"
            )

        elif sigma < 30:

            st.warning(
                f"Stresna moč: {sigma:.2f}° – zmerna"
            )

        elif sigma < 40:

            st.warning(
                f"Stresna moč: {sigma:.2f}° – visoka"
            )

        else:

            st.error(
                f"Stresna moč: {sigma:.2f}° – zelo visoka"
            )

        # ====================================================
        # MATEMATIČNI MODEL
        # ====================================================

        with st.expander(
            "🧮 Podrobnosti izračuna stresne moči"
        ):

            st.write(
                f"**SF utež:** {aggregate['SF_weight']:.2f}"
            )

            st.write(
                f"**PF utež:** {aggregate['PF_weight']:.2f}"
            )

            st.write(
                f"**PR utež:** {aggregate['PR_weight']:.2f}"
            )

            stress_ratio = (
                aggregate["SF_weight"] /
                (aggregate["PF_weight"] + 1.0)
            )

            recovery_factor = (
                1.0 +
                aggregate["PR_weight"] / 10.0
            )

            adjusted_ratio = (
                stress_ratio /
                recovery_factor
            )

            st.write(
                f"**Stress ratio:** {stress_ratio:.4f}"
            )

            st.write(
                f"**Recovery factor:** {recovery_factor:.4f}"
            )

            st.write(
                f"**Adjusted ratio:** {adjusted_ratio:.4f}"
            )

            st.write(
                "**Formula:** "
                "σ = log10(adjusted ratio + 1) × 50"
            )

            st.write(
                f"**Končna stresna moč:** "
                f"σ = {sigma:.2f} stresnih stopinj"
            )

        # ====================================================
        # ENERGIJSKI MODEL
        # ====================================================

        energy = aggregate["energy"]

        st.subheader(
            "⚡ Energijski model"
        )

        e1, e2, e3 = st.columns(3)

        with e1:

            st.metric(
                "Izguba energije",
                f"{energy['izguba_energije']:.2f}"
            )

        with e2:

            st.metric(
                "Uporabna energija",
                f"{energy['uporabna_energija']:.2f}"
            )

        with e3:

            st.metric(
                "Učinkovitost",
                f"{energy['ucinkovitost']:.2f}%"
            )

        # ====================================================
        # PETRIČEVE KATEGORIJE
        # ====================================================

        st.subheader(
            "🧠 Petričeve klasifikacijske enote"
        )

        category_counts = aggregate["categories"]

        if category_counts:

            category_df = pd.DataFrame(
                category_counts.items(),
                columns=[
                    "Klasifikacijska enota",
                    "Frekvenca"
                ]
            ).sort_values(
                "Frekvenca",
                ascending=False
            )

            st.dataframe(
                category_df,
                use_container_width=True
            )

            st.bar_chart(
                category_df.set_index(
                    "Klasifikacijska enota"
                )
            )

        else:

            st.info(
                "V odgovorih ni bilo mogoče zaznati "
                "Petričevih klasifikacijskih enot."
            )

    # ========================================================
    # SKUPNI REZULTAT VSEH STOLPCEV
    # ========================================================

    if all_analysis:

        st.divider()

        st.header(
            "📈 Skupna analiza vseh odgovorov"
        )

        global_result = aggregate_results(
            all_analysis
        )

        g1, g2, g3, g4 = st.columns(4)

        with g1:
            st.metric(
                "Skupaj SF",
                global_result["SF_count"]
            )

        with g2:
            st.metric(
                "Skupaj PF",
                global_result["PF_count"]
            )

        with g3:
            st.metric(
                "Skupaj PR",
                global_result["PR_count"]
            )

        with g4:
            st.metric(
                "SKUPNA STRESNA MOČ",
                f"{global_result['sigma']:.2f}°"
            )

        st.progress(
            min(global_result["sigma"] / 50.0, 1.0)
        )

        st.caption(
            "Stresna moč je izražena v stresnih stopinjah "
            "na lestvici 0–50."
        )


# ============================================================
# ZAGON
# ============================================================

if __name__ == "__main__":
    main()



