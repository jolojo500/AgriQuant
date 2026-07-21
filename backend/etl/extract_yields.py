import requests
import zipfile
import io
import pandas as pd
from pydantic import BaseModel
from pathlib import Path
from etl.transform_config import START_YEAR, END_YEAR

# Bulk download URL — public, no auth required
FAOSTAT_BULK_URL = (
    "https://fenixservices.fao.org/faostat/static/bulkdownloads/"
    "Production_Crops_Livestock_E_All_Data_(Normalized).zip"
)

FAO_CROPS = {
    "maize":     "Maize (corn)",
    "wheat":     "Wheat",
    "soybeans":  "Soya beans",
    "rice":      "Rice",
    "cotton":    "Seed cotton, unginned",
    "canola":    "Rape or colza seed",
    "sunflower": "Sunflower seed",
    "cassava":   "Cassava, fresh",
    "potatoes":  "Potatoes",
}

FAO_COUNTRIES = {
    "usa":       "United States of America",
    "brazil":    "Brazil",
    "argentina": "Argentina",
    "canada":    "Canada",
    "china":     "China, mainland",
    "india":     "India",
}


#Pydantic models
class YieldRecord(BaseModel):
    year: int
    country: str
    crop: str
    yield_kg_ha: float      # kg/hectare — actual FAO unit in this bulk file
    yield_tonnes_ha: float  # same, divided by 1000 (1 tonne = 1000 kg)
                            # ex: US corn ≈ 10.7 t/ha, wheat ≈ 3.5 t/ha

class YieldResponse(BaseModel):
    crop: str
    country: str
    records: list[YieldRecord]


def download_faostat_bulk() -> pd.DataFrame:
    """
    Downloads the full FAOSTAT crop production ZIP (no auth needed).
    Returns a filtered DataFrame with only Yield data.
    This is a big file (~50MB) so we cache it locally.
    """
    cache_path = Path(__file__).parent.parent / "faostat_cache.csv"

    # Use cache if it exists — avoids re-downloading 50MB every run
    if cache_path.exists():
        print("  Using cached FAOSTAT data...")
        return pd.read_csv(cache_path, low_memory=False)

    print("  Downloading FAOSTAT bulk file (~50MB, once only)...")
    response = requests.get(FAOSTAT_BULK_URL, timeout=120)
    response.raise_for_status()

    # Unzip in memory — no temp files needed
    # Stream in chunks and keep only rows we can ever use (Yield rows for our
    # crops/countries, columns parse_yields reads): the full normalized CSV is
    # millions of rows and a one-shot read_csv blows small-RAM hosts (likely
    # what OOM-killed the July 1 quarterly run on Render's 512MB instance).
    # NOTE: cache is filtered to FAO_CROPS/FAO_COUNTRIES — delete
    # faostat_cache.csv after adding crops/countries so it refetches.
    keep_items = set(FAO_CROPS.values())
    keep_areas = set(FAO_COUNTRIES.values())
    usecols = ["Area", "Item", "Element", "Year", "Unit", "Value"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # The normalized file inside the zip
        csv_filename = [f for f in z.namelist() if "Normalized" in f][0]
        with z.open(csv_filename) as f:
            chunks = [
                chunk[
                    (chunk["Element"] == "Yield")
                    & chunk["Item"].isin(keep_items)
                    & chunk["Area"].isin(keep_areas)
                ]
                for chunk in pd.read_csv(f, encoding="latin1", chunksize=200_000, usecols=usecols)
            ]
    df = pd.concat(chunks, ignore_index=True)

    # Cache for future runs
    df.to_csv(cache_path, index=False)
    print(f"  Cached to {cache_path}")

    return df


def parse_yields(df: pd.DataFrame, crop: str, country: str) -> YieldResponse:
    crop_name = FAO_CROPS.get(crop)
    country_name = FAO_COUNTRIES.get(country)

    if not crop_name or not country_name:
        raise ValueError(f"Unknown crop '{crop}' or country '{country}'")

    filtered = df[
        (df["Item"] == crop_name) &
        (df["Area"] == country_name) &
        (df["Year"].between(START_YEAR, END_YEAR))
    ].copy()

    if filtered.empty:
        raise ValueError(f"No data for {crop} / {country}")

    records = [
        YieldRecord(
            year=int(row["Year"]),
            country=country,
            crop=crop,
            yield_kg_ha=float(row["Value"]),
            yield_tonnes_ha=round(float(row["Value"]) / 1000, 4),
        )
        for _, row in filtered.iterrows()
        if pd.notna(row["Value"])
    ]

    records.sort(key=lambda r: r.year)
    return YieldResponse(crop=crop, country=country, records=records)


def fetch_all_yields(df: pd.DataFrame) -> list[YieldResponse]:
    results = []
    total = len(FAO_CROPS) * len(FAO_COUNTRIES)
    count = 0

    for crop in FAO_CROPS:
        for country in FAO_COUNTRIES:
            count += 1
            print(f"  [{count}/{total}] {crop:12} / {country}...")
            try:
                result = parse_yields(df, crop, country)
                results.append(result)
                print(f"           {len(result.records)} years")
            except Exception as e:
                print(f"           Error: {e}")

    return results


if __name__ == "__main__":
    # Download once, reuse for all queries
    df = download_faostat_bulk()
    

    # Debug stuff
    #sample = df[(df["Item"] == "Maize (corn)") & (df["Area"] == "United States of America")]
    #print( sample)
    #print(sample[["Year", "Element", "Unit", "Value"]].tail(5))
    #items = df[df["Item"].str.contains("rape|canola", case=False, na=False)]["Item"].unique()
    #print(items)

    choice = input("\nFetch (1) specific combination or (2) all ? ")

    if choice == "1":
        print(f"Available crops    : {list(FAO_CROPS.keys())}")
        print(f"Available countries: {list(FAO_COUNTRIES.keys())}")
        crop = input("Crop : ").lower()
        country = input("Country : ").lower()

        result = parse_yields(df, crop, country)
        print(f"\nCrop    : {result.crop}")
        print(f"Country : {result.country}")
        print(f"Years   : {len(result.records)}")
        print(f"First   : {result.records[0]}")
        print(f"Last    : {result.records[-1]}")

    elif choice == "2":
        results = fetch_all_yields(df)
        print(f"\nTotal fetched: {len(results)}")
        for r in results:
            if r.records:
                print(f"  {r.crop:12} / {r.country:12} → "
                      f"latest yield: {r.records[-1].yield_tonnes_ha} t/ha")