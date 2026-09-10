
import json
import pandas as pd


# ============================================================
# CONFIGURAZIONE
# ============================================================

INPUT_FILE = "dataset-eventiMeseCorrente.json"
OUTPUT_FILE = "eventi_mese_corrente.csv"


# ============================================================
# 1. CARICAMENTO JSON-LD
# ============================================================

print("Caricamento del JSON-LD...")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

records = data.get("@graph", [])

print(f"Record nel grafo: {len(records):,}")


# ============================================================
# 2. NORMALIZZAZIONE
# ============================================================

df = pd.json_normalize(records)

print(f"DataFrame iniziale: {df.shape[0]:,} righe x {df.shape[1]} colonne")


# ============================================================
# 3. FUNZIONI DI SUPPORTO
# ============================================================

def get_value(value):
    """
    Estrae il valore da una proprietà JSON-LD.

    Gestisce:
    - stringhe
    - {"@value": "..."}
    - {"@id": "..."}
    - liste
    """

    if value is None:
        return None

    if isinstance(value, float) and pd.isna(value):
        return None

    if isinstance(value, dict):
        return value.get("@value") or value.get("@id")

    if isinstance(value, list):

        if len(value) == 0:
            return None

        values = []

        for item in value:

            if isinstance(item, dict):
                value_item = (
                    item.get("@value")
                    or item.get("@id")
                )
            else:
                value_item = item

            if value_item is not None:
                values.append(str(value_item))

        if len(values) == 0:
            return None

        # Se ci sono più valori, li manteniamo
        # separati da " | "
        return " | ".join(values)

    return value


def has_type(value, target):
    """
    Controlla se @type contiene un determinato tipo.
    """

    if isinstance(value, list):
        return target in value

    return value == target


def find_column(dataframe, possible_names):
    """
    Cerca la prima colonna disponibile tra quelle indicate.
    """

    for name in possible_names:

        if name in dataframe.columns:
            return name

    return None


# ============================================================
# 4. ESPLORIAMO I TIPI PRESENTI
# ============================================================

print("\nTipi di entità presenti nel dataset:")

types = df["@type"].apply(get_value)

print(
    types.value_counts().head(30)
)


# ============================================================
# 5. IDENTIFICHIAMO GLI INDIRIZZI
# ============================================================

print("\nEstrazione degli indirizzi...")

addresses = df[
    df["@type"].apply(
        lambda x: has_type(
            x,
            "clvapit:Address"
        )
    )
].copy()

print(f"Indirizzi trovati: {len(addresses):,}")


# ============================================================
# 6. TABELLA DEGLI INDIRIZZI
# ============================================================

addresses_clean = pd.DataFrame()

addresses_clean["address_id"] = (
    addresses["@id"]
)

addresses_clean["indirizzo"] = (
    addresses["clvapit:fullAddress"]
    .apply(get_value)
    if "clvapit:fullAddress" in addresses.columns
    else None
)

addresses_clean["cap"] = (
    addresses["clvapit:postCode"]
    .apply(get_value)
    if "clvapit:postCode" in addresses.columns
    else None
)

addresses_clean["comune_id"] = (
    addresses["clvapit:hasCity.@id"]
    .apply(get_value)
    if "clvapit:hasCity.@id" in addresses.columns
    else None
)

addresses_clean["provincia_id"] = (
    addresses["clvapit:hasProvince.@id"]
    .apply(get_value)
    if "clvapit:hasProvince.@id" in addresses.columns
    else None
)

addresses_clean["regione_id"] = (
    addresses["clvapit:hasRegion.@id"]
    .apply(get_value)
    if "clvapit:hasRegion.@id" in addresses.columns
    else None
)


# ============================================================
# 7. ESTRAIAMO I NOMI DI COMUNE, PROVINCIA E REGIONE
# ============================================================

def extract_last_id_part(value):

    if pd.isna(value):
        return None

    value = str(value)

    if "/" in value:
        return value.rstrip("/").split("/")[-1]

    return value


addresses_clean["comune"] = (
    addresses_clean["comune_id"]
    .apply(extract_last_id_part)
)

addresses_clean["provincia"] = (
    addresses_clean["provincia_id"]
    .apply(extract_last_id_part)
)

addresses_clean["regione"] = (
    addresses_clean["regione_id"]
    .apply(extract_last_id_part)
)


# ============================================================
# 8. IDENTIFICHIAMO I POSSIBILI EVENTI
# ============================================================

print("\nRicerca delle entità evento...")


# Cerchiamo i tipi che contengono parole riconducibili
# agli eventi.

event_type_candidates = []

for value in df["@type"]:

    if isinstance(value, list):
        values = value
    else:
        values = [value]

    for item in values:

        if item is None:
            continue

        item_string = str(item).lower()

        if (
            "event" in item_string
            or "event" in item_string
            or "manifestation" in item_string
        ):
            event_type_candidates.append(item)


event_type_candidates = sorted(
    set(event_type_candidates)
)

print("Possibili tipi evento:")

for item in event_type_candidates:
    print(" -", item)


# ============================================================
# 9. SELEZIONE DEGLI EVENTI
# ============================================================

if event_type_candidates:

    events = df[
        df["@type"].apply(
            lambda x: any(
                has_type(x, event_type)
                for event_type in event_type_candidates
            )
        )
    ].copy()

else:

    print(
        "\nATTENZIONE: non è stato identificato "
        "automaticamente il tipo degli eventi."
    )

    events = pd.DataFrame()


print(
    f"\nEventi identificati: {len(events):,}"
)


# ============================================================
# 10. MOSTRIAMO LE COLONNE DEGLI EVENTI
# ============================================================

if not events.empty:

    print("\nColonne disponibili negli eventi:")

    for column in events.columns:
        print(" -", column)


# ============================================================
# 11. CREIAMO LA TABELLA EVENTI
# ============================================================

if not events.empty:

    output = pd.DataFrame()

    output["id"] = events["@id"]

    # --------------------------------------------------------
    # TITOLO / NOME
    # --------------------------------------------------------

    title_column = find_column(
        events,
        [
            "l0:name.@value",
            "rdfs:label.@value",
            "cis:institutionalCISName.@value",
            "l0:name",
            "rdfs:label"
        ]
    )

    if title_column:

        output["titolo"] = (
            events[title_column]
            .apply(get_value)
        )

    else:

        output["titolo"] = None


    # --------------------------------------------------------
    # DESCRIZIONE
    # --------------------------------------------------------

    description_column = find_column(
        events,
        [
            "l0:description.@value",
            "rdfs:comment.@value",
            "l0:description",
            "rdfs:comment"
        ]
    )

    if description_column:

        output["descrizione"] = (
            events[description_column]
            .apply(get_value)
        )

    else:

        output["descrizione"] = None


    # --------------------------------------------------------
    # TIPOLOGIA
    # --------------------------------------------------------

    type_column = find_column(
        events,
        [
            "dc:type",
            "event:type",
            "schema:eventType"
        ]
    )

    if type_column:

        output["tipologia"] = (
            events[type_column]
            .apply(get_value)
        )

    else:

        output["tipologia"] = None


    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    date_columns = [
        column
        for column in events.columns
        if any(
            keyword in column.lower()
            for keyword in [
                "date",
                "start",
                "end",
                "begin",
                "finish",
                "time"
            ]
        )
    ]

    print("\nPossibili colonne temporali:")

    for column in date_columns:
        print(" -", column)


    # Proviamo a identificare inizio e fine
    start_column = find_column(
        events,
        [
            "schema:startDate",
            "event:startDate",
            "dcterms:startDate",
            "startDate",
            "schema:validFrom"
        ]
    )

    end_column = find_column(
        events,
        [
            "schema:endDate",
            "event:endDate",
            "dcterms:endDate",
            "endDate",
            "schema:validThrough"
        ]
    )

    if start_column:

        output["data_inizio"] = (
            events[start_column]
            .apply(get_value)
        )

    else:

        output["data_inizio"] = None


    if end_column:

        output["data_fine"] = (
            events[end_column]
            .apply(get_value)
        )

    else:

        output["data_fine"] = None


    # --------------------------------------------------------
    # INDIRIZZO ASSOCIATO
    # --------------------------------------------------------

    address_column = find_column(
        events,
        [
            "clvapit:hasAddress.@id",
            "schema:address.@id",
            "cis:siteAddress.@id",
            "hasAddress.@id",
            "address.@id"
        ]
    )

    if address_column:

        output["address_id"] = (
            events[address_column]
            .apply(get_value)
        )

    else:

        output["address_id"] = None


    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    url_column = find_column(
        events,
        [
            "smapit:URL",
            "schema:url",
            "foaf:homepage",
            "schema:website"
        ]
    )

    if url_column:

        output["url"] = (
            events[url_column]
            .apply(get_value)
        )

    else:

        output["url"] = None


    # --------------------------------------------------------
    # IMMAGINE
    # --------------------------------------------------------

    image_column = find_column(
        events,
        [
            "foaf:depiction.@id",
            "schema:image",
            "foaf:depiction"
        ]
    )

    if image_column:

        output["immagine"] = (
            events[image_column]
            .apply(get_value)
        )

    else:

        output["immagine"] = None


    # ========================================================
    # 12. JOIN CON GLI INDIRIZZI
    # ========================================================

    output = output.merge(
        addresses_clean[
            [
                "address_id",
                "indirizzo",
                "cap",
                "comune",
                "provincia",
                "regione"
            ]
        ],
        on="address_id",
        how="left"
    )


    # ========================================================
    # 13. PULIZIA DELLE DATE
    # ========================================================

    for column in [
        "data_inizio",
        "data_fine"
    ]:

        if column in output.columns:

            output[column] = pd.to_datetime(
                output[column],
                errors="coerce"
            )


    # ========================================================
    # 14. PULIZIA DEL TESTO
    # ========================================================

    for column in output.select_dtypes(
        include=["object", "string"]
    ).columns:

        output[column] = (
            output[column]
            .astype("string")
            .str.strip()
        )


    # ========================================================
    # 15. ELIMINIAMO L'ID TECNICO
    # ========================================================

    output = output.drop(
        columns=["address_id"],
        errors="ignore"
    )


    # ========================================================
    # 16. ORDINE DELLE COLONNE
    # ========================================================

    desired_columns = [
        "id",
        "titolo",
        "tipologia",
        "descrizione",
        "data_inizio",
        "data_fine",
        "indirizzo",
        "comune",
        "provincia",
        "regione",
        "cap",
        "url",
        "immagine"
    ]

    desired_columns = [
        column
        for column in desired_columns
        if column in output.columns
    ]

    output = output[desired_columns]


    # ========================================================
    # 17. RIMOZIONE DUPLICATI
    # ========================================================

    before = len(output)

    output = output.drop_duplicates(
        subset="id"
    )

    after = len(output)

    print(
        f"\nDuplicati rimossi: {before - after:,}"
    )


    # ========================================================
    # 18. ESPORTAZIONE CSV
    # ========================================================

    output.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )


    # ========================================================
    # 19. CONTROLLO QUALITÀ
    # ========================================================

    print("\n" + "=" * 60)
    print("CSV CREATO")
    print("=" * 60)

    print(f"File: {OUTPUT_FILE}")
    print(f"Righe: {len(output):,}")
    print(f"Colonne: {len(output.columns)}")

    print("\nColonne finali:")

    print(
        output.columns.tolist()
    )

    print("\nValori mancanti:")

    print(
        output.isna()
        .sum()
        .sort_values(ascending=False)
    )

    print("\nPrime 10 righe:")

    print(
        output.head(10).to_string()
    )


else:

    print("\n" + "=" * 60)
    print("IL DATASET NON È STATO CONVERTITO")
    print("=" * 60)

    print(
        """
Il tipo dell'entità evento non è stato identificato
automaticamente.
        """
    )

