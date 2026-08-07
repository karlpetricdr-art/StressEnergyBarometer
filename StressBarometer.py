import streamlit as st
import pandas as pd
import re
import math
from collections import Counter


# ============================================================
# PETRIČ STRESS POWER CALCULATOR
#
# Izračun celokupne stresne moči po:
# Karl Petrič (2025)
#
# σSF = arcsin(sqrt((FSF * FPR) / FPF))
#
# Rezultat: stresne stopinje °S
# ============================================================


# ============================================================
# 1. OSNOVNE NASTAVITVE MODELA
# ============================================================

THEORETICAL_DENSITY = 10.0
THEORETICAL_COMPLEXITY = 1.0


# ============================================================
# 2. PETRIČEVE KATEGORIJE
# ============================================================

CATEGORIES = {

    "Attentive": [
        "hrup",
        "svetloba",
        "vročina",
        "mraz",
        "temperatura",
        "vlažnost",
        "vonj",
        "neprijeten vonj",
        "prostori",
        "pisarna",
        "ergonomija",
        "oprema",
        "delovno okolje",
        "hrupno",
        "neustrezni prostori"
    ],

    "Performance": [
        "obremenitev",
        "preobremenitev",
        "preveč dela",
        "preveč nalog",
        "premalo časa",
        "pomanjkanje časa",
        "roki",
        "kratek rok",
        "nadure",
        "birokracija",
        "administracija",
        "administrativno delo",
        "delovni čas",
        "nujnost",
        "časovni pritisk",
        "organizacija dela",
        "slaba organizacija",
        "preveč dela",
        "zahteve",
        "pričakovanja"
    ],

    "Individual psychological": [
        "strah",
        "tesnoba",
        "anksioznost",
        "stres",
        "frustracija",
        "napetost",
        "skrb",
        "skrbi",
        "negotovost",
        "nezadovoljstvo",
        "izgorelost",
        "izčrpanost",
        "demotivacija",
        "pomanjkanje samozavesti",
        "samozavest"
    ],

    "Partial social": [
        "plača",
        "prenizka plača",
        "slaba plača",
        "plačilo",
        "denar",
        "finančna situacija",
        "finančna negotovost",
        "nagrada",
        "status",
        "priznanje",
        "nepravičnost",
        "neenakost",
        "standard",
        "davki",
        "stroški"
    ],

    "Social": [
        "odnosi",
        "slabi odnosi",
        "konflikt",
        "konflikti",
        "prepir",
        "mobing",
        "mobbing",
        "nadlegovanje",
        "sodelavci",
        "sodelavec",
        "šef",
        "vodja",
        "vodstvo",
        "komunikacija",
        "slaba komunikacija",
        "nespoštovanje",
        "medosebni odnosi"
    ],

    "Health biological": [
        "zdravje",
        "bolezen",
        "zdravstvene težave",
        "spanje",
        "slabo spanje",
        "pomanjkanje spanja",
        "utrujenost",
        "utrujen",
        "izčrpanost",
        "počitek",
        "premalo počitka",
        "prehrana",
        "slaba prehrana",
        "šport",
        "vadba",
        "rekreacija"
    ]
}


# ============================================================
# 3. POZITIVNI DEJAVNIKI
# ============================================================

POSITIVE_FACTORS = [

    "dobra komunikacija",
    "dobri odnosi",
    "podpora",
    "podpora sodelavcev",
    "podpora vodstva",
    "sodelovanje",
    "priznanje",
    "nagrada",
    "fleksibilnost",
    "samostojnost",
    "avtonomija",
    "dobra organizacija",
    "dobra organizacija dela",
    "dovolj časa",
    "mir",
    "počitek",
    "spanje",
    "dober spanec",
    "šport",
    "vadba",
    "rekreacija",
    "meditacija",
    "joga",
    "družina",
    "prijatelji",
    "zdrava prehrana",
    "pozitivno okolje",
    "dobri pogoji",
    "ustrezna oprema",
    "ustrezni prostori",
    "motivacija",
    "samozavest"
]


# ============================================================
# 4. PREDLOGI
# ============================================================

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
    "potrebujemo",
    "priporočam",
    "priporočljivo je",
    "naj se",
    "naj bi",
    "uvesti",
    "izboljšati",
    "zmanjšati",
    "povečati",
    "odpraviti",
    "omogočiti",
    "zagotoviti",
    "organizirati",
    "rešitev",
    "rešitve",
    "predlog"
]


# ============================================================
# 5. NORMALIZACIJA
# ============================================================

def normalize(text):

    if pd.isna(text):
        return ""

    text = str(text).lower().strip()

    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# 6. ZAZNAVANJE STRESNIH DEJAVNIKOV
# ============================================================

def detect_stress_factors(text):

    text = normalize(text)

    found = []

    for category, factors in CATEGORIES.items():

        for factor in factors:

            if factor in text:

                found.append(
                    (factor, category)
                )

    # isti dejavnik v istem odgovoru
    # šteje samo enkrat

    unique = []

    for item in found:

        if item not in unique:
            unique.append(item)

    return unique


# ============================================================
# 7. ZAZNAVANJE POZITIVNIH DEJAVNIKOV
# ============================================================

def detect_positive_factors(text):

    text = normalize(text)

    found = []

    for factor in POSITIVE_FACTORS:

        if factor in text:

            if factor not in found:
                found.append(factor)

    return found


# ============================================================
# 8. ZAZNAVANJE PREDLOGOV
# ============================================================

def detect_proposals(text):

    text = normalize(text)

    found = []

    # Najprej poiščemo stavke, v katerih je predlog
    sentences = re.split(
        r"(?<=[.!?;])\s+",
        text
    )

    for sentence in sentences:

        for pattern in PROPOSAL_PATTERNS:

            if pattern in sentence:

                sentence = sentence.strip()

                if sentence not in found:
                    found.append(sentence)

                break

    return found


# ============================================================
# 9. ANALIZA ENEGA ODGOVORA
# ============================================================

def analyze_answer(text):

    text = normalize(text)

    sf = detect_stress_factors(text)

    pf = detect_positive_factors(text)

    pr = detect_proposals(text)

    return {
        "SF": sf,
        "PF": pf,
        "PR": pr
    }


# ============================================================
# 10. IZRAČUN DENSITY
# ============================================================

def calculate_density(total_opinions, number_of_persons):

    if number_of_persons <= 0:
        return 0.0

    return total_opinions / number_of_persons


# ============================================================
# 11. IZRAČUN COMPLEXITY / VARIABILITY
# ============================================================

def calculate_complexity(total_opinions, diverse_opinions):

    if diverse_opinions <= 0:
        return 0.0

    return total_opinions / diverse_opinions


# ============================================================
# 12. REAL FACTOR Fo
#
# Fo = Co * rho_o / (Ct * rho_t)
#
# Ct = 1
# rho_t = 10
# ============================================================

def calculate_real_factor(
    complexity,
    density
):

    return (
        complexity * density
    ) / (
        THEORETICAL_COMPLEXITY *
        THEORETICAL_DENSITY
    )


# ============================================================
# 13. STRESNA MOČ
#
# σSF = arcsin sqrt(FSF * FPR / FPF)
#
# Python math.asin vrne radiane,
# zato rezultat pretvorimo v stopinje.
# ============================================================

def calculate_stress_power(
    F_SF,
    F_PF,
    F_PR
):

    if F_PF <= 0:

        return None

    ratio = (
        F_SF * F_PR
    ) / F_PF

    # Zaradi numerične varnosti
    ratio = max(
        0.0,
        min(1.0, ratio)
    )

    sigma_radians = math.asin(
        math.sqrt(ratio)
    )

    sigma_degrees = math.degrees(
        sigma_radians
    )

    return sigma_degrees


# ============================================================
# 14. GLAVNA AGREGACIJA
# ============================================================

def calculate_dataset(results):

    number_of_persons = len(results)

    # --------------------------------------------------------
    # SF
    # --------------------------------------------------------

    all_sf = []

    for result in results:

        all_sf.extend(
            result["SF"]
        )

    total_sf = len(all_sf)

    diverse_sf = len(
        set(all_sf)
    )

    rho_sf = calculate_density(
        total_sf,
        number_of_persons
    )

    C_sf = calculate_complexity(
        total_sf,
        diverse_sf
    )

    F_sf = calculate_real_factor(
        C_sf,
        rho_sf
    )

    # --------------------------------------------------------
    # PF
    # --------------------------------------------------------

    all_pf = []

    for result in results:

        all_pf.extend(
            result["PF"]
        )

    total_pf = len(all_pf)

    diverse_pf = len(
        set(all_pf)
    )

    rho_pf = calculate_density(
        total_pf,
        number_of_persons
    )

    C_pf = calculate_complexity(
        total_pf,
        diverse_pf
    )

    F_pf = calculate_real_factor(
        C_pf,
        rho_pf
    )

    # --------------------------------------------------------
    # PR
    # --------------------------------------------------------

    all_pr = []

    for result in results:

        all_pr.extend(
            result["PR"]
        )

    total_pr = len(all_pr)

    # Za predloge uporabimo normalizirano
    # besedilno vsebino predloga kot raznolikost.

    diverse_pr = len(
        set(all_pr)
    )

    rho_pr = calculate_density(
        total_pr,
        number_of_persons
    )

    C_pr = calculate_complexity(
        total_pr,
        diverse_pr
    )

    F_pr = calculate_real_factor(
        C_pr,
        rho_pr
    )

    # --------------------------------------------------------
    # KONČNA STRESNA MOČ
    # --------------------------------------------------------

    sigma = calculate_stress_power(
        F_sf,
        F_pf,
        F_pr
    )

    return {

        "N": number_of_persons,

        "total_sf": total_sf,
        "diverse_sf": diverse_sf,
        "rho_sf": rho_sf,
        "C_sf": C_sf,
        "F_sf": F_sf,

        "total_pf": total_pf,
        "diverse_pf": diverse_pf,
        "rho_pf": rho_pf,
        "C_pf": C_pf,
        "F_pf": F_pf,

        "total_pr": total_pr,
        "diverse_pr": diverse_pr,
        "rho_pr": rho_pr,
        "C_pr": C_pr,
        "F_pr": F_pr,

        "sigma": sigma
    }


# ============================================================
# 15. INTERPRETACIJA
# ============================================================

def interpret_stress(sigma):

    if sigma is None:
        return "Ni mogoče izračunati."

    if sigma < 15.05:
        return "Zelo nizka stresna moč"

    elif sigma < 30.05:
        return "Nizka stresna moč"

    elif sigma < 45.05:
        return "Srednja stresna moč"

    elif sigma < 60.05:
        return "Višja stresna moč"

    elif sigma < 75.05:
        return "Visoka stresna moč"

    else:
        return "Zelo visoka stresna moč"


# ============================================================
# 16. STREAMLIT
# ============================================================

def main():

    st.set_page_config(
        page_title="Petrič Stress Power",
        layout="wide"
    )

    st.title(
        "🧠 Petrič – izračun celokupne stresne moči"
    )

    st.markdown(
        """
        Ta različica izračunava **samo celokupno moč stresnih
        dejavnikov v stresnih stopinjah (°S)**.

        Celotni odgovori respondentov ostanejo nedotaknjeni.
        Znotraj posameznega odgovora sistem lahko zazna več
        stresnih dejavnikov, pozitivnih dejavnikov in predlogov.
        """
    )

    # ========================================================
    # UPLOAD
    # ========================================================

    uploaded_file = st.sidebar.file_uploader(
        "Naložite podatke",
        type=[
            "xlsx",
            "csv",
            "txt"
        ]
    )

    if uploaded_file is None:

        st.info(
            "Naložite .xlsx, .csv ali .txt datoteko."
        )

        return

    # ========================================================
    # BRANJE
    # ========================================================

    try:

        filename = uploaded_file.name.lower()

        if filename.endswith(".xlsx"):

            df = pd.read_excel(
                uploaded_file
            )

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

            df = pd.read_csv(
                uploaded_file
            )

    except Exception as e:

        st.error(
            f"Napaka pri branju datoteke: {e}"
        )

        return

    if df.empty:

        st.warning(
            "Datoteka je prazna."
        )

        return

    st.success(
        f"Naloženih odgovorov: {len(df)}"
    )

    # ========================================================
    # IZBIRA STOLPCA
    # ========================================================

    st.sidebar.markdown("---")

    st.sidebar.subheader(
        "Stolpec z odgovori"
    )

    column = st.sidebar.selectbox(
        "Izberite stolpec",
        df.columns.tolist()
    )

    # ========================================================
    # ANALIZA
    # ========================================================

    results = []

    for answer in df[column]:

        results.append(
            analyze_answer(answer)
        )

    # ========================================================
    # IZRAČUN
    # ========================================================

    calculation = calculate_dataset(
        results
    )

    # ========================================================
    # GLAVNI REZULTAT
    # ========================================================

    st.divider()

    st.header(
        "🔥 CELOKUPNA MOČ STRESNIH DEJAVNIKOV"
    )

    sigma = calculation["sigma"]

    if sigma is None:

        st.error(
            "Stresne moči ni mogoče izračunati, "
            "ker ni zaznanih pozitivnih dejavnikov."
        )

        return

    st.metric(
        "σSF – stresna moč",
        f"{sigma:.2f} °S"
    )

    st.progress(
        min(sigma / 90.0, 1.0)
    )

    st.subheader(
        interpret_stress(sigma)
    )

    # ========================================================
    # OPOZORILO GLEDE TVOJEGA EMPIRIČNEGA OBMOČJA
    # ========================================================

    if sigma < 30:

        st.warning(
            f"⚠️ Rezultat {sigma:.2f} °S je pod "
            "pričakovanim empiričnim območjem 30–39 °S."
        )

    elif sigma > 39:

        st.warning(
            f"⚠️ Rezultat {sigma:.2f} °S je nad "
            "pričakovanim empiričnim območjem 30–39 °S."
        )

    else:

        st.success(
            f"✅ Rezultat {sigma:.2f} °S je znotraj "
            "pričakovanega območja 30–39 °S."
        )

    # ========================================================
    # PODROBNOSTI IZRAČUNA
    # ========================================================

    with st.expander(
        "🧮 Prikaži znanstveni izračun"
    ):

        st.write(
            f"**Število respondentov N:** "
            f"{calculation['N']}"
        )

        st.markdown("### SF – stresni dejavniki")

        st.write(
            f"Skupno SF: "
            f"{calculation['total_sf']}"
        )

        st.write(
            f"Različni SF: "
            f"{calculation['diverse_sf']}"
        )

        st.write(
            f"ρSF = "
            f"{calculation['rho_sf']:.4f}"
        )

        st.write(
            f"CSF = "
            f"{calculation['C_sf']:.4f}"
        )

        st.write(
            f"FSF = "
            f"{calculation['F_sf']:.4f}"
        )

        st.markdown("### PF – pozitivni dejavniki")

        st.write(
            f"Skupno PF: "
            f"{calculation['total_pf']}"
        )

        st.write(
            f"Različni PF: "
            f"{calculation['diverse_pf']}"
        )

        st.write(
            f"ρPF = "
            f"{calculation['rho_pf']:.4f}"
        )

        st.write(
            f"CPF = "
            f"{calculation['C_pf']:.4f}"
        )

        st.write(
            f"FPF = "
            f"{calculation['F_pf']:.4f}"
        )

        st.markdown("### PR – predlogi")

        st.write(
            f"Skupno PR: "
            f"{calculation['total_pr']}"
        )

        st.write(
            f"Različni PR: "
            f"{calculation['diverse_pr']}"
        )

        st.write(
            f"ρPR = "
            f"{calculation['rho_pr']:.4f}"
        )

        st.write(
            f"CPR = "
            f"{calculation['C_pr']:.4f}"
        )

        st.write(
            f"FPR = "
            f"{calculation['F_pr']:.4f}"
        )

        st.markdown("---")

        st.write(
            "### Končna formula"
        )

        st.latex(
            r"""
            \sigma_{SF}
            =
            \arcsin
            \sqrt{
            \frac{
            F_{SF}\cdot F_{PR}
            }{
            F_{PF}
            }}
            """
        )

        st.write(
            f"**σSF = {sigma:.4f} °S**"
        )

    # ========================================================
    # PREGLED ZAZNANIH DEJAVNIKOV
    # ========================================================

    with st.expander(
        "🔎 Pregled zaznanih dejavnikov"
    ):

        rows = []

        for i, result in enumerate(results):

            sf = ", ".join(
                [
                    f"{factor} [{category}]"
                    for factor, category
                    in result["SF"]
                ]
            )

            pf = ", ".join(
                result["PF"]
            )

            pr = " | ".join(
                result["PR"]
            )

            rows.append({

                "Respondent":
                    i + 1,

                "Stresni dejavniki":
                    sf,

                "Pozitivni dejavniki":
                    pf,

                "Predlogi":
                    pr,

                "SF":
                    len(result["SF"]),

                "PF":
                    len(result["PF"]),

                "PR":
                    len(result["PR"])
            })

        result_df = pd.DataFrame(
            rows
        )

        st.dataframe(
            result_df,
            use_container_width=True,
            height=500
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()



