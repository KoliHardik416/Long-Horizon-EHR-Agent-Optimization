"""MIMIC-III structured retrieval against the ``mimiciii`` schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .connection import connect


class MIMICIIIRetriever:
    """Allow-listed, read-only MIMIC-III retrieval operations."""

    def __init__(self, conninfo: str | None = None):
        self.conninfo = conninfo

    @staticmethod
    def _rows(cursor) -> list[dict[str, Any]]:
        return [dict(row) for row in cursor.fetchall()]

    def patient_context(self, subject_id: int) -> dict[str, Any]:
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT subject_id, gender, dob, dod, dod_hosp, dod_ssn,
                       expire_flag
                FROM mimiciii.patients WHERE subject_id = %s
            """, (subject_id,))
            patient = cur.fetchone()
            cur.execute("""
                SELECT hadm_id, admittime, dischtime, deathtime,
                       admission_type, admission_location, discharge_location,
                       insurance, language, religion, marital_status,
                       ethnicity AS race,
                       hospital_expire_flag
                FROM mimiciii.admissions
                WHERE subject_id = %s ORDER BY admittime
            """, (subject_id,))
            admissions = self._rows(cur)
            cur.execute("""
                SELECT icustay_id, hadm_id, dbsource, first_careunit,
                       last_careunit, intime, outtime, los
                FROM mimiciii.icustays
                WHERE subject_id = %s ORDER BY intime
            """, (subject_id,))
            icu_stays = self._rows(cur)
        return {"patient": dict(patient) if patient else None,
                "admissions": admissions, "icu_stays": icu_stays}

    def labs(self, subject_id: int, hadm_id: int | None = None,
             start: datetime | None = None, end: datetime | None = None,
             itemids: list[int] | None = None, limit: int = 500) -> list[dict[str, Any]]:
        clauses = ["l.subject_id = %s"]
        params: list[Any] = [subject_id]
        if hadm_id is not None: clauses.append("l.hadm_id = %s"); params.append(hadm_id)
        if start is not None: clauses.append("l.charttime >= %s"); params.append(start)
        if end is not None: clauses.append("l.charttime < %s"); params.append(end)
        if itemids: clauses.append("l.itemid = ANY(%s)"); params.append(itemids)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT l.row_id, l.subject_id, l.hadm_id, l.charttime,
                       l.itemid, d.label, d.fluid, l.value, l.valuenum,
                       l.valueuom, l.flag
                FROM mimiciii.labevents l
                LEFT JOIN mimiciii.d_labitems d ON d.itemid = l.itemid
                WHERE {' AND '.join(clauses)}
                ORDER BY l.charttime NULLS LAST, l.row_id LIMIT %s
            """, params)
            return self._rows(cur)

    def diagnoses(self, subject_id: int, hadm_id: int | None = None,
                  limit: int = 200) -> list[dict[str, Any]]:
        clauses = ["d.subject_id = %s"]; params: list[Any] = [subject_id]
        if hadm_id is not None: clauses.append("d.hadm_id = %s"); params.append(hadm_id)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT d.row_id, d.subject_id, d.hadm_id, d.seq_num,
                       d.icd9_code, ref.short_title, ref.long_title
                FROM mimiciii.diagnoses_icd d
                LEFT JOIN mimiciii.d_icd_diagnoses ref ON ref.icd9_code = d.icd9_code
                WHERE {' AND '.join(clauses)}
                ORDER BY d.hadm_id, d.seq_num LIMIT %s
            """, params)
            return self._rows(cur)

    def medications(self, subject_id: int, hadm_id: int | None = None,
                    limit: int = 500) -> list[dict[str, Any]]:
        clauses = ["subject_id = %s"]; params: list[Any] = [subject_id]
        if hadm_id is not None: clauses.append("hadm_id = %s"); params.append(hadm_id)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT row_id, subject_id, hadm_id, icustay_id, startdate,
                       enddate, drug, drug_type, dose_val_rx, dose_unit_rx,
                       route
                FROM mimiciii.prescriptions
                WHERE {' AND '.join(clauses)}
                ORDER BY startdate NULLS LAST LIMIT %s
            """, params)
            return self._rows(cur)

    def procedures(self, subject_id: int, hadm_id: int | None = None,
                   limit: int = 200) -> list[dict[str, Any]]:
        clauses = ["p.subject_id = %s"]; params: list[Any] = [subject_id]
        if hadm_id is not None: clauses.append("p.hadm_id = %s"); params.append(hadm_id)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT p.row_id, p.subject_id, p.hadm_id, p.seq_num,
                       p.icd9_code, ref.short_title, ref.long_title
                FROM mimiciii.procedures_icd p
                LEFT JOIN mimiciii.d_icd_procedures ref ON ref.icd9_code = p.icd9_code
                WHERE {' AND '.join(clauses)}
                ORDER BY p.hadm_id, p.seq_num LIMIT %s
            """, params)
            return self._rows(cur)

