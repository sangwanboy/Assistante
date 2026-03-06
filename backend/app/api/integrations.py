"""REST API for External Channel Integrations (Omnichannel)."""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.models.integration import ExternalIntegration
from app.schemas.integration import IntegrationCreate, IntegrationUpdate, IntegrationOut
from app.services.omnichannel.manager import OmnichannelManager

router = APIRouter()


def _get_manager() -> OmnichannelManager:
    return OmnichannelManager.get_instance()


@router.get("", response_model=List[IntegrationOut])
async def list_integrations(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ExternalIntegration).order_by(ExternalIntegration.created_at))
    return result.scalars().all()


@router.post("", response_model=IntegrationOut)
async def create_integration(
    body: IntegrationCreate,
    session: AsyncSession = Depends(get_session),
):
    integration = ExternalIntegration(
        name=body.name,
        platform=body.platform,
        config_json=json.dumps(body.config),
        agent_id=body.agent_id,
        is_active=body.is_active,
    )
    session.add(integration)
    await session.commit()
    await session.refresh(integration)

    # Start adapter if active
    if integration.is_active:
        manager = _get_manager()
        await manager.start_adapter(integration.id, integration.platform, body.config)

    return integration


@router.put("/{integration_id}", response_model=IntegrationOut)
async def update_integration(
    integration_id: str,
    body: IntegrationUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ExternalIntegration).where(ExternalIntegration.id == integration_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    if body.name is not None:
        integration.name = body.name
    if body.config is not None:
        integration.config_json = json.dumps(body.config)
    if body.agent_id is not None:
        integration.agent_id = body.agent_id
    if body.is_active is not None:
        integration.is_active = body.is_active

    await session.commit()
    await session.refresh(integration)

    # Restart adapter with new config
    manager = _get_manager()
    await manager.stop_adapter(integration_id)
    if integration.is_active and body.config:
        await manager.start_adapter(
            integration.id, integration.platform, json.loads(integration.config_json)
        )

    return integration


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ExternalIntegration).where(ExternalIntegration.id == integration_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    manager = _get_manager()
    await manager.stop_adapter(integration_id)

    await session.delete(integration)
    await session.commit()
    return {"ok": True}


# ── Webhook endpoints for platforms that push events ──────────────────────────

@router.post("/{integration_id}/webhook/slack")
async def slack_webhook(integration_id: str, request: Request):
    """Receive Slack Events API payloads."""
    payload = await request.json()
    # Slack URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    manager = _get_manager()
    await manager.handle_webhook(integration_id, payload=payload)
    return {"ok": True}


@router.post("/{integration_id}/webhook/whatsapp")
async def whatsapp_webhook(integration_id: str, request: Request):
    """Receive Twilio WhatsApp form-encoded payloads."""
    form = await request.form()
    manager = _get_manager()
    await manager.handle_webhook(integration_id, form_data=dict(form))
    return {"ok": True}


@router.post("/{integration_id}/webhook/whatsapp_web")
async def whatsapp_web_webhook(integration_id: str, request: Request):
    """Receive JSON payloads from the custom whatsapp-service."""
    payload = await request.json()
    manager = _get_manager()
    await manager.handle_webhook(integration_id, payload=payload)
    return {"ok": True}
