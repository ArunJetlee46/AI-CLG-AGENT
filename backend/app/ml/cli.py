"""CLI for the Phase-9 ML pipeline.

Usage:
  python -m app.ml.cli train --task dropout      # train one task
  python -m app.ml.cli train --all --booster     # all four tasks (xgboost if installed)
  python -m app.ml.cli predict --task placement  # score + explain top rows
  python -m app.ml.cli datasets                  # inspect dataset shapes/labels
"""
import argparse
import json

from app.db import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.ml.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    train = sub.add_parser("train")
    train.add_argument("--task", choices=["performance", "placement", "attendance", "dropout"])
    train.add_argument("--all", action="store_true")
    train.add_argument("--booster", action="store_true", help="use XGBoost when installed")

    predict = sub.add_parser("predict")
    predict.add_argument("--task", choices=["performance", "placement", "attendance", "dropout"], required=True)
    predict.add_argument("--limit", type=int, default=10)

    datasets = sub.add_parser("datasets")

    args = parser.parse_args()
    if args.command == "train":
        from app.ml.train import train_all, train_task

        results = train_all(use_booster=args.booster) if args.all else [train_task(args.task, use_booster=args.booster)]
        print(json.dumps(results, indent=2, default=str))
    elif args.command == "predict":
        from app.ml.predict import predict_task

        db = SessionLocal()
        try:
            print(json.dumps(predict_task(db, args.task, limit=args.limit), indent=2, default=str))
        finally:
            db.close()
    elif args.command == "datasets":
        from app.ml.datasets import build_all

        db = SessionLocal()
        try:
            for task, dataset in build_all(db).items():
                print(f"{task}: rows={dataset['rows']} pos_rate={dataset['meta'].get('pos_rate')} "
                      f"features={len(dataset['features'])}")
        finally:
            db.close()


if __name__ == "__main__":
    main()
