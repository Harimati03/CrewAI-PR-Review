import os
import requests
from urllib.parse import urlparse
from crewai.tools import tool


@tool("github_pr_file_fetcher")
def fetch_pr_files(pr_url: str) -> dict:
    """
    Fetch pull request metadata, modified files, diffs,
    and line change information from GitHub API.

    Input:
      - pr_url: GitHub pull request URL

    Output:
      - Structured JSON with repo info, commit hash,
        and per-file diffs for analysis agents.
    """

    # ---------- Parse PR URL ----------
    parsed_url = urlparse(pr_url)
    parts = parsed_url.path.strip("/").split("/")

    if len(parts) < 4 or parts[2] != "pull":
        raise ValueError(f"Invalid GitHub PR URL: {pr_url}")

    owner, repo, _, pr_number = parts

    # ---------- API URLs ----------
    pr_api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    files_api_url = f"{pr_api_url}/files"

    # ---------- Headers ----------
    github_token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json"
    }

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    # ---------- Fetch PR Metadata ----------
    pr_response = requests.get(pr_api_url, headers=headers, timeout=10)
    if pr_response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch PR metadata ({pr_response.status_code}): {pr_response.text}"
        )

    pr_data = pr_response.json()

    # ---------- Fetch Files (with pagination) ----------
    structured_files = []
    page = 1
    per_page = 100

    while True:
        files_response = requests.get(
            files_api_url,
            headers=headers,
            params={"page": page, "per_page": per_page},
            timeout=10
        )

        if files_response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch PR files ({files_response.status_code}): {files_response.text}"
            )

        files_data = files_response.json()
        if not files_data:
            break

        for file in files_data:
            structured_files.append({
                "filename": file.get("filename"),
                "status": file.get("status"),
                "additions": file.get("additions"),
                "deletions": file.get("deletions"),
                "changes": file.get("changes"),
                "patch": file.get("patch", "")
            })

        page += 1

    # ---------- Final Structured Output ----------
    return {
        "repo": f"{owner}/{repo}",
        "pull_request": int(pr_number),
        "branch": pr_data["head"]["ref"],
        "author": pr_data["user"]["login"],
        "commit_hash": pr_data["head"]["sha"],
        "files_changed": len(structured_files),
        "files": structured_files
    }
