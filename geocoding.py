
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
# 2. CARICO IL FILE
# ============================================

# Se il file di output esiste già, lo utilizzo
# per riprendere il lavoro da dove era arrivato.

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
# 3. SESSIONE HTTP
# ============================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ProgettoCulturaFerrara/1.0"
})


# ============================================
# 4. CACHE
# ============================================

cache = {}


# ============================================
# 5. FUNZIONE DI GEOCODING
# ============================================

def reverse_geocode(lat, lon):

    key = (lat, lon)

    # Se abbiamo già cercato queste coordinate
    # restituiamo il risultato dalla cache
    if key in cache:
        return cache[key]

    url = "https://nominatim.openstreetmap.org/reverse"

    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "addressdetails": 1,
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
                print("⚠️ Nominatim ha restituito 429.")
                print("Troppe richieste. Aspetto 60 secondi...")
                print()

                time.sleep(60)

                continue


            response.raise_for_status()

            data = response.json()

            address = data.get("address", {})

            risultato = {
                "indirizzo_geocoded": data.get("display_name"),

                "via": address.get("road"),

                "numero_civico": address.get("house_number"),

                "cap_geocoded": address.get("postcode"),

                "comune_geocoded": (
                    address.get("city")
                    or address.get("town")
                    or address.get("village")
                    or address.get("municipality")
                ),

                "provincia_geocoded": address.get("county")
            }

            # Salvo nella cache
            cache[key] = risultato

            return risultato


        except requests.RequestException as e:

            print(
                f"Errore per {lat}, {lon}: {e}"
            )

            # Se non è l'ultimo tentativo
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
# 6. CICLO PRINCIPALE
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
        "Civico:",
        risultato["numero_civico"]
    )


    # ----------------------------------------
    # Rispetto il limite Nominatim
    # ----------------------------------------

    if not era_in_cache:

        time.sleep(2)


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
# 7. SALVATAGGIO FINALE
# ============================================

df.to_csv(
    FILE_OUTPUT,
    index=False,
    encoding="utf-8"
)


# ============================================
# 8. STATISTICHE
# ============================================

print()
print("============================================")
print("GEOCODING COMPLETATO")
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

