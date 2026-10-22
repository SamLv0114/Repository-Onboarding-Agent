"""Clone each repository in data/repos.json and check out its pinned commit.

Run from backend/: python -m scripts.fetch_repos
"""

import subprocess

from app.services.repositories import list_repositories


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def main():
    for repository in list_repositories():
        if repository.commit is None:
            continue
        root = str(repository.root)
        if not repository.root.exists():
            print(f"Cloning {repository.url} into {root}")
            git("clone", "--quiet", repository.url, root)
        git("-C", root, "fetch", "--quiet", "origin", repository.commit)
        git(
            "-C",
            root,
            "-c",
            "advice.detachedHead=false",
            "checkout",
            "--quiet",
            repository.commit,
        )
        head = git("-C", root, "rev-parse", "HEAD")
        print(f"{repository.repository_id}: {head}")


if __name__ == "__main__":
    main()
