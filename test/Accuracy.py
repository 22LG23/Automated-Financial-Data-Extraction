import json
import os

GROUND_TRUTH_FOLDER = r"C:\Users\lucag\Desktop\bilanciGenAi\groundtruth"
MODELLO_FOLDER = r"C:\Users\lucag\Desktop\bilanciGenAi\Unstructured"

# GROUND_TRUTH_FILE = r"C:\Users\lgiandomenico\OneDrive - BUSINESS INTEGRATION PARTNERS SPA\Desktop\bilanciGenAi\groundtruth\documento_3.json"
# MODELLO_FILE = r"C:\Users\lgiandomenico\OneDrive - BUSINESS INTEGRATION PARTNERS SPA\Desktop\bilanciGenAi\extracted_unstructured\documento_3.json"

# Lista di 10 voci quozienti di bilancio
REQUIRED_FIELDS = [
    "UtileNetto",
    "EBIT", 
    "TotaleAttivo",
    "TotalePassivo",
    "PatrimonioNetto",
    "AttivitaCorrenti",
    "PassivitaCorrenti",
    "Immobilizzazioni",
    "Rimanenze",
    "PassivitaNonCorrenti"
]

# Carico Json e restituisco un dizionario di voci
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
#data = load_json(MODELLO_FILE)

# Estrazione dei valori dalla ground truth
def extract_values_from_ground_truth(data):
    valori_estratti = data.get("ValoriEstratti", {})
    if valori_estratti and isinstance(valori_estratti, dict):
        max_year = max(valori_estratti.keys())
        year_data = valori_estratti.get(max_year, {})
        # Controllo che year_data sia un dizionario
        if isinstance(year_data, dict):
            return year_data
    return {}

# result = extract_values_from_ground_truth(data)
# print(result)

def extract_values_from_model(data):
    valori_estratti = data.get("ValoriEstratti", {}) 
    if valori_estratti and isinstance(valori_estratti, dict):
        max_year = max(valori_estratti.keys())
        year_data = valori_estratti.get(max_year, {})
        # Controllo che year_data sia un dizionario
        if isinstance(year_data, dict):
            return year_data
    return {}

# result = extract_values_from_model(data)
# print(result)

# Confronta i valori estratti da ground truth e modello 
def compare_values(gt_values, model_values):

    results = {}
    
    for field in REQUIRED_FIELDS:
        gt_value = gt_values.get(field)
        model_value = model_values.get(field)
        
        # Confronto esatto
        is_correct = gt_value == model_value
        results[field] = {
            'correct': is_correct,
            'gt_value': gt_value,
            'model_value': model_value
        }
    
    return results


# Calcolo dell'accuracy per ogni docuemnto 
def calculate_document_accuracy(comparison_results):
    correct_count = sum(1 for result in comparison_results.values() if result['correct'])
    total_count = len(REQUIRED_FIELDS)
    return correct_count / total_count


# Calcolo dell'accuracy per ogni voce del dataset
def calculate_overall_accuracy(all_results):
    field_accuracies = {}
    
    for field in REQUIRED_FIELDS:
        correct_count = 0
        total_count = 0
        
        for doc_results in all_results:
            if field in doc_results:
                total_count += 1
                if doc_results[field]['correct']:
                    correct_count += 1
        
        field_accuracies[field] = {
            'correct': correct_count,
            'total': total_count,
            'accuracy': correct_count / total_count if total_count > 0 else 0
        }
    
    return field_accuracies

# Stampa risultati
def print_results(document_accuracies, field_accuracies):
    print("Accuratezza per documento:")
    for doc_name, accuracy in document_accuracies.items():
        print(f"{doc_name}: {accuracy:.2f}")
    
    print("\nAccuratezza per voce:")
    for field in REQUIRED_FIELDS:
        stats = field_accuracies[field]
        print(f"{field}: {stats['correct']}/{stats['total']}")

    print("\nAccuratezza media:")
    total_field_accuracy = sum(field_accuracies[field]['accuracy'] for field in REQUIRED_FIELDS)
    avg_field_accuracy = total_field_accuracy / len(REQUIRED_FIELDS)
    print(f"{avg_field_accuracy:.2f}")


# Funzione che processa tutto il dataset Json
def run_accuracy_evaluation():

    #Lista dei file JSON dalla cartella ground truth
    json_files = [f for f in os.listdir(GROUND_TRUTH_FOLDER) if f.endswith('.json')]
    
    if not json_files:
        print("File json non trovato")
        return
    all_results = []
    document_accuracies = {}
    
    for filename in json_files:
        gt_file = os.path.join(GROUND_TRUTH_FOLDER, filename)
        extracted_file = os.path.join(MODELLO_FOLDER, filename)
        
        #Verifica che entrambi i file esistano
        if not os.path.exists(extracted_file):
            print(f"File {filename} non trovato nella cartella extracted, saltato.")
            continue
        
        #Carica e processa la coppia di documenti
        gt_data = load_json(gt_file)
        model_data = load_json(extracted_file)
        
        #Estrazione con funzioni
        gt_values = extract_values_from_ground_truth(gt_data)
        model_values = extract_values_from_model(model_data)
        
        #Comparison dei risultati
        comparison_results = compare_values(gt_values, model_values)
        doc_accuracy = calculate_document_accuracy(comparison_results)
        
        all_results.append(comparison_results)
        document_accuracies[filename] = doc_accuracy
    
    #Calcola e stampa i risultati
    field_accuracies = calculate_overall_accuracy(all_results)
    print_results(document_accuracies, field_accuracies)


#Esecuzione
run_accuracy_evaluation()