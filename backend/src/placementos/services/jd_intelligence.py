"""Evidence-backed JD interpretation and typed policy compilation for P04."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from placementos.core.errors import BadRequestException
from placementos.models.storage import TextExtraction


def canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class InterpretationDraft:
    facts: dict[str, Any]
    evidence: list[dict[str, Any]]
    clarifications: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    usage: dict[str, Any]


class ModelInterpreter(Protocol):
    adapter_id: str
    prompt_version: str

    def interpret(self, extraction: TextExtraction) -> InterpretationDraft: ...


class DeterministicFixtureJDInterpreter:
    """Visible development fixture that emulates structured model output deterministically."""

    adapter_id = "deterministic-fixture-v1"
    prompt_version = "jd-interpretation-v1"
    INJECTION_PATTERNS = (
        "ignore previous instructions",
        "system prompt",
        "call a tool",
        "send email",
        "change permissions",
    )

    @staticmethod
    def _match(pattern: str, text: str, flags: int = re.IGNORECASE) -> re.Match[str] | None:
        return re.search(pattern, text, flags)

    @staticmethod
    def _evidence(
        extraction: TextExtraction, field_path: str, match: re.Match[str]
    ) -> dict[str, Any]:
        start, end = match.span()
        locator = next(
            (
                item
                for item in extraction.locators
                if item.get("char_offset_start", 0) <= start
                and item.get("char_offset_end", 0) >= min(end, len(extraction.extracted_text))
            ),
            None,
        )
        if locator is None:
            locator = min(
                extraction.locators,
                key=lambda item: abs(item.get("char_offset_start", 0) - start),
                default={"locator_type": "paragraph", "paragraph_index": 0},
            )
        excerpt = extraction.extracted_text[start:end].strip() or match.group(0).strip()
        return {
            "field_path": field_path,
            "locator_type": locator.get("locator_type", "paragraph"),
            "page_number": locator.get("page_number"),
            "paragraph_index": locator.get("paragraph_index", 0),
            "char_offset_start": start,
            "char_offset_end": end,
            "excerpt": excerpt[:500],
        }

    def interpret(self, extraction: TextExtraction) -> InterpretationDraft:
        text = extraction.extracted_text
        lower = text.lower()
        facts: dict[str, Any] = {
            "company_name": None,
            "role_title": None,
            "employment_type": None,
            "location": None,
            "work_mode": None,
            "compensation": {"source_wording": None},
            "eligibility_draft": {
                "allowed_branches": None,
                "minimum_cgpa": None,
                "cgpa_scale": None,
                "graduation_years": None,
                "maximum_active_backlogs": None,
            },
            "registration_deadline": {
                "source_date": None,
                "confirmed_instant": None,
                "timezone": None,
            },
            "document_requirements": [],
            "selection_process": [],
        }
        evidence: list[dict[str, Any]] = []
        clarifications: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []

        company = self._match(r"(?:company|organization)\s*[:\-]\s*([^\n]{2,120})", text)
        if company:
            facts["company_name"] = company.group(1).strip()
            evidence.append(self._evidence(extraction, "company_name", company))

        role = self._match(r"(?:role|position|job title)\s*[:\-]\s*([^\n]{2,120})", text)
        if role:
            facts["role_title"] = role.group(1).strip()
            evidence.append(self._evidence(extraction, "role_title", role))

        branch_aliases = {
            "CSE": ("cse", "computer science"),
            "IT": ("information technology", "\bit\b"),
            "ECE": ("ece", "electronics and communication"),
            "EEE": ("eee", "electrical and electronics"),
            "ME": ("mechanical",),
            "CE": ("civil",),
        }
        branches = [
            code
            for code, aliases in branch_aliases.items()
            if any(re.search(alias, lower) for alias in aliases)
        ]
        if branches:
            facts["eligibility_draft"]["allowed_branches"] = sorted(set(branches))
            branch_match = self._match(r"[^\n]*(?:branch|cse|computer science|information technology)[^\n]*", text)
            if branch_match:
                evidence.append(self._evidence(extraction, "eligibility_draft.allowed_branches", branch_match))

        cgpa_matches = list(
            re.finditer(
                r"(?:minimum|min\.?|at least|required)?\s*(?:cgpa|gpa)\s*(?:of|:|>=|is)?\s*(\d+(?:\.\d+)?)\s*(?:out of|/)?\s*(\d+(?:\.\d+)?)?",
                text,
                re.IGNORECASE,
            )
        )
        cgpa_values = {match.group(1) for match in cgpa_matches}
        if len(cgpa_values) == 1:
            chosen = cgpa_matches[0]
            facts["eligibility_draft"]["minimum_cgpa"] = str(Decimal(chosen.group(1)).quantize(Decimal("0.01")))
            facts["eligibility_draft"]["cgpa_scale"] = str(
                Decimal(chosen.group(2) or "10").quantize(Decimal("0.01"))
            )
            evidence.append(self._evidence(extraction, "eligibility_draft.minimum_cgpa", chosen))
        elif len(cgpa_values) > 1:
            clarifications.append(
                {
                    "field_path": "eligibility_draft.minimum_cgpa",
                    "question": f"Conflicting CGPA thresholds found: {', '.join(sorted(cgpa_values))}. Confirm the authoritative threshold.",
                    "reason_code": "CONFLICTING_CGPA",
                    "blocking": True,
                }
            )

        cohort_fragments = re.findall(
            r"[^\n]*(?:graduat(?:ing|ion)?|batch|cohort)[^\n]*",
            text,
            re.IGNORECASE,
        )
        years = sorted(
            {
                int(value)
                for fragment in cohort_fragments
                for value in re.findall(r"\b(20\d{2})\b", fragment)
                if 2020 <= int(value) <= 2100
            }
        )
        if years:
            facts["eligibility_draft"]["graduation_years"] = years
            year_match = self._match(r"[^\n]*(?:graduat|batch|cohort)[^\n]*20\d{2}[^\n]*", text)
            if year_match:
                evidence.append(self._evidence(extraction, "eligibility_draft.graduation_years", year_match))

        backlog = self._match(r"(?:maximum|max\.?|up to)?\s*(\d+|no)\s+(?:active |current )?backlogs?", text)
        if backlog:
            raw = backlog.group(1).lower()
            facts["eligibility_draft"]["maximum_active_backlogs"] = 0 if raw == "no" else int(raw)
            evidence.append(self._evidence(extraction, "eligibility_draft.maximum_active_backlogs", backlog))

        date_match = self._match(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if date_match:
            facts["registration_deadline"]["source_date"] = date_match.group(1)
            evidence.append(self._evidence(extraction, "registration_deadline.source_date", date_match))
            clarifications.append(
                {
                    "field_path": "registration_deadline.confirmed_instant",
                    "question": "Confirm the registration cutoff time and IANA timezone; the source provides only a date.",
                    "reason_code": "DEADLINE_TIMEZONE_MISSING",
                    "blocking": True,
                }
            )

        compensation = self._match(r"[^\n]*(?:ctc|lpa|salary|stipend|compensation)[^\n]*", text)
        if compensation:
            facts["compensation"]["source_wording"] = compensation.group(0).strip()
            evidence.append(self._evidence(extraction, "compensation.source_wording", compensation))

        for document_name in ("resume", "marksheet", "college id", "college-id"):
            if document_name in lower:
                facts["document_requirements"].append(document_name.replace("college-id", "college_id").replace(" ", "_"))

        if re.search(r"(?:10th|12th|percentage|diploma score)", lower):
            clarifications.append(
                {
                    "field_path": "eligibility_draft.unsupported_criterion",
                    "question": "The source contains an academic criterion not modeled by eligibility-v1. Clarify or explicitly defer it.",
                    "reason_code": "UNSUPPORTED_CRITERION",
                    "blocking": True,
                }
            )

        injection_signals = [pattern for pattern in self.INJECTION_PATTERNS if pattern in lower]
        if injection_signals:
            findings.append(
                {
                    "code": "UNTRUSTED_INSTRUCTION_IGNORED",
                    "severity": "warning",
                    "signals": injection_signals,
                    "message": "Instruction-like source content was treated as data and had no tool or approval authority.",
                }
            )

        for field_path, value in (
            ("eligibility_draft.allowed_branches", facts["eligibility_draft"]["allowed_branches"]),
            ("eligibility_draft.minimum_cgpa", facts["eligibility_draft"]["minimum_cgpa"]),
            ("eligibility_draft.graduation_years", facts["eligibility_draft"]["graduation_years"]),
            ("eligibility_draft.maximum_active_backlogs", facts["eligibility_draft"]["maximum_active_backlogs"]),
        ):
            if value is None and not any(item["field_path"] == field_path for item in clarifications):
                clarifications.append(
                    {
                        "field_path": field_path,
                        "question": f"Confirm {field_path.replace('_', ' ').replace('.', ' / ')} or mark it explicitly not required.",
                        "reason_code": "MATERIAL_FIELD_UNRESOLVED",
                        "blocking": True,
                    }
                )

        return InterpretationDraft(
            facts=facts,
            evidence=evidence,
            clarifications=clarifications,
            findings=findings,
            usage={"provider": "fixture", "calls": 1, "repair_attempts": 0, "input_characters": len(text)},
        )


def validate_evidence(extraction: TextExtraction, evidence: list[dict[str, Any]]) -> None:
    valid_locator_pairs = {
        (item.get("locator_type"), item.get("page_number"), item.get("paragraph_index"))
        for item in extraction.locators
    }
    for item in evidence:
        if item.get("locator_type") == "human_correction":
            continue
        pair = (item.get("locator_type"), item.get("page_number"), item.get("paragraph_index"))
        if pair not in valid_locator_pairs:
            raise BadRequestException(
                "Interpretation evidence references an unknown source locator",
                details={"field_path": item.get("field_path")},
            )
        excerpt = str(item.get("excerpt", "")).strip()
        if not excerpt or excerpt not in extraction.extracted_text:
            raise BadRequestException(
                "Interpretation evidence excerpt is not present in the extracted source",
                details={"field_path": item.get("field_path")},
            )


def get_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def set_path(payload: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    allowed_roots = {
        "company_name", "role_title", "employment_type", "location", "work_mode",
        "compensation", "eligibility_draft", "registration_deadline", "document_requirements",
        "selection_process",
    }
    segments = path.split(".")
    if not segments or segments[0] not in allowed_roots or any(not part for part in segments):
        raise BadRequestException("Unsupported interpretation field path")
    updated = copy.deepcopy(payload)
    current: dict[str, Any] = updated
    for segment in segments[:-1]:
        child = current.get(segment)
        if child is None:
            child = {}
            current[segment] = child
        if not isinstance(child, dict):
            raise BadRequestException("Field path traverses a non-object value")
        current = child
    current[segments[-1]] = value
    return updated


def compile_policy(
    reviewed_facts: dict[str, Any],
    *,
    interpretation_id: str,
    explicitly_not_required: set[str],
) -> tuple[dict[str, Any], str]:
    eligibility = reviewed_facts.get("eligibility_draft") or {}
    payload: dict[str, Any] = {
        "schema_version": 1,
        "engine_contract": "eligibility-v1",
        "aggregation": "required_unknown_first_then_failure",
        "evidence_revision": interpretation_id,
    }

    branches = eligibility.get("allowed_branches")
    if "branch" in explicitly_not_required:
        payload["branch"] = {"mode": "not_required"}
    elif isinstance(branches, list) and branches:
        payload["branch"] = {"mode": "required", "operator": "in", "values": sorted(set(branches))}
    else:
        raise BadRequestException("Branch scope is unresolved; confirm it or mark it explicitly not required")

    minimum = eligibility.get("minimum_cgpa")
    scale = eligibility.get("cgpa_scale")
    if "cgpa" in explicitly_not_required:
        payload["cgpa"] = {"mode": "not_required"}
    else:
        try:
            min_decimal = Decimal(str(minimum))
            scale_decimal = Decimal(str(scale))
        except (InvalidOperation, TypeError):
            raise BadRequestException("CGPA threshold and scale must be exact decimal values") from None
        if min_decimal < 0 or scale_decimal <= 0 or min_decimal > scale_decimal:
            raise BadRequestException("CGPA threshold is outside the configured scale")
        payload["cgpa"] = {
            "mode": "required", "operator": "gte",
            "minimum": f"{min_decimal:.2f}", "scale": f"{scale_decimal:.2f}",
        }

    years = eligibility.get("graduation_years")
    if "graduation_year" in explicitly_not_required:
        payload["graduation_year"] = {"mode": "not_required"}
    elif isinstance(years, list) and years and all(isinstance(year, int) and 2020 <= year <= 2100 for year in years):
        payload["graduation_year"] = {"mode": "required", "operator": "in", "values": sorted(set(years))}
    else:
        raise BadRequestException("Graduation cohort is unresolved or invalid")

    backlogs = eligibility.get("maximum_active_backlogs")
    if "active_backlogs" in explicitly_not_required:
        payload["active_backlogs"] = {"mode": "not_required"}
    elif isinstance(backlogs, int) and backlogs >= 0:
        payload["active_backlogs"] = {"mode": "required", "operator": "lte", "maximum": backlogs}
    else:
        raise BadRequestException("Active backlog rule is unresolved or invalid")

    required = [name for name in ("branch", "cgpa", "graduation_year", "active_backlogs") if payload[name]["mode"] == "required"]
    if not required:
        raise BadRequestException("At least one supported academic predicate must be required")
    summary_parts = []
    if payload["branch"]["mode"] == "required":
        summary_parts.append("branches " + ", ".join(payload["branch"]["values"]))
    if payload["cgpa"]["mode"] == "required":
        summary_parts.append(f"CGPA >= {payload['cgpa']['minimum']} / {payload['cgpa']['scale']}")
    if payload["graduation_year"]["mode"] == "required":
        summary_parts.append("graduation years " + ", ".join(map(str, payload["graduation_year"]["values"])))
    if payload["active_backlogs"]["mode"] == "required":
        summary_parts.append(f"active backlogs <= {payload['active_backlogs']['maximum']}")
    return payload, "; ".join(summary_parts)
