"""The stable v1 router; domain routers are added here as their contracts exist."""

from fastapi import APIRouter
from pydantic import BaseModel

from taximobile_api.domains.auth.router import router as auth_router
from taximobile_api.domains.administration.router import router as administration_router
from taximobile_api.domains.drivers.router import router as drivers_router
from taximobile_api.domains.rides.router import router as rides_router
from taximobile_api.domains.rides.offers_router import router as offers_router
from taximobile_api.domains.payments.router import router as payments_router
from taximobile_api.domains.support.router import router as support_router
from taximobile_api.domains.notifications.router import router as notifications_router
from taximobile_api.domains.routing.router import router as routing_router
from taximobile_api.domains.cooperatives.router import router as cooperatives_router


class ApiMetadata(BaseModel):
    service: str
    version: str


router = APIRouter()
router.include_router(auth_router)
router.include_router(administration_router)
router.include_router(drivers_router)
router.include_router(rides_router)
router.include_router(offers_router)
router.include_router(payments_router)
router.include_router(support_router)
router.include_router(notifications_router)
router.include_router(routing_router)
router.include_router(cooperatives_router)


@router.get("/meta", response_model=ApiMetadata, tags=["system"])
async def metadata() -> ApiMetadata:
    return ApiMetadata(service="taximobile-api", version="v1")
