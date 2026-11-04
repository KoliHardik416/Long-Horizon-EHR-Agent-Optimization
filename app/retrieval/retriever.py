"""Allow-listed, read-only retrieval functions for structured MIMIC-IV data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .connection import connect


class StructuredRetriever:
    """Query structured MIMIC-IV tables without exposing arbitrary SQL."""

    def __init__(self, conninfo: str | None = None):
        self.conninfo = conninfo

    @staticmethod
    def _rows(cursor) -> list[dict[str, Any]]:
        return [dict(row) for row in cursor.fetchall()]

    def patient_context(self, subject_id: int) -> dict[str, Any]:
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT subject_id, gender, anchor_age, anchor_year,
                       anchor_year_group, dod
                FROM mimiciv_hosp.patients
                WHERE subject_id = %s
            """, (subject_id,))
            patient = cur.fetchone()
            cur.execute("""
                SELECT hadm_id, admittime, dischtime, deathtime,
                       admission_type, admission_location, discharge_location,
                       hospital_expire_flag
                FROM mimiciv_hosp.admissions
                WHERE subject_id = %s
                ORDER BY admittime
            """, (subject_id,))
            admissions = self._rows(cur)
            cur.execute("""
                SELECT stay_id, hadm_id, intime, outtime,
                       first_careunit, last_careunit
                FROM mimiciv_icu.icustays
                WHERE subject_id = %s
                ORDER BY intime
            """, (subject_id,))
            icu_stays = self._rows(cur)
        return {"patient": dict(patient) if patient else None,
                "admissions": admissions, "icu_stays": icu_stays}

    def admissions(self, subject_id: int, hadm_id: int | None = None,
                   limit: int = 100) -> list[dict[str, Any]]:
        clauses = ["subject_id = %s"]
        params: list[Any] = [subject_id]
        if hadm_id is not None:
            clauses.append("hadm_id = %s")
            params.append(hadm_id)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT hadm_id, subject_id, admittime, dischtime, deathtime,
                       admission_type, admission_location, discharge_location,
                       hospital_expire_flag
                FROM mimiciv_hosp.admissions
                WHERE {' AND '.join(clauses)}
                ORDER BY admittime
                LIMIT %s
            """, params)
            return self._rows(cur)

    def notes(self, subject_id: int, hadm_id: int | None = None,
              limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve bounded discharge and radiology notes from MIMIC-IV-Note."""
        clauses = ["subject_id = %s"]
        params: list[Any] = [subject_id]
        if hadm_id is not None:
            clauses.append("hadm_id = %s")
            params.append(hadm_id)
        rows: list[dict[str, Any]] = []
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            for table in ("mimiciv_note.discharge", "mimiciv_note.radiology"):
                cur.execute(f"""
                    SELECT note_id, subject_id, hadm_id, note_type,
                           charttime, storetime, text
                    FROM {table}
                    WHERE {' AND '.join(clauses)}
                    ORDER BY charttime NULLS LAST, note_id
                    LIMIT %s
                """, [*params, limit])
                rows.extend({"source": table, **row} for row in self._rows(cur))
        return sorted(rows, key=lambda row: (row.get("charttime") is None, row.get("charttime")))[:limit]

    def labs(self, subject_id: int, hadm_id: int | None = None,
             start: datetime | None = None, end: datetime | None = None,
             itemids: list[int] | None = None, limit: int = 500) -> list[dict[str, Any]]:
        clauses = ["l.subject_id = %s"]
        params: list[Any] = [subject_id]
        if hadm_id is not None:
            clauses.append("l.hadm_id = %s"); params.append(hadm_id)
        if start is not None:
            clauses.append("l.charttime >= %s"); params.append(start)
        if end is not None:
            clauses.append("l.charttime < %s"); params.append(end)
        if itemids:
            clauses.append("l.itemid = ANY(%s)"); params.append(itemids)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT l.labevent_id, l.subject_id, l.hadm_id, l.charttime,
                       l.itemid, d.label, d.fluid, l.value, l.valuenum,
                       l.valueuom, l.ref_range_lower, l.ref_range_upper, l.flag
                FROM mimiciv_hosp.labevents l
                LEFT JOIN mimiciv_hosp.d_labitems d ON d.itemid = l.itemid
                WHERE {' AND '.join(clauses)}
                ORDER BY l.charttime NULLS LAST, l.labevent_id
                LIMIT %s
            """, params)
            return self._rows(cur)

    def diagnoses(self, subject_id: int, hadm_id: int | None = None,
                  limit: int = 200) -> list[dict[str, Any]]:
        clauses = ["d.subject_id = %s"]
        params: list[Any] = [subject_id]
        if hadm_id is not None:
            clauses.append("d.hadm_id = %s"); params.append(hadm_id)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT d.subject_id, d.hadm_id, d.seq_num, d.icd_code,
                       d.icd_version, ref.long_title
                FROM mimiciv_hosp.diagnoses_icd d
                LEFT JOIN mimiciv_hosp.d_icd_diagnoses ref
                  ON ref.icd_code = d.icd_code
                 AND ref.icd_version = d.icd_version
                WHERE {' AND '.join(clauses)}
                ORDER BY d.hadm_id, d.seq_num
                LIMIT %s
            """, params)
            return self._rows(cur)

    def medications(self, subject_id: int, hadm_id: int | None = None,
                    limit: int = 500) -> list[dict[str, Any]]:
        clauses = ["subject_id = %s"]
        params: list[Any] = [subject_id]
        if hadm_id is not None:
            clauses.append("hadm_id = %s"); params.append(hadm_id)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT subject_id, hadm_id, pharmacy_id, starttime, stoptime,
                       drug, drug_type, dose_val_rx, dose_unit_rx, route
                FROM mimiciv_hosp.prescriptions
                WHERE {' AND '.join(clauses)}
                ORDER BY starttime NULLS LAST
                LIMIT %s
            """, params)
            return self._rows(cur)

    def procedures(self, subject_id: int, hadm_id: int | None = None,
                   limit: int = 200) -> list[dict[str, Any]]:
        clauses = ["p.subject_id = %s"]
        params: list[Any] = [subject_id]
        if hadm_id is not None:
            clauses.append("p.hadm_id = %s"); params.append(hadm_id)
        params.append(limit)
        with connect(self.conninfo) as conn, conn.cursor() as cur:
            cur.execute(f"""
                SELECT p.subject_id, p.hadm_id, p.seq_num, p.chartdate,
                       p.icd_code, p.icd_version, ref.long_title
                FROM mimiciv_hosp.procedures_icd p
                LEFT JOIN mimiciv_hosp.d_icd_procedures ref
                  ON ref.icd_code = p.icd_code
                 AND ref.icd_version = p.icd_version
                WHERE {' AND '.join(clauses)}
                ORDER BY p.chartdate NULLS LAST, p.seq_num
                LIMIT %s
            """, params)
            return self._rows(cur)

