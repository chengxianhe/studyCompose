import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="本机人工知识审核与任务确认")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    uvicorn.run(
        "govplatform.review.app:create_review_app", factory=True, host="127.0.0.1", port=args.port
    )


if __name__ == "__main__":
    main()
