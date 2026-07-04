import os
import requests
import logging
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

def fetch_github_data(username):
    """
    Fetches all public repositories for the specified user via GitHub API,
    and returns them as a list of LangChain Document objects.
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
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            repos = response.json()
            docs = []
            for r in repos:
                # Skip forks to focus on owner's original work
                if r.get("fork", False):
                    continue
                name = r.get("name", "")
                desc = r.get("description", "") or "No description"
                lang = r.get("language", "") or "Unknown language"
                stars = r.get("stargazers_count", 0)
                url_repo = r.get("html_url", "")
                
                content = f"GitHub Repository: {name}. Description: {desc}. Primary Language: {lang}. Stars: {stars}. Repository URL: {url_repo}."
                docs.append(Document(
                    page_content=content, 
                    metadata={"source": "github_api", "repo_name": name, "url": url_repo}
                ))
            logger.info(f"Retrieved {len(docs)} repositories from GitHub.")
            return docs
        else:
            logger.error(f"Failed to fetch repositories: GitHub API returned status {response.status_code}. Response: {response.text}")
    except Exception as e:
        logger.error(f"Error occurred while connecting to GitHub API: {e}", exc_info=True)
        
    return []
