"""Standard-library-only local CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import SocietalReasoner
from .deliberation import DeliberationCase
from .graph import KnowledgeGraph
from .ingest import import_markdown, write_jsonl
from .models import Scenario
from .merge import merge_files
from .semantics import LexicalRegistry
from .evaluate import evaluate_file


def print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sre", description="Offline societal reasoning prototype")
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="Audit validated inventory metadata")
    audit.add_argument("--concepts", type=Path)
    audit.add_argument("--edges", type=Path)
    search = sub.add_parser("search", help="Search a local concept graph")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--concepts", type=Path)
    search.add_argument("--edges", type=Path)
    get = sub.add_parser("concept", help="Show concept by original inventory identifier")
    get.add_argument("id", type=int)
    get.add_argument("--concepts", type=Path)
    get.add_argument("--edges", type=Path)
    graph = sub.add_parser("neighbors", help="Expand explicit knowledge relationships")
    graph.add_argument("id", type=int)
    graph.add_argument("--depth", type=int, default=1)
    graph.add_argument("--concepts", type=Path)
    graph.add_argument("--edges", type=Path)
    reason = sub.add_parser("reason", help="Analyze a caller-structured, provenance-tagged scenario")
    reason.add_argument("scenario", type=Path)
    reason.add_argument("--concepts", type=Path)
    reason.add_argument("--edges", type=Path)
    deliberate = sub.add_parser("deliberate", help="Compare sourced, caller-proposed readings with explicit warrants")
    deliberate.add_argument("case", type=Path)
    deliberate.add_argument("--concepts", type=Path)
    deliberate.add_argument("--edges", type=Path)
    compare = sub.add_parser("compare-deliberations", help="Report changes between two declared contexts")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    compare.add_argument("--concepts", type=Path)
    compare.add_argument("--edges", type=Path)
    ingest = sub.add_parser("ingest", help="Ingest an exact Markdown copy of an inventory volume")
    ingest.add_argument("input", type=Path)
    ingest.add_argument("output", type=Path)
    ingest.add_argument("--volume", required=True, type=int)
    ingest.add_argument("--expected-start", type=int)
    ingest.add_argument("--expected-end", type=int)
    ingest.add_argument("--require-contiguous", action="store_true")
    merged = sub.add_parser("merge", help="Merge inventory batches, source-transcribed records replace seed summaries")
    merged.add_argument("sources", type=Path, nargs="+")
    merged.add_argument("--output", type=Path, required=True)
    lex = sub.add_parser("define", help="Show reviewed Merriam-Webster senses (source linked; glosses are original)")
    lex.add_argument("term")
    check = sub.add_parser("evaluate", help="Run deterministic developer-authored regression scenarios")
    check.add_argument("cases", type=Path)
    assess = sub.add_parser("assess", help="Capture exact human text and propose surface context boundaries")
    assess.add_argument("input", type=Path, help="UTF-8 file containing the original utterance")
    assess.add_argument("--material", action="append", default=[], help="A material dictionary word from the utterance")
    assess.add_argument("--sense", action="append", default=[], metavar="WORD=ID", help="Caller-supported dictionary sense ID")
    review = sub.add_parser("review-draft", help="Run bounded attribution checks on a proposed answer")
    review.add_argument("assessment", type=Path, help="The assess JSON output")
    review.add_argument("draft", type=Path, help="UTF-8 draft text")
    review.add_argument("--as-user", action="store_true", help="First-person ghostwritten draft for the source speaker")
    demo = sub.add_parser("demo", help="Run bundled context interpretation example")

    args = parser.parse_args(argv)
    try:
        if args.command == "assess":
            senses = {}
            for item in args.sense:
                if "=" not in item or not all(x.strip() for x in item.split("=", 1)):
                    raise ValueError("--sense requires WORD=ID")
                word, sense = item.split("=", 1)
                if word.casefold() in senses:
                    raise ValueError(f"Duplicate --sense word: {word}")
                senses[word.casefold()] = sense
            result = SocietalReasoner.starter().assess_text(
                args.input.read_text(encoding="utf-8"),
                material_words=tuple(args.material), selected_senses=senses,
            )
            print_json(result)
            return 0
        if args.command == "review-draft":
            assessment = json.loads(args.assessment.read_text(encoding="utf-8"))
            result = SocietalReasoner.starter().review_draft(
                assessment, args.draft.read_text(encoding="utf-8"), writing_as_user=args.as_user
            )
            print_json(result)
            return 0 if result["status"] == "pass" else 1
        if args.command == "ingest":
            original = args.input.read_text(encoding="utf-8")
            records, report = import_markdown(
                original, volume=args.volume, source_title=args.input.name,
                expected_start=args.expected_start,
                expected_end=args.expected_end,
                require_contiguous=args.require_contiguous,
            )
            write_jsonl(records, args.output)
            print_json({"saved": str(args.output), "report": report})
            return 0
        if args.command == "merge":
            print_json(merge_files(args.sources, args.output))
            return 0
        if args.command == "define":
            result = LexicalRegistry.starter().lookup(args.term)
            if result is None:
                print(f"Term {args.term!r} not in reviewed registry. No sense asserted.", file=sys.stderr)
                return 2
            print_json(result)
            return 0
        if args.command == "evaluate":
            report = evaluate_file(SocietalReasoner.starter(), args.cases)
            print_json(report)
            return 0 if report["failed"] == 0 else 1
        if args.command == "deliberate":
            case = DeliberationCase.from_dict(json.loads(args.case.read_text(encoding="utf-8")))
            graph = KnowledgeGraph.from_files(args.concepts, args.edges) if args.concepts else KnowledgeGraph.starter()
            print_json(SocietalReasoner(graph, SocietalReasoner.default_rules()).deliberate(case))
            return 0
        if args.command == "compare-deliberations":
            before = DeliberationCase.from_dict(json.loads(args.before.read_text(encoding="utf-8")))
            after = DeliberationCase.from_dict(json.loads(args.after.read_text(encoding="utf-8")))
            graph = KnowledgeGraph.from_files(args.concepts, args.edges) if args.concepts else KnowledgeGraph.starter()
            print_json(SocietalReasoner(graph, SocietalReasoner.default_rules()).compare_deliberations(before, after))
            return 0
        if args.command == "reason":
            case = Scenario.from_dict(json.loads(args.scenario.read_text(encoding="utf-8")))
            graph = KnowledgeGraph.from_files(args.concepts, args.edges) if args.concepts else KnowledgeGraph.starter()
            print_json(SocietalReasoner(graph, SocietalReasoner.default_rules()).analyze(case))
            return 0
        if args.command == "demo":
            from importlib.resources import files
            example = files("societal_reasoning").joinpath("resources", "demo_social.json")
            with example.open(encoding="utf-8") as stream:
                case = Scenario.from_dict(json.load(stream))
            print_json(SocietalReasoner.starter().analyze(case))
            return 0
        if args.command == "neighbors":
            knowledge = KnowledgeGraph.from_files(args.concepts, args.edges) if args.concepts else KnowledgeGraph.starter()
            print_json(knowledge.neighbors(args.id, depth=args.depth))
            return 0
        knowledge = KnowledgeGraph.from_files(args.concepts, args.edges) if args.concepts else KnowledgeGraph.starter()
        if args.command == "audit":
            print_json(knowledge.audit())
        elif args.command == "search":
            print_json([c.to_dict() for c in knowledge.search(args.query, limit=args.limit)])
        elif args.command == "concept":
            item = knowledge.get(args.id)
            if item is None:
                print(f"Unknown concept {args.id}", file=sys.stderr)
                return 2
            print_json(item.to_dict())
        else:
            parser.error("Unknown subcommand")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
