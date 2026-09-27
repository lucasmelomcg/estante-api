import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.database import Base, engine
from app.excecoes import ErroServicoExterno
from app.routers import auth, catalogo, estante, metas, recomendacoes

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

DESCRICAO = """
API principal do projeto **Estante de Leitura** 📚

Organize os livros que você quer ler, está lendo e já leu, acompanhe o progresso de
leitura e defina metas anuais.

### Como usar pelo Swagger
1. Crie uma conta em `POST /auth/registro`.
2. Clique em **Authorize** e faça login (e-mail no campo *username*).
3. Busque livros em `GET /catalogo/busca` e adicione-os com `POST /estante`.
4. Atualize o progresso com `PATCH /estante/{livro_id}` e acompanhe em `GET /estatisticas`.

### Componentes
* **Open Library** (API externa): catálogo de livros, capas e gêneros.
* **Metas de Leitura API** (API secundária): histórico, metas e estatísticas.
"""

TAGS = [
    {"name": "Autenticação", "description": "Cadastro e login com JWT."},
    {"name": "Catálogo (Open Library)", "description": "Consulta à API externa Open Library."},
    {"name": "Minha estante", "description": "CRUD dos livros do usuário."},
    {"name": "Recomendações", "description": "Sugestões baseadas no gosto do usuário."},
    {
        "name": "Metas e estatísticas",
        "description": "Rotas que se comunicam com a API secundária (Metas de Leitura API).",
    },
    {"name": "Saúde", "description": "Monitoramento."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Estante de Leitura API",
    description=DESCRICAO,
    version="1.0.0",
    openapi_tags=TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErroServicoExterno)
async def tratar_erro_servico_externo(_: Request, erro: ErroServicoExterno):
    return JSONResponse(status_code=erro.status_code, content={"detail": erro.detail})


app.include_router(auth.router)
app.include_router(catalogo.router)
app.include_router(estante.router)
app.include_router(recomendacoes.router)
app.include_router(metas.router)


@app.get("/", include_in_schema=False)
def raiz():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Saúde"], summary="Verifica se a API está no ar")
def health():
    return {"status": "ok"}
