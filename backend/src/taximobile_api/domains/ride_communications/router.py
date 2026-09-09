from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import (
    CurrentPrincipal,
    authenticated_principal,
)
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.notifications.service import notify
from taximobile_api.domains.outbox.service import enqueue
from taximobile_api.domains.ride_communications.models import (
    RideCoordinationMessage,
)
from taximobile_api.domains.ride_communications.policy import (
    RideCoordinationClosed,
    RideCoordinationCodeForbidden,
    RideCoordinationForbidden,
    RideCoordinationLimitReached,
    RideCoordinationNotFound,
    compatibility_copy,
    enforce_sender_limit,
    participant_context,
    sender_role_for_code,
)
from taximobile_api.domains.ride_communications.schemas import (
    RideCoordinationCreateRequest,
    RideCoordinationMessageResponse,
)


router = APIRouter(tags=["ride communications"])


def message_response(
    message: RideCoordinationMessage,
) -> RideCoordinationMessageResponse:
    return RideCoordinationMessageResponse(
        id=message.id,
        ride_id=message.ride_id,
        sender_role=sender_role_for_code(message.code),
        code=message.code,
        created_at=message.created_at,
    )


@router.post(
    "/rides/{ride_id}/messages",
    response_model=RideCoordinationMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_coordination_message(
    ride_id: UUID,
    payload: RideCoordinationCreateRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> RideCoordinationMessageResponse:
    try:
        async with session.begin():
            command = await begin_command(
                session,
                user_id=principal.user_id,
                operation="ride.coordination.send",
                key=idempotency_key,
                payload={"ride_id": str(ride_id), "code": payload.code.value},
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(
                    status_code=command.status_code,
                    content=command.payload,
                )
            context = await participant_context(
                session,
                ride_id=ride_id,
                user_id=principal.user_id,
                lock=True,
            )
            if sender_role_for_code(payload.code) != context.sender_role:
                raise RideCoordinationCodeForbidden(
                    "This coordination signal is not available to your ride role."
                )
            if not await request.app.state.rate_limiter.allow(
                f"ride-message:{principal.user_id}:{ride_id}",
                limit=request.app.state.settings.ride_message_rate_limit_per_minute,
                window_seconds=60,
            ):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many ride updates. Try again shortly.",
                )
            await enforce_sender_limit(
                session,
                ride_id=ride_id,
                sender_user_id=principal.user_id,
            )
            message = RideCoordinationMessage(
                ride_id=ride_id,
                sender_user_id=principal.user_id,
                code=payload.code,
            )
            session.add(message)
            await session.flush()
            title, body = compatibility_copy(payload.code)
            await notify(
                session,
                user_id=context.recipient_user_id,
                notification_type=payload.code.value,
                title=title,
                body=body,
                data={"ride_id": str(ride_id), "message_id": str(message.id)},
            )
            await enqueue(
                session,
                topic="ride.coordination.message",
                payload={"message_id": str(message.id)},
            )
            response = message_response(message)
            await finish_command(
                session,
                command,
                status_code=status.HTTP_201_CREATED,
                payload=response.model_dump(mode="json"),
            )
    except RideCoordinationNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RideCoordinationForbidden as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot coordinate this ride.",
        ) from error
    except (
        RideCoordinationClosed,
        RideCoordinationCodeForbidden,
        RideCoordinationLimitReached,
    ) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response
