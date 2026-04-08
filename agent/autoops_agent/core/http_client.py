import requests

from .config import settings


class ControlPlaneClient:
    def __init__(self) -> None:
        self.base_url = settings.control_plane_url.rstrip("/")
        self.agent_token: str | None = None

    def set_agent_token(self, token: str) -> None:
        self.agent_token = token

    def post(self, path: str, payload: dict, use_agent_token: bool = False) -> requests.Response:
        headers = {}
        if use_agent_token and self.agent_token:
            headers["Authorization"] = f"Bearer {self.agent_token}"
        if not use_agent_token and path == "/fleet/agents/register":
            headers["X-Enrollment-Token"] = settings.enrollment_token
        return requests.post(f"{self.base_url}{path}", json=payload, headers=headers, timeout=10)

    def get(self, path: str, use_agent_token: bool = False) -> requests.Response:
        headers = {}
        if use_agent_token and self.agent_token:
            headers["Authorization"] = f"Bearer {self.agent_token}"
        return requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
