import pandas as pd
import requests
import re
import time

# ============================================================
# CONFIGURAZIONE
# ============================================================

INPUT = "/home/benedetta/Scaricati/progetto_cultura/luoghi_della_cultura.csv"

OUTPUT = "/home/benedetta/Scaricati/progetto_cultura/luoghi_arricchiti.csv"

SPARQL_ENDPOINT = "https://dati.cultura.gov.it/sparql"

# ============================================================
# LETTURA DEL CSV
# ============================================================

print("Lettura del CSV...")

df = pd.read_csv(INPUT)

print(f"Righe totali: {len(df)}")

# ============================================================
# ESTRAZIONE DEL CODICE DBUnico
# ============================================================

def estrai_dbunico(valore):

    if pd.isna(valore):
        return None

    match = re.search(r"DBUnico\.(\d+)", str(valore))

    if match:
        return match.group(1)

    return None


df["dbunico"] = df["identificativo"].apply(estrai_dbunico)

print(
    f"DBUnico trovati: "
    f"{df['dbunico'].notna().sum()} / {len(df)}"
)

# ============================================================
# SESSIONE HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "ProgettoCulturaFerrara/1.0"
})

# ============================================================
# FUNZIONE PER CERCARE IL NOME NEL DATASET MiC
# ============================================================

def cerca_nome_mic(dbunico):

    if not dbunico:
        return None

    query = f"""
    PREFIX cis: <http://dati.beniculturali.it/cis/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX l0: <https://w3id.org/italia/onto/l0/>

    SELECT ?nome ?nome_istituzionale
    WHERE {{
        ?luogo l0:identifier "DBUnico.{dbunico}" .

        OPTIONAL {{
            ?luogo rdfs:label ?nome .
        }}

        OPTIONAL {{
            ?luogo cis:institutionalCISName ?nome_istituzionale .
        }}
    }}
    LIMIT 1
    """

    try:

        response = session.get(
            SPARQL_ENDPOINT,
            params={
                "query": query,
                "format": "json"
            },
            headers={
                "Accept": "application/sparql-results+json"
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        risultati = data["results"]["bindings"]

        if not risultati:
            return None

        risultato = risultati[0]

        # Prima proviamo rdfs:label
        if "nome" in risultato:
            nome = risultato["nome"]["value"]

            if nome.strip():
                return nome.strip()

        # Se non disponibile, usiamo il nome istituzionale
        if "nome_istituzionale" in risultato:
            nome = risultato["nome_istituzionale"]["value"]

            if nome.strip():
                return nome.strip()

        return None

    except Exception as e:

        print(
            f"\nERRORE DBUnico {dbunico}: {e}"
        )

        return None


# ============================================================
# RECUPERO DEI NOMI
# ============================================================

print("\nInizio recupero dei nomi dal MiC...")
print("Potrebbe richiedere un po' di tempo.\n")

# Creiamo la colonna
df["nome_mic"] = None

# Cache:
# se lo stesso DBUnico compare più volte,
# non facciamo la stessa richiesta due volte.
cache = {}

totale = len(df)

for posizione, (index, row) in enumerate(df.iterrows(), start=1):

    dbunico = row["dbunico"]

    # Se manca DBUnico
    if pd.isna(dbunico) or dbunico is None:

        print(
            f"[{posizione}/{totale}] "
            f"DBUnico mancante"
        )

        continue

    dbunico = str(dbunico)

    # Controlliamo se lo abbiamo già cercato
    if dbunico in cache:

        nome = cache[dbunico]

    else:

        nome = cerca_nome_mic(dbunico)

        cache[dbunico] = nome

        # Pausa tra le richieste
        time.sleep(0.2)

    df.at[index, "nome_mic"] = nome

    if nome:

        print(
            f"[{posizione}/{totale}] "
            f"DBUnico.{dbunico} → {nome}"
        )

    else:

        print(
            f"[{posizione}/{totale}] "
            f"DBUnico.{dbunico} → NOME NON TROVATO"
        )


# ============================================================
# STATISTICHE
# ============================================================

nomi_trovati = df["nome_mic"].notna().sum()

print("\n" + "=" * 70)
print("RISULTATO")
print("=" * 70)

print(f"Righe totali:       {len(df)}")
print(f"Nomi trovati:       {nomi_trovati}")
print(f"Nomi non trovati:   {len(df) - nomi_trovati}")

if len(df) > 0:

    percentuale = (nomi_trovati / len(df)) * 100

    print(
        f"Percentuale:        {percentuale:.2f}%"
    )


# ============================================================
# SALVATAGGIO
# ============================================================

print("\nSalvataggio del file...")

df.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

print("\nOperazione completata!")
print(f"File salvato in:")
print(OUTPUT)