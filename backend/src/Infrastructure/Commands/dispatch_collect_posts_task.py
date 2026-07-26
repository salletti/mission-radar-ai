import argparse
import sys

from src.Infrastructure.Worker.tasks.collect_posts_task import collect_posts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch collect_posts Celery task")
    parser.add_argument("--query", default="symfony freelance paris", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Max number of posts to collect")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        task = collect_posts.delay(args.query, args.limit)
        print(f"Task dispatched — ID : {task.id}")
        print("Result will appear in worker logs:")
        print("  docker compose logs -f celery_worker")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
