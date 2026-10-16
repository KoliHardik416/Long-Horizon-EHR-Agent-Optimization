"""Check that the MIMIC schemas required by the baseline are available."""

from __future__ import annotations

from .retrieval import PostgresRetriever


REQUIRED = (
    ("mimiciv_hosp", "patients"),
    ("mimiciv_hosp", "admissions"),
    ("mimiciv_hosp", "labevents"),
    ("mimiciv_hosp", "diagnoses_icd"),
    ("mimiciv_hosp", "prescriptions"),
    ("mimiciv_hosp", "procedures_icd"),
    ("mimiciv_hosp", "d_labitems"),
    ("mimiciv_icu", "icustays"),
)


def main() -> None:
    db = PostgresRetriever()
    with db._connect() as conn, conn.cursor() as cur:
        for schema, table in REQUIRED:
            cur.execute("""
                SELECT to_regclass(%s) IS NOT NULL AS present,
                       COALESCE((SELECT reltuples::bigint FROM pg_class
                                 WHERE oid = to_regclass(%s)), 0) AS estimate
            """, (f"{schema}.{table}", f"{schema}.{table}"))
            row = cur.fetchone()
            status = "OK" if row["present"] else "MISSING"
            print(f"{status:7} {schema}.{table} (estimated rows: {row['estimate']})")


if __name__ == "__main__":
    main()

