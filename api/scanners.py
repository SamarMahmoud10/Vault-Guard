import json
import os
import subprocess
import tempfile
from typing import Optional


def prepare_scan_workspace(
    dockerfile_content: str,
    dependency_file_name: Optional[str],
    dependency_file_content: Optional[str],
) -> str:
    workspace = tempfile.mkdtemp(prefix="vaultguard_")

    with open(os.path.join(workspace, "Dockerfile"), "w") as f:
        f.write(dockerfile_content)

    if dependency_file_name and dependency_file_content:
        with open(os.path.join(workspace, dependency_file_name), "w") as f:
            f.write(dependency_file_content)

    return workspace


def run_hadolint(dockerfile_path: str) -> Optional[list]:
    """Returns a list of issues (possibly empty) on success.
    Returns None if the tool itself failed to run — caller must treat
    this as a scan failure (fail-closed), NOT as "no issues found".
    """
    try:
        result = subprocess.run(
            ["hadolint", "--format", "json", dockerfile_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    # hadolint exits 0 (no issues) or 1 (issues found) on a normal run.
    # Anything else means the tool itself crashed/misbehaved.
    if result.returncode not in (0, 1):
        return None

    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        return None


def run_trivy_fs(target_dir: str) -> Optional[dict]:
    """Returns the parsed Trivy report on success.
    Returns None if the tool itself failed to run — caller must treat
    this as a scan failure (fail-closed), NOT as "no vulnerabilities".
    """
    try:
        result = subprocess.run(
            ["trivy", "fs", "--format", "json", "--scanners", "vuln", target_dir],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    # We never set --exit-code, so Trivy only returns non-zero on a real error.
    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return None