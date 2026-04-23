from __future__ import annotations

import json
import os
import re

from openai import OpenAI

from app.schemas import TenderSummary


JSON_SCHEMA = {
    "name": "tender_extraction",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "company_details": {"type": "array", "items": {"type": "string"}},
            "payment_terms": {"type": "array", "items": {"type": "string"}},
            "compliance_requirements": {"type": "array", "items": {"type": "string"}},
            "service_scope": {"type": "array", "items": {"type": "string"}},
            "submission_formats": {"type": "array", "items": {"type": "string"}},
            "needs_human_review": {"type": "array", "items": {"type": "string"}},
            "final_output": {"type": "string"},
        },
        "required": [
            "company_details",
            "payment_terms",
            "compliance_requirements",
            "service_scope",
            "submission_formats",
            "needs_human_review",
            "final_output",
        ],
    },
    "strict": True,
}


KEYWORDS = {
    "company_details": ["company", "registration", "tax", "profile"],
    "payment_terms": ["payment", "invoice", "currency", "terms"],
    "compliance_requirements": ["compliance", "certificate", "license", "mandatory"],
    "service_scope": ["scope", "deliverables", "services", "work"],
    "submission_formats": ["submission", "deadline", "format", "envelope"],
}


def _extract_lines(text: str, keywords: list[str]) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    matches: list[str] = []
    for ln in lines:
        low = ln.lower()
        if any(k in low for k in keywords):
            matches.append(ln)
    return matches[:10]


def _fallback_extract(document_text: str, ingest_notes: list[str]) -> tuple[TenderSummary, list[str], str, list[str]]:
    compact = re.sub(r"\s+", " ", document_text)
    summary = TenderSummary(
        company_details=_extract_lines(document_text, KEYWORDS["company_details"]),
        payment_terms=_extract_lines(document_text, KEYWORDS["payment_terms"]),
        compliance_requirements=_extract_lines(document_text, KEYWORDS["compliance_requirements"]),
        service_scope=_extract_lines(document_text, KEYWORDS["service_scope"]),
        submission_formats=_extract_lines(document_text, KEYWORDS["submission_formats"]),
        notes=ingest_notes + ["Fallback extraction used because OpenAI response was unavailable."],
    )
    needs_review = [
        "Validate compliance and mandatory clauses from source document.",
        "Confirm submission deadlines and contact channels.",
    ]
    final_output = compact[:1400]
    return summary, needs_review, final_output, summary.notes


def extract_with_openai(document_text: str, organization: str, ingest_notes: list[str]) -> tuple[TenderSummary, list[str], str, list[str]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    if not api_key:
        return _fallback_extract(document_text, ingest_notes + ["OPENAI_API_KEY not set."])

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract tender requirements into structured fields. "
                        "Return strictly valid JSON that matches schema."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Organization: {organization}\n\n"
                        "Extract the tender content below and produce concise bullet-like strings:\n\n"
                        f"{document_text[:30000]}"
                    ),
                },
            ],
        )

        parsed = json.loads(response.choices[0].message.content or "{}")
        summary = TenderSummary(
            company_details=parsed.get("company_details", []),
            payment_terms=parsed.get("payment_terms", []),
            compliance_requirements=parsed.get("compliance_requirements", []),
            service_scope=parsed.get("service_scope", []),
            submission_formats=parsed.get("submission_formats", []),
            notes=ingest_notes + ["OpenAI structured extraction completed."],
        )
        needs_review = parsed.get("needs_human_review", [])
        final_output = parsed.get("final_output", "")
        return summary, needs_review, final_output, summary.notes
    except Exception as exc:
        return _fallback_extract(document_text, ingest_notes + [f"OpenAI extraction failed: {exc}"])
