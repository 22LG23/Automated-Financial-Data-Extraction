import json
import os
import re

# Path per le folder
GROUND_TRUTH_FOLDER = r"GROUND_TRUTH_FOLDER_PATH"
MODELLO_FOLDER = r"MODELLO_FOLDER_PATH"
NUM_DOCUMENTI = 10

def normalize_key(key):
    if not isinstance(key, str):
        key = str(key)
    normalized_key = key.lower()
    normalized_key = re.sub(r'[^a-z0-9]', '', normalized_key)

    return normalized_key

def recursive_extraction(data, voci_set):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                recursive_extraction(value, voci_set)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        recursive_extraction(item, voci_set)
            elif isinstance(value, (int, float)):
                key_clean = normalize_key(key)
                voci_set.add((key_clean, value))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                recursive_extraction(item, voci_set)


def ground_truth_extraction(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    voci_set = set()
    recursive_extraction(data, voci_set)
    return voci_set

def model_extraction(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    voci_set = set()
    recursive_extraction(data, voci_set)
    return voci_set

def compute_recall_precision(ground_truth_file, modello_file):
    voci_ground_truth = ground_truth_extraction(ground_truth_file)
    voci_modello = model_extraction(modello_file)
    
    true_positives = voci_ground_truth.intersection(voci_modello)
    false_negatives = voci_ground_truth - voci_modello
    false_positives = voci_modello - voci_ground_truth
    
    recall = len(true_positives) / len(voci_ground_truth) if voci_ground_truth else 0
    precision = len(true_positives) / len(voci_modello) if voci_modello else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'recall': recall,
        'precision': precision,
        'f1_score': f1_score,
        'num_true_positives': len(true_positives),
        'num_false_negatives': len(false_negatives),
        'num_false_positives': len(false_positives),
        'total_ground_truth': len(voci_ground_truth),
        'total_model': len(voci_modello),
        'false_negatives': false_negatives,
        'false_positives': false_positives
    }

def compute_metrics(ground_truth_folder, modello_folder, num_documenti):
    recall_totali = []
    precision_totali = []
    f1_totali = []
    detailed_results = []
    
    for i in range(1, num_documenti + 1):
        ground_truth_file = os.path.join(ground_truth_folder, f"documento_{i}.json")
        modello_file = os.path.join(modello_folder, f"documento_{i}.json")
        
        if os.path.exists(ground_truth_file) and os.path.exists(modello_file):
            risultato = compute_recall_precision(ground_truth_file, modello_file)
            recall_totali.append(risultato['recall'])
            precision_totali.append(risultato['precision'])
            f1_totali.append(risultato['f1_score'])
            detailed_results.append({
                'document': i,
                'recall': risultato['recall'],
                'precision': risultato['precision'],
                'f1_score': risultato['f1_score'],
                'true_positives': risultato['num_true_positives'],
                'false_negatives': risultato['num_false_negatives'],
                'false_positives': risultato['num_false_positives'],
                'total_ground_truth': risultato['total_ground_truth'],
                'total_model': risultato['total_model']
            })
    
    recall_medio = sum(recall_totali) / len(recall_totali) if recall_totali else 0
    precision_media = sum(precision_totali) / len(precision_totali) if precision_totali else 0
    f1_medio = sum(f1_totali) / len(f1_totali) if f1_totali else 0
    
    return {
        'recall_medio': recall_medio,
        'precision_media': precision_media,
        'f1_medio': f1_medio,
        'recall_per_documento': recall_totali,
        'precision_per_documento': precision_totali,
        'f1_per_documento': f1_totali,
        'detailed_results': detailed_results
    }

def print_metrics(results):
    recall_medio = results['recall_medio']
    precision_media = results['precision_media']
    f1_medio = results['f1_medio']
    detailed = results['detailed_results']
    
    print("RISULTATI RECALL, PRECISION e F1-SCORE")
    print(f"Recall medio:    {recall_medio:.4f} ({recall_medio*100:.2f}%)")
    print(f"Precision media: {precision_media:.4f} ({precision_media*100:.2f}%)")
    print(f"F1-Score medio:  {f1_medio:.4f} ({f1_medio*100:.2f}%)")
    print(f"Documenti processati: {len(detailed)}")
    
    print("\nDettaglio per documento:")
    print("-" * 70)
    print(f"{'Doc':<4} {'Recall':<8} {'Prec.':<8} {'F1':<8} {'TP':<4} {'FN':<4} {'FP':<4}")
    print("-" * 70)
    
    for result in detailed:
        doc_num = result['document']
        recall = result['recall']
        precision = result['precision']
        f1 = result['f1_score']
        tp = result['true_positives']
        fn = result['false_negatives']
        fp = result['false_positives']
        
        print(f"{doc_num:<4} {recall:<8.4f} {precision:<8.4f} {f1:<8.4f} {tp:<4} {fn:<4} {fp:<4}")

results = compute_metrics(GROUND_TRUTH_FOLDER, MODELLO_FOLDER, NUM_DOCUMENTI)
print_metrics(results)
