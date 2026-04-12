import os
import subprocess
from typing import Optional

def get_repo_folder(target_repo: str) -> str:
    """Extracts the folder name from a URL or org/repo string."""
    if not target_repo:
        return ""
    # Remove .git and trailing slashes
    clean = target_repo.rstrip("/").replace(".git", "")
    if "/" in clean:
        return clean.split("/")[-1]
    return clean

def test_clone_url_construction(target_repo: str, token: Optional[str]):
    github_token = token
    clone_url = target_repo
    
    # Inject token if available for authenticated clone
    if github_token and "@github.com" not in target_repo:
        clone_url = target_repo.replace("https://github.com/", f"https://{github_token}@github.com/")

    mask_url = target_repo # What we show in logs
    print(f"Original: {target_repo}")
    print(f"Masked (Log): git clone {mask_url}")
    print(f"Real (Internal): {clone_url}")
    
    # Verify masking logic for errors
    if github_token:
        error_msg = f"fatal: could not read from remote repository. {clone_url} failed."
        clean_error = error_msg.replace(github_token, "********")
        print(f"Clean Error: {clean_error}")

print("--- TEST 1: HTTPS URL with Token ---")
test_clone_url_construction("https://github.com/bitpay/bitcore", "ghp_mock_token_123")

print("\n--- TEST 2: HTTPS URL without Token ---")
test_clone_url_construction("https://github.com/bitpay/bitcore", None)

print("\n--- TEST 3: Already authenticated URL ---")
test_clone_url_construction("https://ghp_existing@github.com/bitpay/bitcore", "ghp_new_token")
