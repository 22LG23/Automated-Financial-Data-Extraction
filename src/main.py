from pdfminer.layout import LTContainer, LTImage, LTItem, LTTextBox
from unstructured.documents.elements import Table, Element, Title
from unstructured_client.models import operations, shared
from unstructured.partition.pdf import partition_pdf
from rapidfuzz import fuzz
from rapidfuzz import process
import pandas as pd
import os
import fitz

# Titoli frequenti
titoli_frequenti = {
    "stato patrimoniale",
    "patrimonio netto",
    "patrimonio netto convalidato",
    "conto economico",
    "conto economico consolidato",
    "rendiconto finanziario"
}

# Titoli frequenti per la nota integrativa
titoli_nota ={
    "nota integrativa",
    "nota illustrativa",
    "note illustrative",
    "note al bilancio",
    "note esplicative",
    "nota metodologica"
}

# Path del documento PDF
pdf_path = r"DOCUMENT_PATH"

# processing del documento con strategia fast
elements = partition_pdf(filename=pdf_path, strategy=shared.Strategy.FAST, split_pdf_page=True, split_pdf_allow_failed=True, split_pdf_concurrency_level=15)

def make_dir(pdf_path):
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_folder = pdf_name
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    return output_folder

output_folder = make_dir(pdf_path)

def search_relevant_pages():
    # Calcola il numero totale di pagine presenti nel documento
    total_pages = max( # uso max per ritornare il valore più alto del numero di pagina
        getattr(el.metadata, "page_number", 0) #utilizzo getattr per ottenere il numero di pagina
        for el in elements
        if hasattr(el, "metadata") and hasattr(el.metadata, "page_number") #verifica che l'elemento abbia un attributo metadata e un attributo page number
    )
    #print(total_pages)
    relevant_pages = {}
    for element in elements:
        if isinstance(element, Title) and hasattr(element, "text") and hasattr(element.metadata, "page_number"):
            title_norm = element.text.strip().lower()
            for titolo_frequente in titoli_frequenti:
                if fuzz.ratio(titolo_frequente, title_norm) > 75:
                    page_number = element.metadata.page_number
                    if titolo_frequente not in relevant_pages:
                        relevant_pages[titolo_frequente] = set()

                    # Aggiunge la pagina target
                    relevant_pages[titolo_frequente].add(page_number)

                    # Aggiungo la pagina successiva, se esiste
                    next_page = page_number + 1
                    if next_page <= total_pages:
                        relevant_pages[titolo_frequente].add(next_page)
                    else:
                        print(f"invalid page number")
                    break  # Esco dal ciclo quando trovo un match
    return relevant_pages

# prendo i numeri delle pagine dal dizionario e salvo tutto in un set
relevant_dict = search_relevant_pages()

all_pages = set()
for pages in relevant_dict.values():
    all_pages.update(pages)

all_pages = sorted(all_pages)

# Estrazione delle pagine rilevanti dei proseptti contabili in formato PDF
def page_extraction(pdf_path, all_pages, output_folder):
    doc = fitz.open(pdf_path)
    nuovo_doc = fitz.open()

    output_file_path = os.path.join(output_folder, "finale.pdf")
 
    for pagina in all_pages:
        print(f"Inserisco pagina : {pagina}")
        nuovo_doc.insert_pdf(doc, from_page=pagina - 1, to_page=pagina-1)
        print(f"Tot pagine nel documento: {len(nuovo_doc)}")

    nuovo_doc.save(output_file_path)
    nuovo_doc.close()
    doc.close()
 
    print(f"File salvato in: {output_file_path}")

    return output_file_path

final_pdf_path = page_extraction(pdf_path, all_pages, output_folder)

# Estrazione contenuto della nota integrativa
def nota_integrativa_extraction():
    testo_nota = [] # Lista per contenere le righe di testo estratte dalla nota integrativa
    matching = False # Flag per il match con la sezione della nota integrativa
    for element in elements: # Itero sul testo estratto da unstructured
        if isinstance(element, Title) and not matching: # Controllo se un elemento ha il  tag titolo
            titolo_norm = element.text.strip().lower() # Normalizzo il titolo
            if any(fuzz.partial_ratio(tn, titolo_norm) >= 80 for tn in titoli_nota): # guardo se il titolo ha un match con i titoli nel dizionario
                matching = True
            continue

        if matching and isinstance(element, Element) and not isinstance(element, Table): #controllo che l'elemento sia corretto e non sia una tabella
            testo_nota.append(element.text.strip()) # Aggiungo il testo alla lista

    return testo_nota

output_nota_integrativa = nota_integrativa_extraction()

if not os.path.exists(output_folder): #controllo se la cartella di destinazione esiste
    print(f"Errore: la cartella '{output_folder}' non esiste.")
else:
    nota_finale = os.path.join(output_folder, "nota_integrativa.txt") # Creo il percorso completo del file
    with open(nota_finale, "w", encoding="utf-8") as file: # Scrivo il contenuto della nota integrativa sul file
        for riga in output_nota_integrativa:
            file.write(riga + "\n")      

elements = partition_pdf(filename=final_pdf_path, infer_table_structure=True, strategy="hi_res", hi_res_model_name="yolox", languages=["it"])

#Processing dei prospetti contabili con il metodo hi-res
def text_extraction():
    tabelle_con_titoli = {} # dizionario che contiene i titoli rilevanti (chiavi) e le tabelle associate (valori)
    for i, element in enumerate(elements):
        if isinstance(element, Table): # controllo se l'elemento è una tabella
            coordinates = None
            page_number = None

            if hasattr(element.metadata, 'coordinates') and element.metadata.coordinates: #controlllo se l'elemento ha l'attirbuto cordinates nei metadati
                coordinates = element.metadata.coordinates.points

            if hasattr(element.metadata, 'page_number'):
                page_number = element.metadata.page_number
            
            titoli_precedenti = [] # lista per salvare i titoli precedenti
            for j in range(max(0,i-5), i): # controllo nei 10 titoli precedenti consecutivi
                if isinstance(elements[j], Title): # controllo se l'elemento è un titolo
                    titolo_norm= elements[j].text.strip().lower() # prendo il testo dell'elemento normalizzando il titolo
                    titoli_precedenti.append(titolo_norm)

            for titolo in titoli_precedenti: # itero sui titoli precedenti nella tabella
                for titolo_frequente in titoli_frequenti:  # itero sui titoli frequneti
                    if fuzz.partial_ratio(titolo_frequente, titolo) > 75:  # controllo match titoli
                        if titolo_frequente not in tabelle_con_titoli: # aggiungo la tabella al dizionario
                            tabelle_con_titoli[titolo_frequente] = []
                                
                        tabelle_con_titoli[titolo_frequente].append((element.text, coordinates, page_number))
                        break # esce dal ciclo dei titoli frequenti
                else:
                    continue # continua con il prossimo titolo
                break # se trovo un match con un titolo esco dal ciclo
    return tabelle_con_titoli

print(text_extraction())
