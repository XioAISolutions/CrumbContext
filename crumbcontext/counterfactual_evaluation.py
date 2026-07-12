from __future__ import annotations

import json
from difflib import SequenceMatcher

from .counterfactual_models import EvaluationSpec, ResponseEvaluation, RunRecord
from .counterfactual_payloads import sha256_text
from .providers import ProviderRequest, ProviderResponse


def evaluate_response(
    text: str,
    evaluation: EvaluationSpec,
    fallback_exact: tuple[str, ...],
) -> ResponseEvaluation:
    expected_exact = evaluation.expected_exact or fallback_exact
    exact_found = sum(1 for value in expected_exact if value in text)
    required_found = sum(
        1
        for value in evaluation.required_substrings
        if value.casefold() in text.casefold()
    )
    json_valid = True
    if evaluation.expect_json:
        try:
            json.loads(text)
        except json.JSONDecodeError:
            json_valid = False
    exact_recall = 1.0 if not expected_exact else exact_found / len(expected_exact)
    required_recall = (
        1.0
        if not evaluation.required_substrings
        else required_found / len(evaluation.required_substrings)
    )
    return ResponseEvaluation(
        json_valid=json_valid,
        exact_expected=len(expected_exact),
        exact_found=exact_found,
        exact_recall=round(exact_recall, 4),
        required_expected=len(evaluation.required_substrings),
        required_found=required_found,
        required_recall=round(required_recall, 4),
        task_complete=json_valid and exact_recall == 1.0 and required_recall == 1.0,
    )


def record_run(
    request: ProviderRequest,
    response: ProviderResponse,
    evaluation: EvaluationSpec,
    fallback_exact: tuple[str, ...],
) -> RunRecord:
    return RunRecord(
        request_sha256=request.sha256,
        response_sha256=sha256_text(response.text),
        request=request.to_dict(),
        response=response.to_dict(),
        evaluation=evaluate_response(response.text, evaluation, fallback_exact),
    )


def reduction(before: int, after: int) -> float:
    if before <= 0:
        return 0.0
    return round(max(0.0, 1 - (after / before)) * 100, 1)


def similarity(left: str, right: str) -> float:
    return round(SequenceMatcher(None, left, right).ratio(), 4)
