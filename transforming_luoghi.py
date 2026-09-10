import json
import pandas as pd


# ============================================================
# CONFIGURAZIONE
# ============================================================

INPUT_FILE = "dataset-luoghi.json"
OUTPUT_FILE = "luoghi_della_cultura.csv"


# ============================================================
# 1. CARICAMENTO JSON-LD
# ============================================================

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

records = data["@graph"]

print(f"Record nel JSON-LD: {len(records):,}")


# ============================================================
# 2. NORMALIZZAZIONE
# ============================================================

df = pd.json_normalize(records)

print(f"DataFrame originale: {df.shape}")


# ============================================================
# 3. FUNZIONI DI SUPPORTO
# ============================================================

def get_value(value):
    """
    Estrae un valore da strutture JSON-LD come:
    {"@value": "..."}
    {"@id": "..."}
    oppure liste di queste strutture.
    """

    if isinstance(value, dict):
        return value.get("@value") or value.get("@id")

    if isinstance(value, list):
        if len(value) == 0:
            return None

        first = value[0]

        if isinstance(first, dict):
            return first.get("@value") or first.get("@id")

        return first

    return value


def has_type(value, target):
    """
    Controlla il tipo dell'entità.
    """

    if isinstance(value, list):
        return target in value

    return value == target


# ============================================================
# 4. SELEZIONIAMO I LUOGHI CULTURALI
# ============================================================

luoghi = df[
    df["@type"].apply(
        lambda x: has_type(
            x,
            "cis:CulturalInstituteOrSite"
        )
    )
].copy()

print(f"Luoghi culturali: {len(luoghi):,}")


# ============================================================
# 5. CREIAMO LA TABELLA PRINCIPALE
# ============================================================

output = pd.DataFrame()

output["id"] = luoghi["@id"]

output["tipologia"] = (
    luoghi["dc:type"]
    .apply(get_value)
)

output["descrizione"] = (
    luoghi["l0:description.@value"]
    .apply(get_value)
)

output["identificativo"] = (
    luoghi["l0:identifier"]
    .apply(get_value)
)

output["latitudine"] = (
    luoghi["geo:lat"]
    .apply(get_value)
)

output["longitudine"] = (
    luoghi["geo:long"]
    .apply(get_value)
)

output["immagine"] = (
    luoghi["foaf:depiction.@id"]
    .apply(get_value)
)


# ============================================================
# 6. RECUPERIAMO I NOMI
# ============================================================

names = df[
    df["@type"].apply(
        lambda x: has_type(
            x,
            "cis:CISNameInTime"
        )
    )
].copy()

names_clean = pd.DataFrame()

names_clean["name_id"] = names["@id"]

if "l0:name.@value" in names.columns:

    names_clean["nome"] = (
        names["l0:name.@value"]
        .apply(get_value)
    )

elif "rdfs:label.@value" in names.columns:

    names_clean["nome"] = (
        names["rdfs:label.@value"]
        .apply(get_value)
    )

else:

    names_clean["nome"] = None


names_clean = names_clean.drop_duplicates(
    subset="name_id"
)


# ID del nome associato al luogo
output["name_id"] = (
    luoghi["cis:hasCISNameInTime.@id"]
    .apply(get_value)
)


# Join con i nomi
output = output.merge(
    names_clean,
    on="name_id",
    how="left"
)


# ============================================================
# 7. RECUPERIAMO LE SEDI
# ============================================================

sites = df[
    df["@type"].apply(
        lambda x: has_type(
            x,
            "cis:Site"
        )
    )
].copy()

sites_clean = pd.DataFrame()

sites_clean["site_id"] = sites["@id"]

sites_clean["address_id"] = (
    sites["cis:siteAddress.@id"]
    .apply(get_value)
)


sites_clean = sites_clean.drop_duplicates(
    subset="site_id"
)


# ID della sede associata al luogo
output["site_id"] = (
    luoghi["cis:hasSite.@id"]
    .apply(get_value)
)


# Join con le sedi
output = output.merge(
    sites_clean,
    on="site_id",
    how="left"
)


# ============================================================
# 8. RECUPERIAMO GLI INDIRIZZI
# ============================================================

addresses = df[
    df["@type"].apply(
        lambda x: has_type(
            x,
            "clvapit:Address"
        )
    )
].copy()

addresses_clean = pd.DataFrame()

addresses_clean["address_id"] = addresses["@id"]

addresses_clean["indirizzo"] = (
    addresses["clvapit:fullAddress"]
    .apply(get_value)
)

addresses_clean["cap"] = (
    addresses["clvapit:postCode"]
    .apply(get_value)
)

addresses_clean["comune_id"] = (
    addresses["clvapit:hasCity.@id"]
    .apply(get_value)
)

addresses_clean["provincia_id"] = (
    addresses["clvapit:hasProvince.@id"]
    .apply(get_value)
)

addresses_clean["regione_id"] = (
    addresses["clvapit:hasRegion.@id"]
    .apply(get_value)
)


addresses_clean = addresses_clean.drop_duplicates(
    subset="address_id"
)


# Join con gli indirizzi
output = output.merge(
    addresses_clean,
    on="address_id",
    how="left"
)


# ============================================================
# 9. RECUPERIAMO LE COORDINATE DALLE GEOMETRIE
# ============================================================

geometries = df[
    df["@type"].apply(
        lambda x: has_type(
            x,
            "clvapit:Geometry"
        )
    )
].copy()


geometry_clean = pd.DataFrame()

geometry_clean["geometry_id"] = geometries["@id"]

if "clvapit:lat" in geometries.columns:

    geometry_clean["lat_geometry"] = (
        geometries["clvapit:lat"]
        .apply(get_value)
    )

else:

    geometry_clean["lat_geometry"] = None


if "clvapit:long" in geometries.columns:

    geometry_clean["long_geometry"] = (
        geometries["clvapit:long"]
        .apply(get_value)
    )

else:

    geometry_clean["long_geometry"] = None


geometry_clean = geometry_clean.drop_duplicates(
    subset="geometry_id"
)


# ID della geometria della sede
if "clvapit:hasGeometry.@id" in sites.columns:

    sites_geometry = pd.DataFrame()

    sites_geometry["site_id"] = sites["@id"]

    sites_geometry["geometry_id"] = (
        sites["clvapit:hasGeometry.@id"]
        .apply(get_value)
    )

    sites_geometry = sites_geometry.drop_duplicates(
        subset="site_id"
    )

    output = output.merge(
        sites_geometry,
        on="site_id",
        how="left"
    )

    output = output.merge(
        geometry_clean,
        on="geometry_id",
        how="left"
    )

    # Usiamo le coordinate della geometria
    # solo se quelle del luogo sono mancanti
    output["latitudine"] = (
        output["latitudine"]
        .fillna(output["lat_geometry"])
    )

    output["longitudine"] = (
        output["longitudine"]
        .fillna(output["long_geometry"])
    )


# ============================================================
# 10. CONVERSIONE COORDINATE
# ============================================================

output["latitudine"] = pd.to_numeric(
    output["latitudine"],
    errors="coerce"
)

output["longitudine"] = pd.to_numeric(
    output["longitudine"],
    errors="coerce"
)


# ============================================================
# 11. RIMUOVIAMO GLI ID TECNICI
# ============================================================

output = output.drop(
    columns=[
        "name_id",
        "site_id",
        "address_id",
        "geometry_id",
        "comune_id",
        "provincia_id",
        "regione_id",
        "lat_geometry",
        "long_geometry"
    ],
    errors="ignore"
)


# ============================================================
# 12. ORDINE FINALE DELLE COLONNE
# ============================================================

colonne = [
    "id",
    "nome",
    "tipologia",
    "descrizione",
    "indirizzo",
    "cap",
    "latitudine",
    "longitudine",
    "identificativo",
    "immagine"
]

output = output[
    [col for col in colonne if col in output.columns]
]


# ============================================================
# 13. PULIZIA TESTO
# ============================================================

for colonna in output.select_dtypes(
    include=["object", "string"]
).columns:

    output[colonna] = (
        output[colonna]
        .astype("string")
        .str.strip()
    )


# ============================================================
# 14. ESPORTAZIONE CSV
# ============================================================

output.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 15. CONTROLLO FINALE
# ============================================================

print("\n========================================")
print("CSV CREATO")
print("========================================")

print(f"File: {OUTPUT_FILE}")
print(f"Righe: {len(output):,}")
print(f"Colonne: {len(output.columns)}")

print("\nColonne:")
print(output.columns.tolist())

print("\nValori mancanti:")
print(output.isna().sum())

print("\nPrime 10 righe:")
print(output.head(10).to_string())