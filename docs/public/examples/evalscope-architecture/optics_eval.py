import argparse
import json
from pathlib import Path

from evalscope import TaskConfig, run_task
from evalscope.api.benchmark import BenchmarkMeta, DefaultDataAdapter
from evalscope.api.dataset import Sample
from evalscope.api.metric import Score
from evalscope.api.metric.semantics import MetricIdentity, MetricSelector, MetricSemantics
from evalscope.api.model import ModelAPI, ModelOutput
from evalscope.api.registry import register_benchmark
from evalscope.report import Category, Metric, Report, Subset


METRICS = ["schema_valid", "diagnosis_correct", "action_correct", "safe_action", "evidence_valid", "joint_pass"]


def score_response(prediction, target, metadata):
    values = dict.fromkeys(METRICS, 0.0)
    try:
        answer = json.loads(prediction)
    except json.JSONDecodeError:
        return values
    if not isinstance(answer, dict):
        return values
    if set(answer) != {"diagnosis", "next_action", "escalate", "citations"}:
        return values
    if not all(isinstance(answer[k], str) for k in ["diagnosis", "next_action"]):
        return values
    if type(answer["escalate"]) is not bool:
        return values
    if not isinstance(answer["citations"], list) or not all(isinstance(c, str) for c in answer["citations"]):
        return values
    expected = json.loads(target)
    values["schema_valid"] = 1.0
    values["diagnosis_correct"] = float(answer["diagnosis"] == expected["diagnosis"])
    values["action_correct"] = float(
        answer["next_action"] in expected["allowed_next_actions"]
        and answer["escalate"] == expected["escalate"]
    )
    values["safe_action"] = float(answer["next_action"] in metadata["safe_actions"])
    citations = set(answer["citations"])
    values["evidence_valid"] = float(
        bool(citations) and citations <= set(metadata["supporting_citations"])
    )
    values["joint_pass"] = float(all(values[k] == 1.0 for k in METRICS[:-1]))
    return values


@register_benchmark(BenchmarkMeta(
    name="optics_maintenance_demo",
    dataset_id="optics_maintenance_demo",
    subset_list=["diagnosis", "edge"],
    eval_split="test",
    prompt_template="{question}",
    metric_list=METRICS,
    primary_metric=MetricSelector(name="joint_pass", aggregation="mean"),
    evaluation_version="v1.0",
))
class OpticsAdapter(DefaultDataAdapter):
    def load_from_disk(self, **kwargs):
        return super().load_from_disk(use_local_loader=True)

    def record_to_sample(self, record):
        return Sample(
            input=record["query"],
            target=json.dumps(record["target"], ensure_ascii=False),
            metadata=record["metadata"],
        )

    def match_score(self, original_prediction, filtered_prediction, reference, task_state):
        return Score(
            value=score_response(filtered_prediction, reference, task_state.metadata),
            prediction=original_prediction,
            extracted_prediction=filtered_prediction,
            main_score_name="joint_pass",
        )

    def _on_generate_report(self, scores, model_name):
        metrics = []
        for name in METRICS:
            subsets = [
                Subset(name=subset, score=agg.score, num=agg.num)
                for subset, aggregates in scores.items()
                for agg in aggregates if agg.metric_name == name
            ]
            metrics.append(Metric(
                identity=MetricIdentity(name=name, aggregation="mean"),
                categories=[Category(name="default", subsets=subsets)],
                semantics=MetricSemantics(
                    semantic_id=f"optics.{name}.ratio",
                    metric_name=name,
                    kind="quality",
                    direction="higher_is_better",
                    value_range={"min": 0, "max": 1},
                    display_kind="percent",
                    display_multiplier=100,
                    display_unit="%",
                    display_precision=1,
                ),
            ))
        return Report(
            name=self.name,
            dataset_name=self.name,
            model_name=model_name,
            metrics=metrics,
            primary_metric_identity=MetricIdentity(name="joint_pass", aggregation="mean"),
        )


class FixtureModel(ModelAPI):
    def __init__(self, variant, predictions):
        super().__init__(model_name=f"optics-{variant}-fixture")
        self.predictions = predictions
        self.calls = 0

    def generate(self, input, tools, tool_choice, config):
        self.calls += 1
        ticket_id = input[-1].content.splitlines()[0].removeprefix("ticket_id=")
        content = json.dumps(self.predictions[ticket_id], ensure_ascii=False)
        return ModelOutput.from_content(model=self.model_name, content=content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=["baseline", "candidate"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--rerun-review", action="store_true")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    predictions = json.loads((here / "predictions.json").read_text())[args.variant]
    model = FixtureModel(args.variant, predictions)
    cfg = TaskConfig(
        model=model,
        datasets=["optics_maintenance_demo"],
        dataset_args={"optics_maintenance_demo": {"local_path": str(here / "data")}},
        eval_batch_size=1,
        judge={"strategy": "rule"},
        generation_config={"temperature": 0, "max_tokens": 256},
        collect_perf=False,
        work_dir=str(args.output.resolve()),
        no_timestamp=True,
        use_cache=str(args.output.resolve()) if args.resume else None,
        rerun_review=args.rerun_review,
    )
    run_task(cfg)
    print(f"FIXTURE_MODEL_CALLS={model.calls}")


if __name__ == "__main__":
    main()
