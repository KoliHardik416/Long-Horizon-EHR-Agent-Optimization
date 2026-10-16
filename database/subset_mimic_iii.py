#!/usr/bin/env python3
"""Create a patient-consistent, compressed MIMIC-III subset.

The input directory is left unchanged. The output remains flat and uses the
original uppercase MIMIC-III filenames so it can be consumed by the official
PostgreSQL `mimic-gz` loader.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import random
import shutil
from pathlib import Path


def gz_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.csv.gz"), key=lambda p: p.name.upper())


def read_subject_ids(path: Path, count: int, seed: int) -> set[str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        field = next((f for f in reader.fieldnames or [] if f.upper() == "SUBJECT_ID"), None)
        if field is None:
            raise ValueError(f"{path.name} has no SUBJECT_ID column")
        ids = sorted({row[field].strip() for row in reader if row[field].strip()})
    if len(ids) < count:
        raise ValueError(f"{path.name} contains only {len(ids)} subjects; requested {count}")
    random.Random(seed).shuffle(ids)
    return set(ids[:count])


def filter_file(source: Path, destination: Path, subjects: set[str]) -> tuple[int, int]:
    with gzip.open(source, "rt", encoding="utf-8", newline="") as src:
        reader = csv.reader(src)
        header = next(reader)
        normalized = [column.strip().upper() for column in header]
        subject_index = normalized.index("SUBJECT_ID") if "SUBJECT_ID" in normalized else None
        destination.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(destination, "wt", encoding="utf-8", newline="") as dst:
            writer = csv.writer(dst, lineterminator="\n")
            writer.writerow(header)
            scanned = written = 0
            for row in reader:
                scanned += 1
                if subject_index is None or (subject_index < len(row) and row[subject_index].strip() in subjects):
                    writer.writerow(row)
                    written += 1
    return scanned, written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-subjects", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        parser.error(f"input directory does not exist: {args.input_dir}")
    if args.input_dir.resolve() == args.output_dir.resolve():
        parser.error("input and output directories must differ")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.force:
        parser.error(f"output directory is not empty: {args.output_dir}; use --force")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sources = gz_files(args.input_dir)
    patients = next((p for p in sources if p.name.upper() == "PATIENTS.CSV.GZ"), None)
    if patients is None:
        parser.error("input directory does not contain PATIENTS.csv.gz")
    subjects = read_subject_ids(patients, args.num_subjects, args.seed)
    print(f"Selected {len(subjects)} subjects with seed {args.seed}: {', '.join(sorted(subjects))}")

    for source in sources:
        destination = args.output_dir / source.name
        scanned, written = filter_file(source, destination, subjects)
        print(f"{source.name}: retained {written:,} / {scanned:,} rows")

    print(f"Created compressed subset in {args.output_dir}")


if __name__ == "__main__":
    main()

