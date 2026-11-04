#!/usr/bin/env python3
"""Create deterministic, patient-consistent MIMIC-IV and Note subsets."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
import shutil
from pathlib import Path


def read_subject_ids(path: Path, count: int, seed: int) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        ids = sorted(row["subject_id"] for row in reader if row.get("subject_id"))
    if len(ids) < count:
        raise ValueError(f"{path} contains only {len(ids)} subjects; requested {count}")
    random.Random(seed).shuffle(ids)
    return sorted(ids[:count])


def filter_csv(source: Path, destination: Path, subjects: set[str]) -> tuple[int, int]:
    with gzip.open(source, "rt", encoding="utf-8", newline="") as src:
        reader = csv.reader(src)
        header = next(reader)
        normalized = [column.strip().lower() for column in header]
        subject_index = normalized.index("subject_id") if "subject_id" in normalized else None
        destination.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(destination, "wt", encoding="utf-8", newline="") as dst:
            writer = csv.writer(dst, lineterminator="\n")
            writer.writerow(header)
            scanned = written = 0
            for row in reader:
                scanned += 1
                if subject_index is None or (subject_index < len(row) and row[subject_index] in subjects):
                    writer.writerow(row)
                    written += 1
    return scanned, written


def process_tree(source_root: Path, output_root: Path, subjects: set[str]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for source in sorted(source_root.rglob("*.csv.gz")):
        relative = source.relative_to(source_root)
        destination = output_root / relative
        scanned, written = filter_csv(source, destination, subjects)
        counts[str(relative)] = {"scanned": scanned, "written": written}
        print(f"{relative}: retained {written:,} / {scanned:,} rows", flush=True)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mimiciv-dir", type=Path, required=True)
    parser.add_argument("--note-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--num-subjects", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.num_subjects <= 0:
        parser.error("--num-subjects must be positive")
    for source in (args.mimiciv_dir, args.note_dir):
        if not source.is_dir():
            parser.error(f"source directory does not exist: {source}")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.force:
        parser.error(f"output directory is not empty: {args.output_dir}; use --force")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    patients = args.mimiciv_dir / "hosp" / "patients.csv.gz"
    if not patients.exists():
        parser.error(f"missing patients table: {patients}")
    selected = read_subject_ids(patients, args.num_subjects, args.seed)
    subjects = set(selected)
    print(f"Selected {len(selected)} subjects with seed {args.seed}", flush=True)

    mimic_counts = process_tree(args.mimiciv_dir, args.output_dir / "mimiciv", subjects)
    note_counts = process_tree(args.note_dir, args.output_dir / "note", subjects)
    manifest = {
        "dataset": "mimic-iv-and-note",
        "num_subjects": len(selected),
        "seed": args.seed,
        "subject_ids": selected,
        "mimiciv_counts": mimic_counts,
        "note_counts": note_counts,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created subset in {args.output_dir}")


if __name__ == "__main__":
    main()
