from fastapi import APIRouter, Query
from typing import List, Optional
import os
import re
from datetime import datetime

router = APIRouter()

LOG_DIR = "/workspace/logs"

@router.get("/logs")
async def get_logs(
    service: str = Query("all", description="Serviço para filtrar logs"),
    limit: int = Query(100, description="Número máximo de linhas"),
    level: Optional[str] = Query(None, description="Filtrar por nível de log")
):
    logs = []
    log_files = {
        "api": "api.log",
        "comfyui": "comfyui.log",
        "system": "setup.log"
    }

    files_to_read = (
        [log_files[service]] if service in log_files
        else log_files.values() if service == "all"
        else []
    )

    for log_file in files_to_read:
        file_path = os.path.join(LOG_DIR, log_file)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                lines = f.readlines()[-limit:]
                for line in lines:
                    # Extrair timestamp e nível do log
                    match = re.match(r'\[(.*?)\].*?(\w+):(.*)', line)
                    if match:
                        timestamp, log_level, message = match.groups()
                        if not level or log_level.upper() == level.upper():
                            logs.append({
                                "timestamp": timestamp.strip(),
                                "level": log_level.strip(),
                                "message": message.strip()
                            })

    return {"logs": sorted(logs, key=lambda x: x["timestamp"])} 