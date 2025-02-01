from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .utils.markdown_parser import EndpointParser

router = APIRouter()

# Configurar templates e arquivos estáticos
templates = Jinja2Templates(directory="src/web/templates")
static_path = Path("src/web/static")

# Carregar e parsear endpoints
with open("docs/http_endpoints.md", "r", encoding='utf-8') as f:
    parser = EndpointParser(f.read())
    endpoints_data = parser.parse()

# Montar arquivos estáticos
router.mount("/static", StaticFiles(directory=static_path), name="static")

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/endpoints/{section}")
async def endpoints(request: Request, section: str):
    if section not in endpoints_data:
        return templates.TemplateResponse("endpoints.html", {
            "request": request,
            "section_title": "Seção não encontrada",
            "section_description": "",
            "endpoints": []
        })
        
    data = endpoints_data[section]
    return templates.TemplateResponse("endpoints.html", {
        "request": request,
        "section_title": data["title"],
        "section_description": data.get("description", ""),
        "endpoints": data["endpoints"]
    })

@router.get("/auth")
async def auth_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})

# Adicionar mais rotas para outras páginas... 