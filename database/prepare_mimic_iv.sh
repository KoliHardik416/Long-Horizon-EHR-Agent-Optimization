#!/usr/bin/env bash

# Prepare a flat MIMIC-IV download for the PostgreSQL loader.
# The input directory is never modified.

set -euo pipefail

usage() {
    cat >&2 <<'EOF'
Usage:
  prepare_mimic_iv.sh [--force] <flat_input_dir> <output_dir>

Decompresses flat MIMIC-IV *.csv.gz files into output_dir/hosp and
output_dir/icu. The output can then be passed to the PostgreSQL loader.
EOF
    exit 2
}

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
    shift
fi
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
        admissions|d_hcpcs|d_icd_diagnoses|d_icd_procedures|d_labitems|diagnoses_icd|drgcodes|emar|emar_detail|hcpcsevents|labevents|microbiologyevents|omr|patients|pharmacy|poe|poe_detail|prescriptions|procedures_icd|provider|services|transfers) printf '%s' hosp ;;
        caregiver|chartevents|datetimeevents|d_items|icustays|ingredientevents|inputevents|outputevents|procedureevents) printf '%s' icu ;;
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
        echo "WARNING: unrecognized MIMIC-IV file, skipped: $filename" >&2
        unknown=$((unknown + 1))
        continue
    fi
    destination="$OUTPUT_DIR/$section/$table.csv"
    if [[ -e "$destination" && "$FORCE" != true ]]; then
        echo "ERROR: output file already exists: $destination" >&2
        exit 1
    fi
    echo "Decompressing $filename -> $section/$table.csv"
    gzip -dc -- "$source" > "$destination"
    count=$((count + 1))
done

echo "Prepared $count MIMIC-IV files in $OUTPUT_DIR"
[[ $unknown -eq 0 ]] || echo "Skipped $unknown unrecognized file(s); review the warnings." >&2
echo "Next: database/mimic-iv/buildmimic/postgres/build_mimic.sh $OUTPUT_DIR"

