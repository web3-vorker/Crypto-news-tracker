import asyncio
import os

from fastapi import FastAPI
import uvicorn

from app.main import main as collector_main
from utils.logger import logger


app = FastAPI()

_collector_task: asyncio.Task | None = None
_collector_started_at: float | None = None


@app.on_event("startup")
async def on_startup():
    global _collector_task, _collector_started_at

    import time
    _collector_started_at = time.time()

    # Запускаем твой while-True цикл сбора новостей как фоновую задачу.
    # FastAPI/uvicorn держит открытый HTTP-порт (это формальное требование
    # Render для Web Service), а реальная работа крутится в _collector_task.
    _collector_task = asyncio.create_task(_run_collector_with_restart())


async def _run_collector_with_restart():
    # Если collector_main() вдруг упадёт с необработанным исключением,
    # не даём всему процессу умереть — логируем и перезапускаем через паузу.
    while True:
        try:
            await collector_main()
        except Exception as e:
            logger.error(f"[WORKER] collector crashed, restarting in 30s: {e}")
            await asyncio.sleep(30)


@app.get("/")
@app.get("/health")
async def health():
    is_alive = _collector_task is not None and not _collector_task.done()
    return {
        "status": "ok" if is_alive else "collector_dead",
        "collector_running": is_alive,
        "started_at": _collector_started_at,
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("app.worker_service:app", host="0.0.0.0", port=port)