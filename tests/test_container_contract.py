from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_container_security_contract():
    docker = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "compose.yaml").read_text()
    ignore = (ROOT / ".dockerignore").read_text()
    assert "FROM python:3.12-slim" in docker
    assert "USER regen" in docker and "--reload" not in docker
    assert "${REGEN_BIND_IP:-127.0.0.1}:${REGEN_HOST_PORT:-18200}:8080" in compose
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose and "ALL" in compose
    assert "tmpfs:" in compose and "/tmp" in compose
    assert compose.count("${REGEN_AUDIT_DIR:-./.runtime/audit}:/data") == 1
    assert "docker.sock" not in compose
    assert "REGEN_API_TOKEN" in compose and "REGEN_API_TOKEN" not in docker
    assert ".runtime/" in (ROOT / ".gitignore").read_text()
    for text in (docker, compose):
        assert "/srv/projetos" not in text and ".ssh" not in text
    assert ".env" in ignore and ".git" in ignore and "__pycache__" in ignore
    assert "*.swp" in ignore and "*.swp" in (ROOT / ".gitignore").read_text()
