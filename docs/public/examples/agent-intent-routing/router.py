"""Synthetic routing-policy exercise. No model inference or real business writes."""
import math

INTENTS = {"refund", "invoice", "delivery", "policy", "human", "unknown"}
READ_ROUTES = {"invoice": "invoice_flow", "delivery": "delivery_flow", "policy": "knowledge_answer"}
VERSION = "router-v1"


def route(request):
    context = request["context"]
    prediction = request["prediction"]
    if context.get("security_block"):
        return "security_review"
    if context.get("explicit_human"):
        return "human_queue"
    if prediction.get("status") != "ok":
        return "human_queue"
    candidates = prediction.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return "human_queue"
    seen = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            return "human_queue"
        label, score = candidate.get("intent"), candidate.get("score")
        if not isinstance(label, str) or label not in INTENTS or label in seen:
            return "human_queue"
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
            return "human_queue"
        seen.add(label)
    candidates = sorted(candidates, key=lambda item: item["score"], reverse=True)
    label, score = candidates[0]["intent"], candidates[0]["score"]
    if label == "unknown":
        return "out_of_scope"
    if label == "human":
        return "human_queue"
    if score < 0.80:
        return "clarify_intent"
    if len(candidates) > 1 and score - candidates[1]["score"] < 0.15:
        return "clarify_intent"
    if context.get("domain") not in {"retail", "delivery"}:
        return "clarify_domain"
    if context.get("multiple_goals"):
        return "clarify_order_of_tasks"
    if label in READ_ROUTES:
        return READ_ROUTES[label]
    if not context.get("order_id"):
        return "collect_order"
    if not context.get("authenticated"):
        return "authenticate"
    if not context.get("owns_order"):
        return "deny_access"
    if not context.get("eligible"):
        return "explain_ineligible"
    operation = {
        "intent": "refund",
        "order_id": context["order_id"],
        "amount_cents": context["amount_cents"],
        "currency": context["currency"],
        "state_version": context["state_version"],
    }
    confirmation = context.get("confirmation", {})
    if confirmation.get("operation") != operation or confirmation.get("expires_at", 0) <= context["now"]:
        return "confirm_refund"
    return "refund_ready"
