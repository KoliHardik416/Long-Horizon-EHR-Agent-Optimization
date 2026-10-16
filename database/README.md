# MIMIC database loaders

This directory contains the upstream MIMIC database-building assets. It is
kept separate from the project retrieval and agent code.

```text
database/
├── mimic-iv/       structured hospital and ICU CSV loaders, concepts, tests
├── mimic-iv-note/  clinical-note CSV loaders for PostgreSQL
└── archive/        alternative backend loaders retained for future use
```

The two datasets can be loaded into the same PostgreSQL database:

- `mimic-iv` creates `mimiciv_hosp`, `mimiciv_icu`, and `mimiciv_derived`.
- `mimic-iv-note` creates `mimiciv_note`.

The relative paths inside the upstream scripts remain unchanged because each
dataset directory retains its original internal layout. Start with the
project-level instructions in `baseline_postgres/README.md`.

The archived directories are:

```text
archive/mimic-iv-buildmimic-duckdb
archive/mimic-iv-buildmimic-bigquery
archive/mimic-iv-buildmimic-mysql
archive/mimic-iv-buildmimic-sqlite
archive/mimic-iv-concepts-duckdb
archive/mimic-iv-note-buildmimic-duckdb
archive/mimic-iv-note-buildmimic-bigquery
```

They contain loaders and dialect-specific SQL, not additional copies of the
MIMIC patient data. The active PostgreSQL loader paths are unchanged within
`mimic-iv/` and `mimic-iv-note/`.

If a flat MIMIC-IV download contains all structured `.csv.gz` files in one
directory, use `prepare_mimic_iv.sh` to create the expected `hosp/` and `icu/`
folders and decompress the files without changing the original download:

```bash
database/prepare_mimic_iv.sh /path/to/flat-mimiciv /path/to/mimiciv
```

The current flat download appears to be MIMIC-III. Prepare it separately with:

```bash
database/prepare_mimic_iii.sh flat_input /path/to/mimiciii
```

Do not pass the resulting directory to the MIMIC-IV PostgreSQL loader. MIMIC-III
has different table names and schemas, including `noteevents`, `inputevents_cv`,
and `inputevents_mv`.

To create a small patient-consistent compressed subset for development:

```bash
python database/subset_mimic_iii.py \
  --input-dir /path/to/flat_input \
  --output-dir /path/to/mimiciii_subset \
  --num-subjects 15 \
  --seed 42
```

The output retains the official flat uppercase filenames and can be passed to
the MIMIC-III `make mimic-gz` PostgreSQL loader. The full input directory is
never modified.
