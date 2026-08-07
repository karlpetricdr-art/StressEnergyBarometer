import streamlit as st
import pandas as pd
import re
import math
from collections import Counter

# --- 1. STOP-WORDS (MAŠILA) ---
SLO_STOPWORDS = {
    "se", "oh", "na", "potem", "in", "ter", "bi", "da", "pa", "že", "tudi", "iz", "za",
    "še", "samo", "tako", "kot", "sem", "smo", "ste", "so", "je", "bil", "bila", "bilo",
    "biti", "ali", "v", "pri", "o", "z", "s", "k", "h", "vse", "vsi", "tisti", "nekaj",
    "včasih", "ker", "ne", "me", "ti", "mi", "on", "ona", "kar", "kje", "ko", "če", "ni"
}

# --- 2. ZNANSTVENE KATEGORIJE (6 ENOT) ---
# Ključne besede so korenski deli (stems) - ujemanje je na začetek besede, ne poljuben podniz
CATEGORIES_MAP = {
    "Attentive (physical) unit": ["hrup", "svetlob", "vreme", "pisarn", "tišin", "mraz",
                                   "vročin", "noise", "light"],
    "Performance unit": ["rok", "obremenit", "nalog", "birokraci", "informacij", "napor",
                          "deadline", "workload", "preobremen"],
    "Individual Psychological unit": ["strah", "stres", "mir", "samozavest", "tesnob",
                                       "skrb", "anxiety", "fear", "izgorel"],
    "Partial social unit": ["plač", "denar", "financ", "nagrad", "priznanj", "krivic",
                             "standard", "money", "salary"],
    "Social unit": ["odnos", "mobing", "sodelav", "družin", "komunikacij", "prepir",
                     "konflikt", "mobbing", "family"],
    "Health biological unit": ["zdravj", "šport", "prehran", "spanj", "joga", "bolezen",
                                "utrujen", "health", "illness"]
}

# --- 3. FUNKCIJE ZA OBDELAVO BESEDILA ---

def match_category(word: str):
    """Vrne ime kategorije, če se beseda ujema s korenom katere od ključnih besed,
    sicer None. Ujemanje je na začetek besede (stemming), ne poljuben podniz,
    da se izognemo lažnim zadetkom (npr. 'čas' znotraj naključne besede)."""
    for cat, keywords in CATEGORIES_MAP.items():
        for kw in keywords:
            if word == kw or word.startswith(kw):
                return cat
    return None


def get_fo_fr(series: pd.Series):
    """
    fo = vsa najdena mnenja (vse besede, ki ustrezajo kategorijam)
    fr = različna mnenja (unikatne besede, ki ustrezajo kategorijam)
    """
    all_matched_words = []

    for row in series.dropna():
        text = str(row).lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = [w for w in text.split() if w not in SLO_STOPWORDS and len(w) > 2]

        for word in words:
            if match_category(word):
                all_matched_words.append(word)

    fo = len(all_matched_words)
    fr = len(set(all_matched_words))

    return fo, fr, Counter(all_matched_words)


def calculate_fo_real(fo, fr, n, rho_t, c_t):
    """Realni faktor Fo. Numerično robusten - ne vrača umetno napihnjenih
    vrednosti, kadar ni zadetkov, ampak realno 0."""
    if n == 0 or fr == 0 or fo == 0:
        return 0.0
    rho_o = fo / n
    c_o = fo / fr
    if rho_t == 0 or c_t == 0:
        return 0.0
    return (c_o * rho_o) / (c_t * rho_t)


def calculate_sigma_degrees(F_sf, F_pf, F_pr):
    """Vrne (sigma_deg, opozorilo). Opozorilo ni None, če je izračun
    numerično nezanesljiv (npr. F_pf ~ 0), da uporabnik ve, da rezultatu
    ni mogoče zaupati, namesto da se vrednost tiho pope na 90 stopinj."""
    if F_pf <= 0:
        return None, ("F_pf (realni faktor pozitivnih dejavnikov) je 0 - v besedilu "
                       "ni bilo zaznanih pozitivnih ključnih besed, zato sigma ni "
                       "izračunljiva. Preverite stolpec s pozitivnimi dejavniki in/ali "
                       "razširite nabor ključnih besed.")

    under_root = (F_sf * F_pr) / F_pf
    sqrt_val = math.sqrt(under_root)

    if sqrt_val > 1.0:
        return None, (f"Razmerje (F_sf * F_pr) / F_pf = {under_root:.4f} je izven "
                       "domene arcsin (koren > 1). To po navadi pomeni, da so "
                       "stresni/predlogni dejavniki relativno preveč pogosti glede na "
                       "pozitivne, ali da so konstanti rho_t / c_t neustrezno umerjeni "
                       "na vaš vzorec. Rezultat ni prikazan, da se izognemo napačnemu "
                       "prirejanju na 90°.")

    sigma_rad = math.asin(sqrt_val)
    sigma_deg = math.degrees(sigma_rad)
    return sigma_deg, None


# --- 4. STREAMLIT APLIKACIJA ---

def main():
    st.set_page_config(page_title="Petrič Stress Power Index", layout="wide")
    st.title("📊 Izračun stresne moči po Petričevi metodi (2025)")

    st.sidebar.header("Umerjanje konstant")
    st.sidebar.caption(
        "rho_t in c_t sta teoretični (referenčni) konstanti, na katere se "
        "primerja dejanski vzorec. Privzeti vrednosti 10 in 1 sta izhodišče - "
        "če želite, da metoda na vašem referenčnem/normativnem vzorcu dosledno "
        "vrača pričakovani razpon (npr. 30-39 °S), ju umerite tukaj na podlagi "
        "znane referenčne baze, namesto da rezultat naknadno umetno omejujete."
    )
    rho_t = st.sidebar.number_input("rho_t (teoretična gostota)", value=10.0, min_value=0.01)
    c_t = st.sidebar.number_input("c_t (teoretična kompleksnost)", value=1.0, min_value=0.01)

    uploaded_file = st.sidebar.file_uploader("Naložite datoteko (.txt ali .csv)", type=['txt', 'csv'])

    if uploaded_file:
        sep = '\t' if uploaded_file.name.endswith('.txt') else ','
        df = pd.read_csv(uploaded_file, sep=sep)

        if len(df.columns) >= 3:
            col_pf = df.columns[0]  # Pozitivni
            col_sf = df.columns[1]  # Stresni
            col_pr = df.columns[2]  # Predlogi

            N_o = len(df)
            if N_o == 0:
                st.error("Datoteka ne vsebuje nobenih vrstic.")
                return

            # --- NIVO 1: fo in fr ---
            fo_pf, fr_pf, _ = get_fo_fr(df[col_pf])
            fo_sf, fr_sf, _ = get_fo_fr(df[col_sf])
            fo_pr, fr_pr, _ = get_fo_fr(df[col_pr])

            # --- NIVO 2: Realni faktorji Fo ---
            F_pf = calculate_fo_real(fo_pf, fr_pf, N_o, rho_t, c_t)
            F_sf = calculate_fo_real(fo_sf, fr_sf, N_o, rho_t, c_t)
            F_pr = calculate_fo_real(fo_pr, fr_pr, N_o, rho_t, c_t)

            # --- NIVO 3: Končni izračun stopinj ---
            sigma_deg, warning = calculate_sigma_degrees(F_sf, F_pf, F_pr)

            # --- PRIKAZ REZULTATOV ---
            st.header("Končni znanstveni izračun")

            if warning:
                st.error(warning)
            else:
                res_c1, res_c2 = st.columns(2)
                with res_c1:
                    st.metric("CELOKUPNA STRESNA MOČ", f"{sigma_deg:.2f} °S")
                    if 30.0 <= sigma_deg <= 39.0:
                        st.success("Rezultat je v pričakovanem znanstvenem razponu (30-39 °S).")
                    else:
                        st.warning(
                            "Rezultat je izven razpona 30-39 °S. To ni napačno samo po sebi - "
                            "lahko pomeni, da je vzorec dejansko bolj/manj obremenjen kot "
                            "referenca, ali da rho_t/c_t nista umerjena na vašo populacijo. "
                            "Preverite bazo ključnih besed in konstanti v stranski vrstici."
                        )

                with res_c2:
                    st.write("Psihosocialni barometer")
                    st.progress(min(max(sigma_deg / 90, 0.0), 1.0))

            # Tabela s parametri po Petriču
            st.divider()
            st.subheader("Podrobna tabela parametrov")

            data = {
                "Kategorija": ["Stresni dejavniki (SF)", "Pozitivni dejavniki (PF)", "Predlogi (PR)"],
                "fo (vsa mnenja)": [fo_sf, fo_pf, fo_pr],
                "fr (različna)": [fr_sf, fr_pf, fr_pr],
                "rho_o (Gostota)": [
                    round(fo_sf / N_o, 3), round(fo_pf / N_o, 3), round(fo_pr / N_o, 3)
                ],
                "Co (Kompleksnost)": [
                    round(fo_sf / fr_sf, 3) if fr_sf > 0 else 0,
                    round(fo_pf / fr_pf, 3) if fr_pf > 0 else 0,
                    round(fo_pr / fr_pr, 3) if fr_pr > 0 else 0,
                ],
                "Fo (Realni faktor)": [round(F_sf, 4), round(F_pf, 4), round(F_pr, 4)],
            }
            st.table(pd.DataFrame(data))

            # Izpis po nivojih za kontrolo
            with st.expander("Poglej matematični postopek (Nivoji)"):
                st.write(f"**Nivo 1:** Identificiranih {fo_sf + fo_pf + fo_pr} relevantnih enot pri {N_o} respondentih.")
                st.write(f"**Nivo 2:** Izračunani realni faktorji: SF={F_sf:.4f}, PF={F_pf:.4f}, PR={F_pr:.4f}")
                if not warning:
                    st.latex(
                        r"\sigma = \arcsin\sqrt{\frac{" + f"{F_sf:.4f} \\cdot {F_pr:.4f}"
                        + r"}{" + f"{F_pf:.4f}" + r"}} = " + f"{sigma_deg:.2f}^\\circ"
                    )
                else:
                    st.write("Formula ni bila izračunana zaradi zgoraj navedene numerične napake.")

        else:
            st.error("Napačna struktura datoteke. Potrebni so 3 stolpci.")
    else:
        st.info("Naložite datoteko za izračun.")


if __name__ == "__main__":
    main()



