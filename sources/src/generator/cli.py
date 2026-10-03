"""Command line: generate (reference tables) | stream (sales events)."""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .config import DATA_DIR, calibration_path, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generator", description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="path to a TOML config (default: config/fruit_juice.toml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("generate", help="write the dimensions and the revenue target (tab_fato004) as Parquet")
    p.add_argument("--start", help="override period.start (YYYY-MM-DD)")
    p.add_argument("--end", help="override period.end (YYYY-MM-DD)")
    p.add_argument("--seed", type=int, help="override seed")

    p = sub.add_parser("stream", help="emit individual synthetic sales events in real time")
    p.add_argument("--sink", choices=["stdout", "file", "kafka"], default="stdout",
                   help="where events go (default: stdout, one JSON object per line)")
    p.add_argument("--file", type=Path, help="path for --sink file (default: data/stream/<dataset>/events.jsonl)")
    p.add_argument("--rate", type=float, default=1.0, help="events per second (default: 1.0)")
    p.add_argument("--duration", type=float, help="stop after this many seconds (default: run until Ctrl+C)")
    p.add_argument("--count", type=int, help="stop after this many events")
    p.add_argument("--as-of", help="simulated 'today' for prices/costs and timestamps (YYYY-MM-DD; default: real today)")
    p.add_argument("--speed", type=float, default=1.0, help="simulated-time multiplier (2.0 = runs twice as fast as the wall clock)")
    p.add_argument("--no-jitter", action="store_true", help="fixed interval between events instead of a Poisson process")
    p.add_argument("--start-seq", type=int, default=0, help="first event number (resume a stopped stream exactly)")
    p.add_argument("--seed", type=int, help="override seed (default: from config)")
    p.add_argument("--quiet", action="store_true", help="do not print a one-line summary per event to stderr")

    args = parser.parse_args(argv)
    overrides = {"seed": args.seed} if args.seed is not None else {}
    if args.command == "generate":
        if args.start:
            overrides["period.start"] = args.start
        if args.end:
            overrides["period.end"] = args.end
    cfg = load_config(args.config, **overrides)

    if args.command == "generate":
        from .batch import generate
        print(f"generating {cfg['dataset']} {cfg['period']['start']} -> {cfg['period']['end']} (seed {cfg['seed']})")
        counts = generate(cfg)
        print("\n".join(f"  {name:20s} {rows:>12,d}" for name, rows in counts.items()))
        return 0
    return stream(cfg, args)


def stream(cfg: dict, args: argparse.Namespace) -> int:
    from .model import Model, load_calibration
    from .sinks import make_sink
    from .stream import EventGenerator, iter_events

    as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
    model = Model(load_calibration(calibration_path(cfg)), cfg, last_year=as_of.year)
    generator = EventGenerator(model, as_of)
    start_time = datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc)

    file_path = args.file or (DATA_DIR / "stream" / cfg["dataset"] / "events.jsonl")
    try:
        sink = make_sink(args.sink, cfg["dataset"], file_path)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print(f"streaming {cfg['dataset']} -> {args.sink} at {args.rate:g} events/s (seed {cfg['seed']}, as-of {as_of}, "
          f"speed {args.speed:g}x){'' if args.sink != 'file' else f': {file_path}'}  (Ctrl+C to stop)", file=sys.stderr)
    emitted = 0
    try:
        for event in iter_events(generator, args.rate, start_seq=args.start_seq, count=args.count,
                                 duration=args.duration, start_time=start_time, speed=args.speed,
                                 jitter=not args.no_jitter):
            sink.write(event)
            emitted += 1
            if not args.quiet and args.sink != "stdout":
                print(f"  [{event.seq:>8}] {event.event_time:%H:%M:%S} {event.cod_cliente} {event.cod_produto} "
                      f"{event.cod_fabrica}  R$ {event.faturamento:>9,.2f}", file=sys.stderr)
    except KeyboardInterrupt:
        print(file=sys.stderr)
    finally:
        sink.close()
    print(f"stopped after {emitted:,} event(s); resume with --start-seq {args.start_seq + emitted}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
