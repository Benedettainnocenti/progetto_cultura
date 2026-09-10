import pandas as pd
import requests
import time

# Leggi il CSV
df = pd.read_csv(
    "/home/benedetta/Scaricati/progetto_cultura/luoghi_della_cultura.csv"
)

# Colonne che aggiungeremo
df["nome_osm"] = ""
df["indirizzo_osm"] = ""

url = "https://nominatim.openstreetmap.org/reverse"

headers = {
    "User-Agent": "ProgettoCulturaFerrara/1.0"
}

for i, row in df.iterrows():

    lat = row["latitudine"]
    lon = row["longitudine"]

    # Salta le righe senza coordinate
    if pd.isna(lat) or pd.isna(lon):
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

        # Nome del luogo
        df.at[i, "nome_osm"] = data.get("name", "")

        # Indirizzo completo
        df.at[i, "indirizzo_osm"] = data.get("display_name", "")

        print(
            f"{i}: {lat}, {lon} → "
            f"{data.get('name', '')}"
        )

    except Exception as e:
        print(f"Errore alla riga {i}: {e}")

    # Importante: non bombardare l'API
    time.sleep(1)

# Salva il nuovo CSV
output = "/home/benedetta/Scaricati/progetto_cultura/luoghi_arricchiti.csv"

df.to_csv(output, index=False)

print("\nFinito!")
print(f"File salvato in: {output}")