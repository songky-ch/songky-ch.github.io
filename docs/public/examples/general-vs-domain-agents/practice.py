"""Offline teaching simulator. No LLM, external API, or persistent storage."""

from dataclasses import dataclass, replace
import platform


@dataclass(frozen=True)
class Request:
    principal: str = "user-demo"
    order_id: str = "A17"
    amount_cents: int = 19900
    approval_id: str | None = "approval-demo"
    operation_key: str = "refund-operation-demo"


class Service:
    def __init__(self, lose_response=False):
        self.order = {"id": "A17", "owner": "user-demo", "refundable_cents": 19900}
        self.approvals = {"approval-demo": ("user-demo", "A17", 19900)}
        self.refunds = {}
        self.lose_response = lose_response

    def get_order(self, request):
        if request.order_id != self.order["id"] or request.principal != self.order["owner"]:
            raise PermissionError("order not accessible")
        return dict(self.order)

    def validate(self, request):
        order = self.get_order(request)
        if not 0 < request.amount_cents <= order["refundable_cents"]:
            raise ValueError("amount outside refundable range")
        return {"eligible": True}

    def check_approval(self, request):
        bound = (request.principal, request.order_id, request.amount_cents)
        return {"approved": self.approvals.get(request.approval_id) == bound}

    def submit(self, request):
        self.validate(request)
        if not self.check_approval(request)["approved"]:
            raise PermissionError("approval missing or mismatched")
        if request.operation_key not in self.refunds:
            self.refunds[request.operation_key] = {
                "order_id": request.order_id,
                "amount_cents": request.amount_cents,
                "status": "confirmed",
            }
            if self.lose_response:
                raise TimeoutError("response lost after commit")
        return dict(self.refunds[request.operation_key])

    def get_refund(self, request):
        self.get_order(request)
        return dict(self.refunds[request.operation_key])


def execute(service, action, request, observations, trace):
    trace.append(action)
    try:
        observations[action] = getattr(service, action)(request)
    except TimeoutError:
        observations[action] = {"status": "unknown"}
        trace.append("response_unknown")
    except (PermissionError, ValueError) as error:
        return {"status": "blocked", "reason": str(error)}
    if action == "check_approval" and not observations[action]["approved"]:
        return {"status": "awaiting_approval"}
    return None


def decide(observations):
    if "get_order" not in observations:
        return "get_order"
    if "validate" not in observations:
        return "validate"
    if "check_approval" not in observations:
        return "check_approval"
    if "submit" not in observations:
        return "submit"
    if "get_refund" not in observations:
        return "get_refund"
    return "final"


def general(service, request):
    observations, trace = {}, []
    for _ in range(8):
        action = decide(observations)
        if action == "final":
            return {"status": "succeeded", "refund": observations["get_refund"]}, trace
        trace.append("decide:" + action)
        stopped = execute(service, action, request, observations, trace)
        if stopped:
            return stopped, trace
    return {"status": "budget_exhausted"}, trace


def vertical(service, request):
    observations, trace = {}, []
    for stage in ("get_order", "validate", "check_approval", "submit", "get_refund"):
        trace.append("stage:" + stage)
        stopped = execute(service, stage, request, observations, trace)
        if stopped:
            return stopped, trace
    return {"status": "succeeded", "refund": observations["get_refund"]}, trace


if __name__ == "__main__":
    print("Python", platform.python_version(), "|", platform.system(), platform.machine())
    print("Offline deterministic simulator; no LLM/API; in-memory state only.")
    cases = [
        ("normal", Request(), False, "succeeded", 1),
        ("no_approval", replace(Request(), approval_id=None), False, "awaiting_approval", 0),
        ("wrong_owner", replace(Request(), principal="other-user"), False, "blocked", 0),
        ("timeout_after_commit", Request(), True, "succeeded", 1),
        ("amount_over_limit", replace(Request(), amount_cents=20000), False, "blocked", 0),
    ]
    checks = 0
    for runner in (general, vertical):
        for name, request, lose_response, expected_status, expected_count in cases:
            service = Service(lose_response)
            result, trace = runner(service, request)
            assert result["status"] == expected_status
            assert len(service.refunds) == expected_count
            if expected_status == "succeeded":
                assert result["refund"]["status"] == "confirmed"
                assert result["refund"]["amount_cents"] == 19900
                assert result["refund"]["order_id"] == "A17"
                repeated = service.submit(request)
                assert repeated == result["refund"] and len(service.refunds) == 1
            if name == "timeout_after_commit":
                assert "response_unknown" in trace
                assert trace.index("response_unknown") < trace.index("get_refund")
                assert trace.count("submit") == 1
            print(f"PASS {runner.__name__}/{name}: {result['status']}, refunds={len(service.refunds)}")
            print("  " + " -> ".join(trace))
            checks += 1
    print(f"{checks} scenario checks passed.")
