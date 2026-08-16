from typing import Optional

from pydantic import BaseModel


class ScanRequest(BaseModel):
    repo_name: str
    commit_sha: str
    dockerfile_content: str
    dependency_file_name: Optional[str] = None
    dependency_file_content: Optional[str] = None


class ScanResponse(BaseModel):
    status: str
    violations: list
    scan_id: str