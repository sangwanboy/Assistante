from __future__ import annotations

import json
import socket
from contextlib import closing

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_workspace import WebWorkspace
from app.services.web_workspace_manager import WebWorkspaceManager
from app.tools.base import BaseTool


def _find_free_port(start: int = 8400, end: int = 8999) -> int:
    for port in range(start, end + 1):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free preview ports available")


class WebWorkspaceCreateTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_workspace_create"

    @property
    def description(self) -> str:
        return "Create a web workspace for static or React app generation."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_type": {"type": "string", "enum": ["static", "react"], "default": "static"},
            },
        }

    async def execute(self, project_type: str = "static", _session: AsyncSession | None = None, _agent_id: str | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})

        ws = WebWorkspace(owner_agent_id=_agent_id, project_type=project_type, status="CREATED")
        _session.add(ws)
        await _session.commit()
        await _session.refresh(ws)

        mgr = WebWorkspaceManager()
        path = str(mgr.ensure_workspace(ws.id))
        return json.dumps({"workspace_id": ws.id, "project_type": ws.project_type, "path": path, "status": ws.status})


class WebWorkspaceWriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_workspace_write_file"

    @property
    def description(self) -> str:
        return "Write a file inside a web workspace."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["workspace_id", "file_path", "content"],
        }

    async def execute(self, workspace_id: str, file_path: str, content: str, _session: AsyncSession | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})

        ws = await _session.get(WebWorkspace, workspace_id)
        if not ws:
            return json.dumps({"error": "workspace not found"})

        mgr = WebWorkspaceManager()
        full_path = mgr.write_file(workspace_id, file_path, content)
        return json.dumps({"status": "ok", "workspace_id": workspace_id, "file_path": file_path, "absolute_path": full_path})


class WebWorkspaceReadFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_workspace_read_file"

    @property
    def description(self) -> str:
        return "Read a file from a web workspace."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["workspace_id", "file_path"],
        }

    async def execute(self, workspace_id: str, file_path: str, _session: AsyncSession | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})
        ws = await _session.get(WebWorkspace, workspace_id)
        if not ws:
            return json.dumps({"error": "workspace not found"})

        mgr = WebWorkspaceManager()
        content = mgr.read_file(workspace_id, file_path)
        return json.dumps({"workspace_id": workspace_id, "file_path": file_path, "content": content})


class WebWorkspaceListFilesTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_workspace_list_files"

    @property
    def description(self) -> str:
        return "List files in a web workspace."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"workspace_id": {"type": "string"}},
            "required": ["workspace_id"],
        }

    async def execute(self, workspace_id: str, _session: AsyncSession | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})
        ws = await _session.get(WebWorkspace, workspace_id)
        if not ws:
            return json.dumps({"error": "workspace not found"})

        mgr = WebWorkspaceManager()
        return json.dumps({"workspace_id": workspace_id, "files": mgr.list_files(workspace_id)})


class WebWorkspaceDeleteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_workspace_delete_file"

    @property
    def description(self) -> str:
        return "Delete a file in a web workspace."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["workspace_id", "file_path"],
        }

    async def execute(self, workspace_id: str, file_path: str, _session: AsyncSession | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})
        ws = await _session.get(WebWorkspace, workspace_id)
        if not ws:
            return json.dumps({"error": "workspace not found"})

        mgr = WebWorkspaceManager()
        mgr.delete_file(workspace_id, file_path)
        return json.dumps({"status": "ok", "workspace_id": workspace_id, "file_path": file_path})


class WebPageDesignerTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_page_designer"

    @property
    def description(self) -> str:
        return "Create a structured page blueprint from a high-level spec."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "spec": {"type": "string"},
                "project_type": {"type": "string", "enum": ["static", "react"], "default": "static"},
            },
            "required": ["spec"],
        }

    async def execute(self, spec: str, project_type: str = "static", **kwargs) -> str:
        blueprint = {
            "project_type": project_type,
            "pages": [
                {
                    "route": "/",
                    "title": "Generated Page",
                    "sections": [
                        {"type": "hero", "content": spec[:180]},
                        {"type": "features", "items": ["Fast", "Responsive", "Accessible"]},
                    ],
                }
            ],
            "styles": {
                "palette": {"bg": "#f6f4ef", "text": "#1f2a37", "accent": "#1f8a70"},
                "font": "'Space Grotesk', sans-serif",
            },
        }
        return json.dumps(blueprint)


class WebPageCodegenTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_page_codegen"

    @property
    def description(self) -> str:
        return "Generate actual web files from a blueprint into a workspace."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "blueprint_json": {"type": "string"},
            },
            "required": ["workspace_id", "blueprint_json"],
        }

    async def execute(self, workspace_id: str, blueprint_json: str, _session: AsyncSession | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})
        ws = await _session.get(WebWorkspace, workspace_id)
        if not ws:
            return json.dumps({"error": "workspace not found"})

        try:
            blueprint = json.loads(blueprint_json)
        except json.JSONDecodeError:
            return json.dumps({"error": "invalid blueprint_json"})

        mgr = WebWorkspaceManager()
        title = (
            blueprint.get("pages", [{}])[0].get("title")
            if isinstance(blueprint.get("pages"), list)
            else "Generated Page"
        ) or "Generated Page"
        hero_text = "Build generated by Assistance"
        try:
            hero_text = blueprint["pages"][0]["sections"][0]["content"]
        except Exception:
            pass

        html = f"""<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title}</title>
    <link rel=\"stylesheet\" href=\"styles.css\" />
  </head>
  <body>
    <main class=\"app\">
      <h1>{title}</h1>
      <p>{hero_text}</p>
    </main>
  </body>
</html>
"""
        css = """body { margin: 0; background: linear-gradient(135deg, #f6f4ef, #dce8e0); color: #1f2a37; font-family: 'Space Grotesk', sans-serif; }
.app { min-height: 100vh; display: grid; place-content: center; padding: 2rem; text-align: center; }
h1 { font-size: clamp(2rem, 6vw, 4rem); margin-bottom: 1rem; }
p { max-width: 68ch; margin: 0 auto; line-height: 1.6; }
"""
        mgr.write_file(workspace_id, "index.html", html)
        mgr.write_file(workspace_id, "styles.css", css)

        ws.status = "BUILDING"
        await _session.commit()
        return json.dumps({"status": "ok", "workspace_id": workspace_id, "files": ["index.html", "styles.css"]})


class WebPreviewLauncherTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_preview_launcher"

    @property
    def description(self) -> str:
        return "Launch a dockerized preview server for a workspace and return URL."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"workspace_id": {"type": "string"}},
            "required": ["workspace_id"],
        }

    async def execute(self, workspace_id: str, _session: AsyncSession | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})
        ws = await _session.get(WebWorkspace, workspace_id)
        if not ws:
            return json.dumps({"error": "workspace not found"})

        try:
            import docker  # type: ignore
        except Exception:
            ws.status = "FAILED"
            await _session.commit()
            return json.dumps({"error": "docker sdk unavailable"})

        mgr = WebWorkspaceManager()
        workspace_dir = str(mgr.ensure_workspace(workspace_id))
        host_port = _find_free_port()

        client = docker.from_env()
        container_name = f"assistance-web-preview-{workspace_id[:8]}"
        try:
            old = client.containers.list(all=True, filters={"name": container_name})
            for c in old:
                c.remove(force=True)

            container = client.containers.run(
                image="python:3.12-alpine",
                command=["python", "-m", "http.server", "4173", "--directory", "/workspace"],
                name=container_name,
                detach=True,
                ports={"4173/tcp": host_port},
                volumes={workspace_dir: {"bind": "/workspace", "mode": "ro"}},
                mem_limit="256m",
                cpu_period=100000,
                cpu_quota=50000,
                network_mode="bridge",
                user="1000:1000",
                read_only=True,
                cap_drop=["ALL"],
                pids_limit=128,
            )
        except Exception as exc:
            ws.status = "FAILED"
            await _session.commit()
            return json.dumps({"error": str(exc)})

        ws.status = "RUNNING"
        ws.preview_container_id = container.id
        ws.entry_url = f"http://127.0.0.1:{host_port}"
        await _session.commit()

        return json.dumps({"workspace_id": workspace_id, "status": ws.status, "entry_url": ws.entry_url})


class WebPreviewStopTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_preview_stop"

    @property
    def description(self) -> str:
        return "Stop preview container for a web workspace."

    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"workspace_id": {"type": "string"}},
            "required": ["workspace_id"],
        }

    async def execute(self, workspace_id: str, _session: AsyncSession | None = None, **kwargs) -> str:
        if _session is None:
            return json.dumps({"error": "DB session required"})
        ws = await _session.get(WebWorkspace, workspace_id)
        if not ws:
            return json.dumps({"error": "workspace not found"})

        if ws.preview_container_id:
            try:
                import docker  # type: ignore
                client = docker.from_env()
                c = client.containers.get(ws.preview_container_id)
                c.stop(timeout=5)
                c.remove(force=True)
            except Exception:
                pass

        ws.status = "STOPPED"
        ws.preview_container_id = None
        await _session.commit()
        return json.dumps({"workspace_id": workspace_id, "status": ws.status})
