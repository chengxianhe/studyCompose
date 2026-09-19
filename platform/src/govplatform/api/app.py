from __future__ import annotations

from fastapi import FastAPI

from govplatform.api.routes.contract import router as contract_router
from govplatform.api.routes.knowledge import router as knowledge_router


def create_app() -> FastAPI:
    app = FastAPI(title="govplatform", version="0.1.0")
    app.include_router(knowledge_router)
    app.include_router(contract_router)
    return app


app = create_app()
