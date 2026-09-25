import pandas as pd
import requests
import time
import os

# ============================================
# 1. FILE
# ============================================

FILE_INPUT = "/home/benedetta/Scaricati/progetto_cultura/luoghi_arricchiti.csv"

FILE_OUTPUT = "/home/benedetta/Scaricati/progetto_cultura/luoghi_geocodificati.csv"


# ============================================
# 2. TOKEN LOCATIONIQ
# ============================================

LOCATIONIQ_TOKEN = "pk.671134535a4fe21206bbff32d29f2bf1"


# ============================================
# 3. CARICO IL FILE
# ============================================

if os.path.exists(FILE_OUTPUT):

    print("File di output già esistente.")
    print("Riprendo il lavoro da dove era stato interrotto.")

    df = pd.read_csv(FILE_OUTPUT)

else:

    print("Creo un nuovo file di output.")

    df = pd.read_csv(FILE_INPUT)

    # Creo le nuove colonne
    df["indirizzo_geocoded"] = None
    df["via"] = None
    df["numero_civico"] = None
    df["cap_geocoded"] = None
    df["comune_geocoded"] = None
    df["provincia_geocoded"] = None


print(f"Righe totali: {len(df)}")


# ============================================
# 4. SESSIONE HTTP
# ============================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ProgettoCulturaFerrara/1.0"
})


# ============================================
# 5. CACHE
# ============================================

cache = {}


# ============================================
# 6. FUNZIONE DI GEOCODING
# ============================================

def reverse_geocode(lat, lon):

    key = (lat, lon)

    # Se abbiamo già cercato queste coordinate
    # restituiamo il risultato dalla cache

    if key in cache:

        return cache[key]


    # Endpoint europeo di LocationIQ

    url = "https://eu1.locationiq.com/v1/reverse"


    # Parametri della richiesta

    params = {

        "key": LOCATIONIQ_TOKEN,

        "lat": lat,

        "lon": lon,

        "format": "json",

        "addressdetails": 1,

        "normalizeaddress": 1,

        "zoom": 18,

        "accept-language": "it"
    }


    # Numero massimo di tentativi

    max_tentativi = 3


    for tentativo in range(max_tentativi):

        try:

            response = session.get(
                url,
                params=params,
                timeout=15
            )


            # ------------------------------------
            # RATE LIMIT
            # ------------------------------------

            if response.status_code == 429:

                print()
                print("⚠️ LocationIQ ha restituito 429.")
                print("Limite di richieste raggiunto.")
                print("Aspetto 60 secondi...")
                print()

                time.sleep(60)

                continue


            # ------------------------------------
            # ALTRI ERRORI HTTP
            # ------------------------------------

            response.raise_for_status()


            # ------------------------------------
            # JSON
            # ------------------------------------

            data = response.json()


            # ------------------------------------
            # DATI DELL'INDIRIZZO
            # ------------------------------------

            address = data.get("address", {})


            # ------------------------------------
            # RISULTATO
            # ------------------------------------

            risultato = {

                "indirizzo_geocoded":
                    data.get("display_name"),

                "via":
                    address.get("road"),

                "numero_civico":
                    address.get("house_number"),

                "cap_geocoded":
                    address.get("postcode"),

                "comune_geocoded":
                    (
                        address.get("city")
                        or
                        address.get("town")
                        or
                        address.get("village")
                        or
                        address.get("municipality")
                    ),

                "provincia_geocoded":
                    (
                        address.get("county")
                        or
                        address.get("state")
                    )
            }


            # ------------------------------------
            # SALVO NELLA CACHE
            # ------------------------------------

            cache[key] = risultato


            return risultato


        # ========================================
        # ERRORI DI CONNESSIONE
        # ========================================

        except requests.RequestException as e:

            print(
                f"Errore per {lat}, {lon}: {e}"
            )


            if tentativo < max_tentativi - 1:

                print("Riprovo tra 10 secondi...")

                time.sleep(10)

            else:

                print("Salto questa coordinata.")


                return {

                    "indirizzo_geocoded": None,

                    "via": None,

                    "numero_civico": None,

                    "cap_geocoded": None,

                    "comune_geocoded": None,

                    "provincia_geocoded": None
                }


# ============================================
# 7. CICLO PRINCIPALE
# ============================================

for i, row in df.iterrows():

    lat = row["latitudine"]

    lon = row["longitudine"]


    # ----------------------------------------
    # Coordinate mancanti
    # ----------------------------------------

    if pd.isna(lat) or pd.isna(lon):

        print(
            f"[{i + 1}/{len(df)}] "
            "Coordinate mancanti"
        )

        continue


    # ----------------------------------------
    # Controllo se già elaborato
    # ----------------------------------------

    if pd.notna(row["indirizzo_geocoded"]):

        print(
            f"[{i + 1}/{len(df)}] "
            "Già elaborato → salto"
        )

        continue


    print()

    print(
        f"[{i + 1}/{len(df)}] "
        f"DBUnico: {row['dbunico']}"
    )

    print(
        f"Coordinate: {lat}, {lon}"
    )


    # ----------------------------------------
    # Chiamata API
    # ----------------------------------------

    era_in_cache = (lat, lon) in cache

    risultato = reverse_geocode(lat, lon)


    # ----------------------------------------
    # Salvo i risultati
    # ----------------------------------------

    for colonna, valore in risultato.items():

        df.at[i, colonna] = valore


    print(
        "Indirizzo:",
        risultato["indirizzo_geocoded"]
    )

    print(
        "Via:",
        risultato["via"]
    )

    print(
        "Civico:",
        risultato["numero_civico"]
    )

    print(
        "CAP:",
        risultato["cap_geocoded"]
    )

    print(
        "Comune:",
        risultato["comune_geocoded"]
    )

    print(
        "Provincia:",
        risultato["provincia_geocoded"]
    )


    # ----------------------------------------
    # Pausa tra le richieste
    # ----------------------------------------

    if not era_in_cache:

        time.sleep(1)


    # ----------------------------------------
    # Salvataggio ogni 50 righe
    # ----------------------------------------

    if (i + 1) % 50 == 0:

        df.to_csv(
            FILE_OUTPUT,
            index=False,
            encoding="utf-8"
        )

        print()
        print("💾 Progresso salvato.")
        print()


# ============================================
# 8. SALVATAGGIO FINALE
# ============================================

df.to_csv(
    FILE_OUTPUT,
    index=False,
    encoding="utf-8"
)


# ============================================
# 9. STATISTICHE
# ============================================

print()

print("============================================")
print("GEOCODING LOCATIONIQ COMPLETATO")
print("============================================")

print(
    f"File creato: {FILE_OUTPUT}"
)

print()

print(
    "Indirizzi recuperati:",
    df["indirizzo_geocoded"].notna().sum()
)

print(
    "Civici recuperati:",
    df["numero_civico"].notna().sum()
)

print(
    "CAP recuperati:",
    df["cap_geocoded"].notna().sum()
)

print(
    "Comuni recuperati:",
    df["comune_geocoded"].notna().sum()
)

print(
    "Province recuperate:",
    df["provincia_geocoded"].notna().sum()
)
print(f"DEBUG: lat={lat}, lon={lon}")
print(f"URL: {url}")