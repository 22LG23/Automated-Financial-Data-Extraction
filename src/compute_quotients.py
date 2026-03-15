import json

# Percorso al file JSON
document_path = r"DOCUMENT_PATH"

#  File Json
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        return json.load(file)

dati = load_json(document_path)

def extract_values_from_model(data):
    valori_estratti = data.get("ValoriEstratti", {}) 
    if valori_estratti and isinstance(valori_estratti, dict):
        max_year = max(valori_estratti.keys())
        year_data = valori_estratti.get(max_year, {})
        # Assicurati che year_data sia un dizionario
        if isinstance(year_data, dict):
            return year_data
    return {}

valori = extract_values_from_model(dati)

#print(valori)


def calcola_quozienti(valori):

    risultati = {} # dizionario per ritornare i risultati

    # Quozienti di redditività
    try: risultati["ROE"] = valori["UtileNetto"] / valori["PatrimonioNetto"]
    except: risultati["ROE"] = None

    try: risultati["ROI"] = valori["EBIT"] / valori["TotaleAttivo"]
    except: risultati["ROI"] = None

    # Quozienti di liquidità
    try: risultati["AT"] = valori["TotaleAttivo"] / valori["TotalePassivo"]
    except: risultati["AT"] = None

    try: risultati["IndiceDiLiquidità"] = valori["AttivitaCorrenti"] / valori["PassivitàCorrenti"]
    except: risultati["IndiceDiLiquidità"] = None

    # Quozienti di solidità patrimoniale
    try:
        risultati["CI"] = (valori["TotalePassivo"] + valori["PatrimonioNetto"]) / valori["Immobilizzazioni"]
    except:
        risultati["CI"] = None

    try:
        risultati["AutonomiaFinanziaria"] = (valori["PatrimonioNetto"] / valori["TotalePassivo"])* 100
    except:
        risultati["AutonomiaFinanziaria"] = None

    return risultati

quozienti = calcola_quozienti(valori)

print(quozienti)

