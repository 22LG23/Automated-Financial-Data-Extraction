from unstructured.documents.elements import Table, Element, Title
from unstructured.partition.pdf import partition_pdf
from unstructured_client.models import operations, shared
from rapidfuzz import fuzz
from rapidfuzz import process
from openai import AzureOpenAI
import json
import os

# Path del documento
pdf_path = r"PATH_TO_PDF_DOCUMENT"

# Titoli frequenti per i prospetti contabili
titoli_frequenti ={
    "stato patrimoniale",
    "patrimonio netto",
    "patrimonio netto convalidato",
    "conto economico",
    "conto economico consolidato",
    "Rendiconto finanziario"
}

prompt_estrazione = '''
### OBIETTIVO
Estrarre **tutte le voci** contabili dai prospetti di **Stato Patrimoniale** e **Conto Economico** presenti nel testo OCR di entrambi gli anni se sono presenti.  
Restituire l’output in **formato JSON strutturato** + calcolare **10 indicatori riassuntivi** standard in una sezione separata.

---

### INPUT
OCR di bilanci aziendali. Il testo può contenere errori, impaginazioni variabili, simboli non standard o separatori numerici inconsistenti.

---

### ISTRUZIONI

1. **Identifica le sezioni contabili**:
   - Stato Patrimoniale → suddividi in `"attivo"`, `"passivo"`, `"patrimonio_netto"`
   - Conto Economico → suddividi in `"ricavi"`, `"costi"`, `"risultatoEsercizio"`

2. **Estrai tutte le voci presenti**, inclusi sottogruppi e dettagli (es. “materie prime”, “altre riserve”, “oneri diversi di gestione”, ecc.).  
   - Mantieni la gerarchia logica delle voci (es. Attivo → Rimanenze → Prodotti finiti).
   - Non omettere righe. Non aggregare.

3. **Classifica ogni valore per anno**, solo se l’anno è chiaramente indicato nel testo.

4. **Rimuovi tutti i simboli monetari** e converti i numeri in **interi puliti** (es. "2.304.000 €" → `2304000`).

5. **Non dedurre valori mancanti.**  
   Se serve calcolare un indicatore partendo da altre voci, fallo solo se la logica è esplicita e documentalo nelle note.

6. **Se sono presenti valori distinti per "gruppo" e "terzi", usa sempre il valore del gruppo.**

7. **Mantieni l’ordine di apparizione** delle voci, se possibile.

---

### VALORI RIASSUNTIVI (sezione "ValoriEstratti")

In aggiunta all’elenco completo delle voci, estrai questi 10 indicatori standard (anche se nel documento sono indicati con nomi diversi):

- UtileNetto  
- EBIT  
- TotaleAttivo  
- TotalePassivo  
- PatrimonioNetto  
- AttivitaCorrenti  
- PassivitaCorrenti  
- Immobilizzazioni  
- Rimanenze  
- PassivitaNonCorrenti  

---

### OUTPUT JSON

```json
{
  "StatoPatrimoniale": {
    "anno": {
      "attivo": {
        "categoria": {
          "voce": valore_intero
        }
      },
      "passivo": {
        "categoria": {
          "voce": valore_intero
        }
      },
      "patrimonio_netto": {
        "voce": valore_intero
      }
    }
  },
  "ContoEconomico": {
    "anno": {
      "categoria": {
        "voce": valore_intero
      }
    }
  },
  "ValoriEstratti": {
    "anno": {
      "UtileNetto": int,
      "EBIT": int,
      "TotaleAttivo": int,
      "TotalePassivo": int,
      "PatrimonioNetto": int,
      "AttivitaCorrenti": int,
      "PassivitaCorrenti": int,
      "Immobilizzazioni": int,
      "Rimanenze": int,
      "PassivitaNonCorrenti": int
    }
  },
  "note": {
    "correzioni_ocr": [],
    "ambiguita": [],
    "assunzioni": [],
    "calcoli_effettuati": []
  }
}
'''

elements = partition_pdf(
    filename=pdf_path,
    infer_table_structure=True,
    ocr_strategy="hi_res",
    hi_res_model_name="yolox",
)

#estrazione dei prospetti contabili con il metodo hi-res
def text_extraction():
    tabelle_con_titoli = {} # dizionario che contiene i titoli rilevanti (chiavi) e le tabelle associate (valori)
    for i, element in enumerate(elements):
        if isinstance(element, Table): # controllo se l'elemento è una tabella
            # coordinates = None
            # if hasattr(element.metadata):
            # # 'coordinates') and element.metadata.coordinates: controlllo se l'elemento ha l'attirbuto cordinates nei metadati
            #     coordinates = element.metadata.coordinates.points
            titoli_precedenti = [] # lista per salvare i titoli precedenti
            for j in range(max(0,i-8), i): # controllo nei 10 titoli precedenti consecutivi
                if isinstance(elements[j], Title): # controllo se l'elemento è un titolo
                    titolo_norm= elements[j].text.strip().lower() # prendo il testo dell'elemento normalizzando il titolo
                    titoli_precedenti.append(titolo_norm)

            for titolo in titoli_precedenti: # itero sui titoli precedenti nella tabella
                for titolo_frequente in titoli_frequenti:  # itero sui titoli frequneti
                    if fuzz.partial_ratio(titolo_frequente, titolo) > 75:  # controllo match titoli
                        if titolo_frequente not in tabelle_con_titoli: # aggiungo la tabella al dizionario
                            tabelle_con_titoli[titolo_frequente] = []
                                
                        tabelle_con_titoli[titolo_frequente].append((element.text)) #, coordinates))
                        break # esce dal ciclo dei titoli frequenti
                else:
                    continue # continua con il prossimo titolo
                break # se trovo un match con un titolo esco dal ciclo
    return tabelle_con_titoli

tabelle_estratte = text_extraction()

# # Formattazione output modello
# testo_formattato_per_modello = ""
# if tabelle_estratte:
#     testo_formattato_per_modello += "Testo estratto dal documento:\n" # Start della string che contiene l'output
#     for titolo, testi_tabelle in tabelle_estratte.items(): #Itero su ogni coppia chiave-valore del dizionario
#         testo_formattato_per_modello += f"\n--- {titolo.upper()} ---\n" #Aggiungo il titolo del prospetto corrente
#         for testo_tabella, _ in testi_tabelle:  # Ignoro le coordinate qui passo solo il testo
#             testo_formattato_per_modello += f"{testo_tabella}\n\n"  #Itero su ogni elemento della lista testi_tabelle
# else:
#     testo_formattato_per_modello = "Nessuna tabella è stata estratta dal documento."


def input_preparation(tabelle_estratte):
    sezioni = []
    for titolo, tabelle in tabelle_estratte.items():
        sezioni.append(f"--- {titolo.upper()} ---")
        for testo_tabella in tabelle:
            sezioni.append(testo_tabella.strip())
    return "\n\n".join(sezioni)

testo_formattato_per_modello = input_preparation(tabelle_estratte)

# Chiamata al modello
client = AzureOpenAI(
  azure_endpoint = "YOUR_AZURE_ENDPOINT",
  api_key="YOUR_API_KEY",  
  api_version="YOUR_API_VERSION"
)
 
deployment_name = "o4-mini" 
prompt = prompt_estrazione

messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "text", "text": testo_formattato_per_modello}
        ]
    }
]
 
response = client.chat.completions.create(
    model=deployment_name,
    messages=messages,
    response_format={"type": "json_object"}
)
 
# Print json della risposta
raw_json = response.choices[0].message.content
estrazione_json = json.loads(raw_json)


with open("estrazione_output.json", "w", encoding="utf-8") as f:
    json.dump(estrazione_json, f, indent=2, ensure_ascii=False)
