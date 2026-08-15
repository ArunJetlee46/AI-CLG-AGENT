import argparse
import json
import os

from app.db import SessionLocal, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Beru Campus AI - synthetic data generator")
    parser.add_argument("--students", type=int, default=500)
    parser.add_argument("--courses", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=None, help="write JSON bundle to this directory")
    parser.add_argument("--no-db", action="store_true", help="skip database insert")
    parser.add_argument("--reset", action="store_true", help="wipe existing rows from the database before inserting")
    args = parser.parse_args()

    from synthetic.generator import SyntheticDataGenerator

    generator = SyntheticDataGenerator(students=args.students, courses=args.courses, seed=args.seed)
    bundle = generator.generate()
    print(
        f"Generated: {len(bundle.students)} students, {len(bundle.courses)} courses, "
        f"{len(bundle.enrollments)} enrollments, {len(bundle.attendance)} attendance rows, "
        f"{len(bundle.timetable)} timetable entries"
    )

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        manifest = {}
        for name, rows in bundle.__dict__.items():
            path = os.path.join(args.out, f"{name}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rows, fh, default=str, indent=1)
            manifest[name] = len(rows)
        with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
        print(f"JSON bundle written to {args.out}")

    if not args.no_db:
        init_db()
        db = SessionLocal()
        try:
            if args.reset:
                from app.models import entities

                for table in reversed(entities.Base.metadata.sorted_tables):
                    db.execute(table.delete())
                db.commit()
                print("Database wiped")
            stats = generator.insert_to_db(db, bundle)
            print(f"Inserted into database: {stats}")
        finally:
            db.close()


if __name__ == "__main__":
    main()
