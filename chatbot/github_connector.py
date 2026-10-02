import os
import requests
import logging

logger = logging.getLogger(__name__)

def fetch_github_repos(username):
    """
    Fetches the user's public, non-fork repositories via the GitHub API.
    Returns a list of {"name", "description", "language", "url"} dicts, or None if the request failed
    (so callers can tell "no repos" apart from "GitHub unreachable").
    """
    url = f"https://api.github.com/users/{username}/repos"
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }

    # Optionally authenticate if GITHUB_TOKEN is present to bypass rate limits
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        logger.info(f"Connecting to GitHub API to query repositories for user '{username}'...")
        response = requests.get(url, headers=headers, params={"per_page": 100}, timeout=15)
        if response.status_code == 200:
            repos = [
                {
                    "name": r.get("name", ""),
                    "description": r.get("description") or "",
                    "language": r.get("language") or "",
                    "url": r.get("html_url", ""),
                }
                # Skip forks to focus on owner's original work
                for r in response.json() if not r.get("fork", False)
            ]
            logger.info(f"Retrieved {len(repos)} repositories from GitHub.")
            return repos
        else:
            logger.error(f"Failed to fetch repositories: GitHub API returned status {response.status_code}. Response: {response.text}")
    except Exception as e:
        logger.error(f"Error occurred while connecting to GitHub API: {e}", exc_info=True)

    return None
