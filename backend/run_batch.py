import argparse
import shutil
from pathlib import Path

from app import config, report
from app.pipeline import InvalidImageError, Options, Pipeline


def main():
    ap = argparse.ArgumentParser(description="Restore every image in a folder")
    ap.add_argument("input")
    ap.add_argument("--out", default="restored")
    ap.add_argument("--mode", default="auto", choices=["auto", "id_photo", "document"])
    ap.add_argument("--scale", type=int, default=0, choices=[0, 1, 2, 4])
    ap.add_argument("--sharpen", type=float, default=0.5)
    ap.add_argument("--contrast", type=float, default=0.5)
    ap.add_argument("--fidelity", type=float, default=0.7)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pipe = Pipeline()
    jobs, errors = [], []
    files = [p for p in sorted(Path(args.input).iterdir()) if p.suffix.lower() in config.ALLOWED_EXT]
    for i, p in enumerate(files, 1):
        try:
            job = pipe.run(p.read_bytes(), p.name, Options(args.mode, args.scale, True, args.sharpen, args.contrast, args.fidelity))
            shutil.copy(config.JOBS_DIR / job["id"] / "restored.png", out / f"{p.stem}_restored.png")
            jobs.append(job)
            print(f"[{i}/{len(files)}] {p.name}: quality {job['metrics']['quality']['score']}, preservation {job['metrics']['preservation']['score']} ({job['metrics']['preservation']['verdict']})")
        except (InvalidImageError, OSError) as exc:
            errors.append({"filename": p.name, "error": str(exc)})
            print(f"[{i}/{len(files)}] {p.name}: failed, {exc}")
    (out / "summary.csv").write_text(report.batch_csv(jobs, errors), encoding="utf-8")
    print(f"Done. {len(jobs)} ok, {len(errors)} failed. Summary at {out / 'summary.csv'}")


if __name__ == "__main__":
    main()
