"""Commands: build a lake, verify it, serve a page; interpret one
question with AMIGO, picking the interpretation meant at the prompt (or, with --ask,
answering AMIGO's questions)."""

import argparse
import logging
import sys

from . import config, layer


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m amigo")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        commands.add_parser(name).add_argument("lake")
    interpreting = commands.add_parser("interpret")
    interpreting.add_argument("lake")
    interpreting.add_argument("question")
    interpreting.add_argument("--ask", action="store_true", help="answer AMIGO's questions instead of picking")
    serving = commands.add_parser("serve")
    serving.add_argument("lake", nargs="*")
    serving.add_argument("--port", type=int, default=8765)
    serving.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "build":
        layer.build(args.lake)
    elif args.command == "interpret":
        from . import interpret
        from .probe import Probe

        probe = Probe(args.lake)
        stage, found = interpret.run(probe, args.question, config.RUNS_DIR / f"interpret_{args.lake}.jsonl")
        if found:
            print(interpret.show(probe, stage, found))
        else:
            print("No interpretation in this lake, even leaving out parts of the question.")
        if sys.stdin.isatty() and found:
            found = (interpret.ask if args.ask else interpret.pick)(probe, stage, found, input)
            print(interpret.show(probe, stage, found))
        if sys.stdin.isatty() and found and not found[0].left_out and len(stage.entities) > 1 and input(
                "Show answers that leave out one part of the question? [y/N] ").strip().lower() == "y":
            log_path = config.RUNS_DIR / f"interpret_{args.lake}.jsonl"
            for j, some in interpret.relaxed(probe, stage, args.question, log_path) or [(None, [])]:
                if j is None:
                    print("Leaving out one part gives no interpretation either.")
                else:
                    print(f'Leaving out "{stage.entities[j].attribute}":')
                    print(interpret.show(probe, stage, some))
    elif args.command == "serve":
        from . import serve

        serve.run(args.lake, args.port, args.host)
    else:
        from . import verify

        if not verify.run(args.lake):
            sys.exit(1)


if __name__ == "__main__":
    main()
