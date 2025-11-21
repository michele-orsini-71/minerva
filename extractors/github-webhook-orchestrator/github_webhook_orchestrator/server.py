import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from .config import WebhookConfig, load_config
from .github_auth import validate_signature
from .reindex import detect_markdown_changes, execute_reindex


app = FastAPI(title="GitHub Webhook Orchestrator")
config: Optional[WebhookConfig] = None
logger = logging.getLogger(__name__)


def initialize_logging(log_file: str):
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)


@app.get("/health")
async def health_check():
    return JSONResponse(
        content={"status": "healthy", "timestamp": datetime.utcnow().isoformat()},
        status_code=status.HTTP_200_OK
    )


@app.post("/webhook")
async def webhook_handler(request: Request):
    if config is None:
        logger.error("Server not configured")
        return JSONResponse(
            content={"error": "Server not configured"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    body = await request.body()
    signature_header = request.headers.get('X-Hub-Signature-256', '')

    # Validate signature on the raw body (before any decoding)
    if not validate_signature(body, signature_header, config.webhook_secret):
        logger.warning("Invalid signature received")
        return JSONResponse(
            content={"error": "Invalid signature"},
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Handle URL-encoded payload (GitHub form-encoded webhooks)
    payload_body = body
    if body.startswith(b'payload='):
        from urllib.parse import unquote_plus
        # Extract and decode the payload parameter
        payload_body = unquote_plus(body.decode('utf-8')[8:]).encode('utf-8')

    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        logger.error(f"Received body (first 500 chars): {body[:500].decode('utf-8', errors='replace')}")
        return JSONResponse(
            content={"error": "Invalid JSON payload"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    event_type = request.headers.get('X-GitHub-Event', '')

    if event_type != 'push':
        logger.info(f"Ignoring event type: {event_type}")
        return JSONResponse(
            content={"message": f"Ignored event type: {event_type}"},
            status_code=status.HTTP_200_OK
        )

    repo_name = payload.get('repository', {}).get('name', '')
    if not repo_name:
        logger.error("No repository name in payload")
        return JSONResponse(
            content={"error": "No repository name in payload"},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    repo_config = None
    for repo in config.repositories:
        if repo.name == repo_name:
            repo_config = repo
            break

    if repo_config is None:
        logger.info(f"Repository not configured: {repo_name}")
        return JSONResponse(
            content={"message": f"Repository not configured: {repo_name}"},
            status_code=status.HTTP_200_OK
        )

    commits = payload.get('commits', [])

    if not detect_markdown_changes(commits):
        logger.info(f"No markdown changes detected in {repo_name}")
        return JSONResponse(
            content={"message": "No markdown changes detected"},
            status_code=status.HTTP_200_OK
        )

    logger.info(f"Markdown changes detected in {repo_name}, triggering reindex")

    success = execute_reindex(repo_config)

    if success:
        logger.info(f"Reindex completed successfully for {repo_name}")
        return JSONResponse(
            content={"message": "Reindex completed successfully"},
            status_code=status.HTTP_200_OK
        )
    else:
        logger.error(f"Reindex failed for {repo_name}")
        return JSONResponse(
            content={"error": "Reindex failed"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def main(config_path: str, host: str = "127.0.0.1", port: int = 8338):
    global config

    config = load_config(config_path)
    initialize_logging(config.log_file)

    logger.info(f"Starting webhook orchestrator with {len(config.repositories)} repositories")
    for repo in config.repositories:
        logger.info(f"  - {repo.name}: {repo.local_path}")

    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
