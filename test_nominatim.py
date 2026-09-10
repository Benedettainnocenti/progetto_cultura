import pandas as pd
import requests
import time

# Leggi il CSV
df = pd.read_csv("luoghi_della_cultura.csv")

# Prendiamo solo le prime 10 righe
test = df.head(10).copy()

url = "https://nominatim.openstreetmap.org/reverse"

headers = {
    "User-Agent": "ProgettoCulturaFerrara/1.0"
}

for index, row in test.iterrows():

    lat = row["latitudine"]
    lon = row["longitudine"]

    if pd.isna(lat) or pd.isna(lon):
        print(f"\nRiga {index}: coordinate mancanti")
        continue

    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "addressdetails": 1,
        "namedetails": 1,
        "accept-language": "it"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        data = response.json()

        print("\n" + "=" * 60)
        print(f"RIGA: {index}")
        print(f"Coordinate: {lat}, {lon}")
        print(f"Nome originale: {row['nome']}")
        print(f"Tipologia: {row['tipologia']}")
        print(f"Nome trovato: {data.get('name', '')}")
        print(f"Indirizzo trovato: {data.get('display_name', '')}")

        # Mostriamo anche i dettagli dell'indirizzo
        address = data.get("address", {})

        print(f"Comune: {address.get('city', address.get('town', address.get('village', '')))}")
        print(f"Provincia: {address.get('county', '')}")
        print(f"Regione: {address.get('state', '')}")

    except Exception as e:
        print(f"Errore alla riga {index}: {e}")

    # Nominatim richiede di non superare 1 richiesta al secondo
    time.sleep(1)