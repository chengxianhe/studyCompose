from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter

from govplatform.delivery.context import get_context, prepare
from govplatform.delivery.evidence import EvidenceError, VerificationMode, read_evidence
from govplatform.delivery.report import latest_packet
from govplatform.delivery.service import import_verification
from govplatform.delivery.submission import submit
from govplatform.harness import service as harness
from govplatform.harness.models import AcceptanceResult, HarnessStatus
from govplatform.identity.models import Agent


def verify(repository: Path, mode: VerificationMode) -> tuple[int, Path]:
    prefix = f"Verification: {mode}; evidence: "
    directory: Path | None = None
    with subprocess.Popen(
        ["bash", "scripts/verify.sh", mode],
        cwd=repository,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as process:
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            if directory is None and line.startswith(prefix):
                directory = Path(line[len(prefix) :].strip())
        result = process.wait()
    if directory is None:
        raise EvidenceError(f"验证未产生证据目录，退出码 {result}")
    return result, directory


def main() -> None:
    parser = argparse.ArgumentParser(description="校验/执行统一门禁，并以 Agent 身份记录真实结果")
    parser.add_argument(
        "command", choices=("inspect", "import", "verify", "prepare", "submit", "status")
    )
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--mode", choices=("android", "platform", "all"))
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--session-id")
    parser.add_argument("--results", type=Path, help="非人工 AC 的 AcceptanceResult JSON 数组")
    parser.add_argument("--limitations", help="已知风险和未验证项；没有则明确说明")
    args = parser.parse_args()
    if args.command in ("inspect", "import", "submit") and args.evidence is None:
        parser.error("inspect/import/submit 需要 --evidence")
    if args.command != "inspect" and (not args.run_id or not args.session_id):
        parser.error("运行操作需要 --run-id 和 --session-id")
    if args.command not in ("submit", "status") and (args.repo is None or args.mode is None):
        parser.error("此命令需要 --repo 和 --mode")
    if args.command == "submit" and (args.results is None or not args.limitations):
        parser.error("submit 需要 --results 和 --limitations")
    caller = Agent(kind="codex", session_id=args.session_id or "evidence-inspect")
    try:
        if args.command == "status":
            run = harness.get(args.run_id, caller=caller)
            if run is None:
                raise EvidenceError("运行不存在；先由用户冻结并启动")
            print(run.model_dump_json(indent=2))
            context = get_context(args.run_id)
            print(context.model_dump_json(indent=2) if context else "未记录准入基线")
            print(
                f"最近生成的审查包（实际状态以上述运行为准）：{latest_packet(args.run_id) or '无'}"
            )
            return
        if args.command == "submit":
            context = get_context(args.run_id)
            if context is None:
                raise EvidenceError("缺少准入基线")
            if (args.repo is not None and str(args.repo.resolve()) != context.repository) or (
                args.mode is not None and args.mode != context.mode
            ):
                raise EvidenceError("仓库或验证范围与准入不一致")
            results = TypeAdapter(list[AcceptanceResult]).validate_json(args.results.read_bytes())
            run, packet = submit(
                run_id=args.run_id,
                directory=args.evidence,
                results=results,
                limitations=args.limitations,
                caller=caller,
            )
            print(f"run_id={run.run_id} status={run.status.value} review={packet / 'review.md'}")
            raise SystemExit(
                0 if run.status in (HarnessStatus.WAITING_FOR_HUMAN, HarnessStatus.PASSED) else 1
            )
        repository = args.repo.resolve()
        mode = cast(VerificationMode, args.mode)
        directory = args.evidence
        process_result: int | None = None
        if args.command in ("verify", "prepare"):
            run = harness.get(args.run_id, caller=caller)
            if run is None or run.status not in (HarnessStatus.DEVELOPING, HarnessStatus.REPAIRING):
                raise EvidenceError("运行必须已由用户启动，且处于开发或修复状态")
            if args.command == "verify" and get_context(args.run_id) is None:
                raise EvidenceError("先执行 prepare 记录准入，再开始实现和准出验证")
            previous = get_context(args.run_id)
            if previous is not None and (
                previous.repository != str(repository) or previous.mode != mode
            ):
                raise EvidenceError("仓库或验证范围与准入不一致；未执行验证命令")
            if args.command == "prepare" and previous is not None:
                resumed = prepare(
                    repository=repository,
                    directory=Path(previous.baseline.directory),
                    mode=mode,
                    run_id=args.run_id,
                    caller=caller,
                )
                print(resumed.model_dump_json(indent=2))
                return
            if directory is None or args.command == "verify":
                process_result, directory = verify(repository, mode)
        assert directory is not None
        evidence = read_evidence(repository, directory, mode)
        if process_result is not None and process_result != evidence.exit_code:
            raise EvidenceError("进程退出码与证据不一致，拒绝入库")
        if args.command == "prepare":
            context = prepare(
                repository=repository,
                directory=directory,
                mode=mode,
                run_id=args.run_id,
                caller=caller,
            )
            print(context.model_dump_json(indent=2))
        elif args.command == "inspect":
            print(evidence.model_dump_json(indent=2))
        else:
            updated = import_verification(
                repository=repository,
                directory=directory,
                mode=mode,
                run_id=args.run_id,
                caller=caller,
            )
            print(f"run_id={updated.run_id} status={updated.status.value}")
        raise SystemExit(evidence.exit_code)
    except (ValueError, harness.HarnessStateError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"未记录为通过：{exc}\n")


if __name__ == "__main__":
    main()
