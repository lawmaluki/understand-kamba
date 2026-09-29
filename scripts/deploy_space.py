"""
Upload the backend to the Hugging Face Space.

Copies space/ (README with Space config, server.py, requirements.txt) and
app/ into a temporary folder and uploads it, so only the backend is
published -- no web/, docs/, .env or data/.

Usage (after `hf auth login` with a write token):
    python scripts/deploy_space.py [--space lawmaluki/understand-kamba-api]
"""
import argparse
import os
import shutil
import tempfile

from huggingface_hub import HfApi

ROOT = os.path.join(os.path.dirname(__file__), "..")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", default="lawmaluki/understand-kamba-api")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as stage:
        for name in os.listdir(os.path.join(ROOT, "space")):
            src = os.path.join(ROOT, "space", name)
            if os.path.isfile(src):  # skips __pycache__ and the like
                shutil.copy2(src, stage)
        shutil.copytree(
            os.path.join(ROOT, "app"),
            os.path.join(stage, "app"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        commit = HfApi().upload_folder(
            repo_id=args.space,
            repo_type="space",
            folder_path=stage,
            delete_patterns=["*"],  # remove files no longer in the stage
            commit_message="Deploy backend",
        )
    print("Uploaded:", commit.commit_url)
    print(f"Build logs: https://huggingface.co/spaces/{args.space}?logs=build")


if __name__ == "__main__":
    main()
