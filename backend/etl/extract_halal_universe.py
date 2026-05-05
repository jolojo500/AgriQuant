import requests
import json
import time
from bs4 import BeautifulSoup
from datetime import date
from pathlib import Path

# Hardcoded candidates
# Sources: yfinance industry tags + manual research
AG_CANDIDATES = {
    # agricultural equipment
    "DE": "John Deere",
    "AGCO": "AGCO Corporation",
    "CNH": "CNH Industrial",
    "CNHI": "CNH Industrial (NYSE)",
    "LNN": "Lindsay Corporation (irrigation)",
    "IIHR": "Indica Industries",

    # Fertilizers & others (pesticides etc)
    "NTR": "Nutrien",
    "MOS": "Mosaic",
    "CTVA": "Corteva",
    #"DD": "DuPont de Nemours", #ctva and DD were together, might still have relevant activity that gets affected
    "FMC": "FMC Corporation",
    "IPI": "Intrepid Potash",
    "SEED": "Origin Agritech",
    "SANW": "S&W Seed Company",

    # Food processing & distribution
    "ADM": "Archer-Daniels-Midland",
    "BG": "Bunge",
    "INGR": "Ingredion",
    "CALM": "Cal-Maine Foods (eggs)",
    "SAFM": "Sanderson Farms",
    "HRL": "Hormel Foods",
    "TSN": "Tyson Foods",
    "SFM": "Sprouts Farmers Market",
    "WFCF": "Where Food Comes From",
    "VITL": "Vital Farms",

    # Canadian
    "BAYRY": "Bayer AG (seeds/pesticides)",
    "SYT": "Syngenta",
    "AG": "First Majestic (silver/AG symbol)",
    "TFII": "TFI International",

    # Agricultural machinery/tech
    "RAVN": "Raven Industries",
#    "PRLB": "Proto Labs", very vaguely related tbf
    "KRYS": "Krystal Biotech",
    "TRMK": "Trimble (precision ag)",
    "TRIMBLE": "Trimble",
    "TRMB": "Trimble Navigation",
} #would seem like things of heavy machinery liek tractors etc dont pass screening because these companies have a financial branch which does loaning


def check_zoya_compliance(ticker: str) -> str:
    """
    Fetche Zoya page for a ticker and returns:
    'compliant', 'non_compliant', or 'unknown'
    """
    url = f"https://zoya.finance/stocks/{ticker.lower()}" #manually found btw I aint paying for that
    headers = {
        #Present ourselves as normal user
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return "unknown"

        soup = BeautifulSoup(response.text, "html.parser")

        # Looks for the h2 that contains the status
        # Pattern: "TICKER stock is Shariah-compliant" or "not Shariah-compliant"
        for h2 in soup.find_all("h2"):
            text = h2.get_text().lower()
            if "shariah-compliant" in text or "sharia-compliant" in text:
                if "not shariah" in text or "not sharia" in text:
                    return "non_compliant"
                else:
                    return "compliant"

        return "unknown"

    except Exception as e:
        print(f"  Error for {ticker}: {e}")
        return "unknown"


def build_halal_universe():
    """
    Check all candidates on Zoya and sauve
    the compliants in halal_universe.json
    """ 
    results = {
        "last_verified": str(date.today()),
        "screener": "Zoya (AAOIFI methodology)",
        "compliant": [],
        "non_compliant": [],
        "unknown": [],
    }

    print(f"Checking {len(AG_CANDIDATES)} tickers on Zoya...\n")

    for ticker, name in AG_CANDIDATES.items():
        status = check_zoya_compliance(ticker)
        print(f"  {ticker:10} {name:40} → {status}")

        entry = {"ticker": ticker, "name": name}

        if status == "compliant":
            results["compliant"].append(entry)
        elif status == "non_compliant":
            results["non_compliant"].append(entry)
        else:
            results["unknown"].append(entry)

        # To respect the servers after all we are a normal user
        time.sleep(2)

    # Always saves in the backend/  folder (because this file's parent parent folder)
    output_path = Path(__file__).parent.parent / "halal_universe.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f" Results:")
    print(f"   Compliant    : {len(results['compliant'])}")
    print(f"   Non-compliant: {len(results['non_compliant'])}")
    print(f"   Unknown      : {len(results['unknown'])}")
    print(f"Saved in {output_path}")


if __name__ == "__main__":
    build_halal_universe()