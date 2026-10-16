#!/usr/bin/env bash

# Prepare a flat MIMIC-III download for a database loader.
# The input directory is never modified. MIMIC-III and MIMIC-IV use different
# schemas, so this script must not be used with the MIMIC-IV loader.

set -euo pipefail

usage() {
    echo "Usage: prepare_mimic_iii.sh [--force] <flat_input_dir> <output_dir>" >&2
    echo "Creates output_dir/hosp and output_dir/icu with decompressed CSV files." >&2
    exit 2
}

FORCE=false
if [[ "${1:-}" == "--force" ]]; then FORCE=true; shift; fi
[[ $# -eq 2 ]] || usage
INPUT_DIR=$1
OUTPUT_DIR=$2
[[ -d "$INPUT_DIR" ]] || { echo "ERROR: input directory does not exist: $INPUT_DIR" >&2; exit 1; }
[[ "$INPUT_DIR" != "$OUTPUT_DIR" ]] || { echo "ERROR: input and output directories must differ" >&2; exit 1; }
if [[ -e "$OUTPUT_DIR" && "$FORCE" != true ]]; then
    echo "ERROR: output already exists: $OUTPUT_DIR" >&2
    echo "Use --force to overwrite output CSV files." >&2
    exit 1
fi
mkdir -p "$OUTPUT_DIR/hosp" "$OUTPUT_DIR/icu"

classify() {
    case "$1" in
        ADMISSIONS|CALLOUT|CAREGIVERS|CPTEVENTS|D_CPT|D_LABITEMS|DIAGNOSES_ICD|DRGCODES|D_ICD_DIAGNOSES|D_ICD_PROCEDURES|LABEVENTS|MICROBIOLOGYEVENTS|NOTEEVENTS|PATIENTS|PRESCRIPTIONS|PROCEDURES_ICD|SERVICES|TRANSFERS) printf '%s' hosp ;;
        CHARTEVENTS|DATETIMEEVENTS|D_ITEMS|ICUSTAYS|INPUTEVENTS_CV|INPUTEVENTS_MV|OUTPUTEVENTS|PROCEDUREEVENTS_MV) printf '%s' icu ;;
        *) return 1 ;;
    esac
}

shopt -s nullglob
files=("$INPUT_DIR"/*.csv.gz)
[[ ${#files[@]} -gt 0 ]] || { echo "ERROR: no .csv.gz files found in $INPUT_DIR" >&2; exit 1; }

count=0
unknown=0
for source in "${files[@]}"; do
    filename=${source##*/}
    table=${filename%.csv.gz}
    if ! section=$(classify "$table"); then
        echo "WARNING: unrecognized MIMIC-III file, skipped: $filename" >&2
        unknown=$((unknown + 1)); continue
    fi
    normalized_table=$(printf '%s' "$table" | tr '[:upper:]' '[:lower:]')
    destination="$OUTPUT_DIR/$section/$normalized_table.csv"
    if [[ -e "$destination" && "$FORCE" != true ]]; then
        echo "ERROR: output file already exists: $destination" >&2; exit 1
    fi
    echo "Decompressing $filename -> $section/$normalized_table.csv"
    gzip -dc -- "$source" > "$destination"
    count=$((count + 1))
done

echo "Prepared $count MIMIC-III files in $OUTPUT_DIR"
[[ $unknown -eq 0 ]] || echo "Skipped $unknown unrecognized file(s); review the warnings." >&2
echo "NOTE: use a MIMIC-III-compatible schema/loader, not the MIMIC-IV loader."
