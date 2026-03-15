# Financial Statement Analysis Pipeline

## Overview

This project implements an end-to-end pipeline for the automated ingestion, parsing, and structured extraction of financial data from Italian corporate annual reports (bilanci aziendali) in PDF format. The goal is to reduce the manual effort required to analyze financial statements by automatically identifying relevant accounting sections, extracting tabular data, and computing standard financial ratios.

The pipeline is built on the `Unstructured` library for PDF parsing, combined with `OpenAI o4-mini` for structured data extraction. It outputs structured JSON files containing the full balance sheet (Stato Patrimoniale), income statement (Conto Economico), and a set of pre-computed summary financial values, which are then used to calculate financial ratios.

## Pipeline Architecture

```
![1773578694674](image/README/1773578694674.png)
```

## Repository Structure

```
├── main.py                              # Open-source pipeline (page classification + extraction)
├── structured_data_pipeline_unstructured.py  # Full pipeline: OCR → LLM → JSON output
├── compute_quotients.py                 # Financial ratio computation from extracted JSON
└── README.md
```

## How It Works

### 1. Document Ingestion & Page Classification

The pipeline begins by ingesting the full PDF using `Unstructured` with the `fast` strategy. A heuristic function then scans all extracted elements for `Title` elements whose text fuzzy-matches a predefined set of relevant accounting section headings:

**Target headings (titoli frequenti):**

* `stato patrimoniale`
* `patrimonio netto` / `patrimonio netto convalidato`
* `conto economico` / `conto economico consolidato`
* `rendiconto finanziario`

Fuzzy matching is performed using `RapidFuzz` (`fuzz.ratio > 75`), tolerating OCR errors and minor formatting inconsistencies. Matched pages (plus the following page) are collected into a reduced sub-document, which is saved as `finale.pdf`.

Additionally, the **nota integrativa** (notes to the financial statements) is extracted as plain text and saved to `nota_integrativa.txt`.

### 2. High-Resolution Table Extraction

The reduced PDF (`finale.pdf`) is re-processed with `Unstructured` using the `hi_res` strategy and the `yolox` model for accurate table structure inference. Tables are associated with their nearest preceding title via a sliding window of up to 5–8 preceding elements, again using fuzzy matching.

### 3. Structured Data Extraction via LLM (`structured_data_pipeline_unstructured.py`)

The extracted table text is formatted into a prompt and sent to **OpenAI o4-mini** (via Azure OpenAI). The model is instructed to:

* Identify and parse all accounting entries from the Stato Patrimoniale and Conto Economico.
* Preserve the full hierarchy of entries (no aggregation).
* Classify values by year.
* Normalize all monetary values to clean integers (removing currency symbols and separators).
* Extract 10 standard summary financial values (`ValoriEstratti`) used for ratio computation.

The model responds exclusively in JSON format. The output is validated, parsed, and saved to `estrazione_output.json`.

**Summary values extracted (`ValoriEstratti`):**

| Field                    | Description                        |
| ------------------------ | ---------------------------------- |
| `UtileNetto`           | Net profit                         |
| `EBIT`                 | Earnings before interest and taxes |
| `TotaleAttivo`         | Total assets                       |
| `TotalePassivo`        | Total liabilities                  |
| `PatrimonioNetto`      | Shareholders' equity               |
| `AttivitaCorrenti`     | Current assets                     |
| `PassivitaCorrenti`    | Current liabilities                |
| `Immobilizzazioni`     | Fixed assets                       |
| `Rimanenze`            | Inventories                        |
| `PassivitaNonCorrenti` | Non-current liabilities            |

### 4. Financial Ratio Computation

Once the JSON is available, `compute_quotients.py` loads it, selects the most recent year's data from `ValoriEstratti`, and computes the following ratios:

| Ratio                           | Formula                                              | Description              |
| ------------------------------- | ---------------------------------------------------- | ------------------------ |
| **ROE**                   | UtileNetto / PatrimonioNetto                         | Return on Equity         |
| **ROI**                   | EBIT / TotaleAttivo                                  | Return on Investment     |
| **AT**                    | TotaleAttivo / TotalePassivo                         | Asset-to-Liability ratio |
| **Indice di Liquidità**  | AttivitaCorrenti / PassivitaCorrenti                 | Current Ratio            |
| **CI**                    | (TotalePassivo + PatrimonioNetto) / Immobilizzazioni | Capital intensity        |
| **Autonomia Finanziaria** | (PatrimonioNetto / TotalePassivo) × 100             | Financial autonomy (%)   |

All divisions are wrapped in `try/except` blocks, returning `None` for any ratio that cannot be computed due to missing values.

## Key Technologies

| Tool                                                         | Role                                                                        |
| ------------------------------------------------------------ | --------------------------------------------------------------------------- |
| [Unstructured](https://github.com/Unstructured-IO/unstructured) | PDF ingestion, OCR, and document element classification                     |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)               | Page extraction and sub-document creation                                   |
| [RapidFuzz](https://github.com/maxbachmann/RapidFuzz)           | Fuzzy string matching for title identification (Levenshtein distance)       |
| [OpenAI o4-mini](https://openai.com/)                           | LLM-based structured data extraction from OCR text                          |
| YOLOX                                                        | Deep learning model for high-resolution table detection within Unstructured |

## Setup & Configuration

### Prerequisites

* Python 3.9+
* An LLM API key

### Installation

```bash
uv add unstructured[pdf] rapidfuzz pymupdf openai
```

### Configuration

Before running, update the following placeholders in each script:

**`main.py` and `structured_data_pipeline_unstructured.py`:**

```python
pdf_path = r"PATH_TO_PDF_DOCUMENT"
```

**`structured_data_pipeline_unstructured.py`** (OpenAI credentials):

```python
azure_endpoint = "YOUR_AZURE_ENDPOINT"
api_key = "YOUR_API_KEY"
api_version = "YOUR_API_VERSION"
```

**`compute_quotients.py`:**

```python
document_path = r"PATH_TO_JSON_OUTPUT"
```

---

## Running the Pipeline

### Step 1 — Extract and classify pages, extract nota integrativa

```bash
python main.py
```

Output: `<document_name>/finale.pdf`, `<document_name>/nota_integrativa.txt`

### Step 2 — Extract structured financial data

```bash
python structured_data_pipeline_unstructured.py
```

Output: `estrazione_output.json`

### Step 3 — Compute financial ratios

```bash
python compute_quotients.py
```

Output: printed dictionary of computed ratios

---

## Output JSON Structure

```json
{
  "StatoPatrimoniale": {
    "<year>": {
      "attivo": { ... },
      "passivo": { ... },
      "patrimonio_netto": { ... }
    }
  },
  "ContoEconomico": {
    "<year>": { ... }
  },
  "ValoriEstratti": {
    "<year>": {
      "UtileNetto": 0,
      "EBIT": 0,
      "TotaleAttivo": 0,
      ...
    }
  },
  "note": {
    "correzioni_ocr": [],
    "ambiguita": [],
    "assunzioni": [],
    "calcoli_effettuati": []
  }
}
```

## Limitations & Known Issues

* OCR quality is heavily dependent on the PDF source. Scanned, low-resolution, or two-column documents may result in incomplete table extraction.
* The heuristic title-matching approach works well for standard Italian statutory financial statements but may need tuning for non-standard layouts or foreign-language documents.
* The LLM extraction step depends on the quality of the OCR output fed to it; errors in OCR propagate to the JSON output.
* The pipeline currently selects only the **most recent year** when computing ratios. Multi-year trend analysis requires minor extension of `compute_quotients.py`.
* API credentials are currently hardcoded in the scripts and should be moved to environment variables or a `.env` file for production use.
