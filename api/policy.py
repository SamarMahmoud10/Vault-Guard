from typing import Optional

FAIL_ON_HADOLINT_LEVELS = {"error"}
FAIL_ON_TRIVY_SEVERITIES = {"HIGH", "CRITICAL"}


def evaluate(hadolint_results: Optional[list], trivy_results: Optional[dict]) -> dict:
    violations = []

    # Fail-closed: if a scanner didn't run successfully, that's a
    # failure on its own — we never treat "the tool crashed" the same
    # as "the tool found nothing wrong".
    if hadolint_results is None:
        violations.append(
            {
                "source": "system",
                "tool": "hadolint",
                "message": "Hadolint failed to execute — failing closed",
            }
        )
    else:
        for issue in hadolint_results:
            if issue.get("level") in FAIL_ON_HADOLINT_LEVELS:
                violations.append(
                    {
                        "source": "hadolint",
                        "line": issue.get("line"),
                        "code": issue.get("code"),
                        "message": issue.get("message"),
                    }
                )

    if trivy_results is None:
        violations.append(
            {
                "source": "system",
                "tool": "trivy",
                "message": "Trivy failed to execute — failing closed",
            }
        )
    else:
        for result in trivy_results.get("Results", []):
            for vuln in result.get("Vulnerabilities") or []:
                if vuln.get("Severity") in FAIL_ON_TRIVY_SEVERITIES:
                    violations.append(
                        {
                            "source": "trivy",
                            "package": vuln.get("PkgName"),
                            "vulnerability_id": vuln.get("VulnerabilityID"),
                            "severity": vuln.get("Severity"),
                        }
                    )

    status = "fail" if violations else "pass"
    return {"status": status, "violations": violations}