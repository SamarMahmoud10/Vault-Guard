import hashlib
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Client, ScanResult
from notifier import send_failure_alert
from policy import evaluate
from scanners import prepare_scan_workspace, run_hadolint, run_trivy_fs
from schemas import ScanRequest, ScanResponse

app = FastAPI(title="Vault-Guard API")

Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def seed_default_client():
    default_key = os.getenv("VAULT_GUARD_API_KEY")
    if not default_key:
        return

    db = next(get_db())
    key_hash = hashlib.sha256(default_key.encode()).hexdigest()
    existing = db.query(Client).filter(Client.api_key_hash == key_hash).first()
    if not existing:
        db.add(Client(name="default-client", api_key_hash=key_hash))
        db.commit()


@app.get("/health")
def health_check():
    return {"status": "ok"}


def authenticate(
    x_api_key: str = Header(...), db: Session = Depends(get_db)
) -> Client:
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    client = (
        db.query(Client)
        .filter(Client.api_key_hash == key_hash, Client.is_active == True)  # noqa: E712
        .first()
    )
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return client


@app.post("/scan", response_model=ScanResponse)
def scan(
    request: ScanRequest,
    client: Client = Depends(authenticate),
    db: Session = Depends(get_db),
):
    workspace = prepare_scan_workspace(
        request.dockerfile_content,
        request.dependency_file_name,
        request.dependency_file_content,
    )

    hadolint_results = run_hadolint(f"{workspace}/Dockerfile")
    trivy_results = run_trivy_fs(workspace)

    verdict = evaluate(hadolint_results, trivy_results)

    scan_result = ScanResult(
        client_id=client.id,
        repo_name=request.repo_name,
        commit_sha=request.commit_sha,
        status=verdict["status"],
        hadolint_raw=hadolint_results,
        trivy_raw=trivy_results,
        policy_violations=verdict["violations"],
    )
    db.add(scan_result)
    db.commit()
    db.refresh(scan_result)

    if verdict["status"] == "fail":
        send_failure_alert(request.repo_name, request.commit_sha, verdict["violations"])

    return ScanResponse(
        status=verdict["status"],
        violations=verdict["violations"],
        scan_id=str(scan_result.id),
    )