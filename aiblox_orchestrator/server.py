from __future__ import annotations

import asyncio
import json
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from aiblox_kb import ChunkCacheRepo, ItemRepo, make_engine, make_session_factory, make_sessionmaker
from aiblox_orchestrator.chunker.registry import InMemoryChunkerRegistry
from aiblox_orchestrator.config.settings import load_settings
from aiblox_orchestrator.orchestrator import Orchestrator, StepRunner
from aiblox_orchestrator.orchestrator.stubs import FakeDSPyRuntime, StubAgentRunner, StubToolRunner, StubValidator
from aiblox_orchestrator.protocol.context import ConversationWindow, ProductProfile, RequestContext, UserInput
from aiblox_orchestrator.protocol.event_sink import EventSink
from aiblox_orchestrator.protocol.events import EventEnvelope
from aiblox_orchestrator.retriever.embedder import DeterministicEmbedder
from aiblox_orchestrator.retriever.retriever import HybridRetriever
from aiblox_orchestrator.router.decision_router import DecisionRouter

app = FastAPI(title="AI Blox Orchestrator")


class WebSocketEventSink(EventSink):
    """Event sink that writes envelopes to a websocket."""

    def __init__(self, websocket: WebSocket, lock: asyncio.Lock) -> None:
        self.websocket = websocket
        self.lock = lock

    async def emit(self, event: EventEnvelope) -> None:
        payload = event.model_dump(mode="json")
        async with self.lock:
            await self.websocket.send_text(json.dumps(payload))


settings = load_settings()
engine = make_engine(settings.db_dsn)
sessionmaker = make_sessionmaker(engine)
session_factory = make_session_factory(sessionmaker)

decision_router = DecisionRouter()
item_repo = ItemRepo(session_factory=session_factory)
chunk_cache_repo = ChunkCacheRepo(session_factory=session_factory)
chunker_registry = InMemoryChunkerRegistry()
embedder = DeterministicEmbedder()
retriever = HybridRetriever(
    item_repo=item_repo,
    chunker_registry=chunker_registry,
    embedder=embedder,
    chunk_cache_repo=chunk_cache_repo,
)
step_runner = StepRunner(
    retriever=retriever,
    dspy_runtime=FakeDSPyRuntime(),
    tool_runner=StubToolRunner(),
    agent_runner=StubAgentRunner(),
    validator=StubValidator(),
)

orchestrator = Orchestrator(
    decision_router=decision_router,
    step_runner=step_runner,
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    send_lock = asyncio.Lock()
    event_sink = WebSocketEventSink(websocket, send_lock)
    active_tasks: Dict[str, asyncio.Task] = {}
    active_contexts: Dict[str, RequestContext] = {}

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await event_sink.emit(
                    EventEnvelope(
                        type="rag.error",
                        request_id="unknown",
                        seq=0,
                        payload={"message": "invalid JSON payload"},
                    )
                )
                continue

            msg_type = message.get("type")
            if msg_type == "rag.request":
                request_id = message.get("request_id") or str(uuid4())
                payload = message.get("payload") or {}
                user_input = UserInput(**payload)
                conversation = ConversationWindow(messages=payload.get("conversation", []))
                product_profile = ProductProfile(**payload.get("product_profile", {})) if payload.get("product_profile") else ProductProfile()
                ctx = RequestContext(request_id=request_id)
                active_contexts[request_id] = ctx
                task = asyncio.create_task(
                    orchestrator.run(
                        ctx=ctx,
                        user_input=user_input,
                        conversation=conversation,
                        product_profile=product_profile,
                        event_sink=event_sink,
                    )
                )
                active_tasks[request_id] = task
            elif msg_type == "rag.cancel":
                request_id = message.get("request_id")
                ctx = active_contexts.get(request_id)
                if ctx:
                    ctx.cancel()
            else:
                await event_sink.emit(
                    EventEnvelope(
                        type="rag.error",
                        request_id=message.get("request_id") or "unknown",
                        seq=0,
                        payload={"message": f"unknown message type: {msg_type}"},
                    )
                )
    except WebSocketDisconnect:
        for ctx in active_contexts.values():
            ctx.cancel()
        for task in active_tasks.values():
            task.cancel()
    finally:
        for task in active_tasks.values():
            if not task.done():
                task.cancel()
