from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from govplatform.evaluation.models import Backend
from govplatform.evaluation.runner import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="Isolated retrieval baseline, no paid LLM calls")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--backend", choices=("sqlite", "elasticsearch", "both"), default="both")
    parser.add_argument("--es-url", help="Explicit local Elasticsearch URL for isolated eval index")
    parser.add_argument(
        "--output", type=Path, required=True, help="New output file; never overwrite"
    )
    args = parser.parse_args()
    if args.backend != "sqlite" and not args.es_url:
        parser.error("Elasticsearch evaluation requires --es-url")
    if args.output.exists():
        parser.error("output already exists; choose a new path to preserve evidence")
    backends: list[Backend] = (
        ["sqlite", "elasticsearch"] if args.backend == "both" else [cast(Backend, args.backend)]
    )
    report = evaluate(args.dataset, backends, args.es_url)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(report.model_dump_json(indent=2) + "\n")
    for backend in report.backends:
        print(backend.requested_backend, backend.metrics, "error_type=", backend.error_type)
    # Poor quality is a measured result, not a reason to hide the report or tune labels.
    if any(
        item.error_type
        or any(row.status != "ok" or row.lifecycle_violations for row in item.results)
        for item in report.backends
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
