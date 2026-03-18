import json
import socket
from contextlib import closing

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.web_workspace import WebWorkspace
from app.services.web_workspace_manager import WebWorkspaceManager

router = APIRouter(prefix="/web-workspaces")


class CreateWorkspaceRequest(BaseModel):
    project_type: str = "static"


class FileWriteRequest(BaseModel):
    file_path: str
    content: str


class DesignRequest(BaseModel):
    spec: str


class CodegenRequest(BaseModel):
    blueprint_json: str


def _find_free_port(start: int = 8400, end: int = 8999) -> int:
    for port in range(start, end + 1):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free preview ports available")


def _workspace_response(item: WebWorkspace) -> dict:
    mgr = WebWorkspaceManager()
    files = mgr.list_files(item.id)
    return {
        "id": item.id,
        "owner_agent_id": item.owner_agent_id,
        "project_type": item.project_type,
        "status": item.status,
        "entry_url": item.entry_url,
        "preview_container_id": item.preview_container_id,
        "files": files,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.post("")
async def create_web_workspace(req: CreateWorkspaceRequest, session: AsyncSession = Depends(get_session)):
    ws = WebWorkspace(project_type=req.project_type, status="CREATED")
    session.add(ws)
    await session.commit()
    await session.refresh(ws)

    mgr = WebWorkspaceManager()
    mgr.ensure_workspace(ws.id)
    return _workspace_response(ws)


@router.get("")
async def list_web_workspaces(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(select(WebWorkspace).order_by(WebWorkspace.created_at.desc()))
    items = rows.scalars().all()
    return [
        {
            "id": w.id,
            "owner_agent_id": w.owner_agent_id,
            "project_type": w.project_type,
            "status": w.status,
            "entry_url": w.entry_url,
            "created_at": w.created_at,
            "updated_at": w.updated_at,
        }
        for w in items
    ]


@router.get("/{workspace_id}")
async def get_web_workspace(workspace_id: str, session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    return _workspace_response(item)


@router.post("/{workspace_id}/files")
async def write_workspace_file(workspace_id: str, req: FileWriteRequest, session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    mgr = WebWorkspaceManager()
    full_path = mgr.write_file(workspace_id, req.file_path, req.content)
    return {
        "status": "ok",
        "workspace_id": workspace_id,
        "file_path": req.file_path,
        "absolute_path": full_path,
    }


@router.get("/{workspace_id}/file")
async def read_workspace_file(workspace_id: str, path: str = Query(...), session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    mgr = WebWorkspaceManager()
    try:
        content = mgr.read_file(workspace_id, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found")
    return {"workspace_id": workspace_id, "file_path": path, "content": content}


@router.delete("/{workspace_id}/file")
async def delete_workspace_file(workspace_id: str, path: str = Query(...), session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    mgr = WebWorkspaceManager()
    mgr.delete_file(workspace_id, path)
    return {"status": "ok", "workspace_id": workspace_id, "file_path": path}


@router.post("/{workspace_id}/design")
async def design_workspace(workspace_id: str, req: DesignRequest, session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    blueprint = {
        "project_type": item.project_type,
        "pages": [
            {
                "route": "/",
                "title": "Generated Page",
                "sections": [
                    {"type": "hero", "content": req.spec[:180]},
                    {"type": "features", "items": ["Fast", "Responsive", "Accessible"]},
                ],
            }
        ],
        "styles": {
            "palette": {"bg": "#f6f4ef", "text": "#1f2a37", "accent": "#1f8a70"},
            "font": "'Space Grotesk', sans-serif",
        },
    }
    return blueprint


@router.post("/{workspace_id}/codegen")
async def codegen_workspace(workspace_id: str, req: CodegenRequest, session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    try:
        blueprint = json.loads(req.blueprint_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid blueprint_json")

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

    item.status = "BUILDING"
    await session.commit()
    return {"status": "ok", "workspace_id": workspace_id, "files": ["index.html", "styles.css"]}


@router.post("/{workspace_id}/preview/start")
async def start_workspace_preview(workspace_id: str, session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    try:
        import docker  # type: ignore
    except Exception:
        item.status = "FAILED"
        await session.commit()
        raise HTTPException(status_code=503, detail="docker unavailable")

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
        item.status = "FAILED"
        await session.commit()
        raise HTTPException(status_code=500, detail=str(exc))

    item.status = "RUNNING"
    item.preview_container_id = container.id
    item.entry_url = f"http://127.0.0.1:{host_port}"
    await session.commit()
    return _workspace_response(item)


@router.post("/{workspace_id}/preview/stop")
async def stop_workspace_preview(workspace_id: str, session: AsyncSession = Depends(get_session)):
    item = await session.get(WebWorkspace, workspace_id)
    if not item:
        raise HTTPException(status_code=404, detail="workspace not found")

    if item.preview_container_id:
        try:
            import docker  # type: ignore
            client = docker.from_env()
            c = client.containers.get(item.preview_container_id)
            c.stop(timeout=5)
            c.remove(force=True)
        except Exception:
            pass

    item.status = "STOPPED"
    item.preview_container_id = None
    await session.commit()
    return _workspace_response(item)
