# 📚 Estante de Leitura API

API principal do projeto **Estante de Leitura**, uma aplicação para organizar livros que você
**quer ler**, **está lendo** e **já leu**, acompanhar o progresso página a página e definir
**metas anuais de leitura**.

A Estante API consome a **[Open Library](https://openlibrary.org/developers/api)** (API externa pública)
para buscar livros, capas e gêneros, e se comunica com a
**[Metas de Leitura API](https://github.com/lucasmelomcg/metas-leitura-api)** (API secundária),
que guarda o histórico de leitura e calcula metas e estatísticas.

> MVP da Sprint de Arquitetura de Software, desenvolvido no **Cenário 2** do enunciado:
> uma API principal e uma API secundária, ambas próprias, mais uma API externa.

---

## 🏛️ Arquitetura

![Arquitetura da aplicação](docs/arquitetura.png)

| Componente | Papel | Tecnologia | Porta |
|---|---|---|---|
| **Estante API** (este repositório) | API principal: autenticação, catálogo, estante, recomendações e repasse de metas | FastAPI + SQLite | 8000 |
| **Metas de Leitura API** | API secundária: leituras concluídas, sessões, metas e estatísticas | FastAPI + SQLite | 8001 |
| **Open Library** | API externa: catálogo de livros | REST pública | — |

### Como os componentes se comunicam

1. O usuário usa a **Estante API** pelo Swagger, autenticado com **JWT**.
2. Para buscar ou adicionar livros, a Estante API consulta a **Open Library** (REST/HTTPS), converte a
   resposta para o seu próprio formato e salva os dados no banco. O usuário **nunca é redirecionado**
   para a Open Library.
3. Algumas mudanças na estante são enviadas automaticamente para a **Metas de Leitura API** (REST,
   protegida pelo cabeçalho `X-API-Key`):
   - avançar `pagina_atual` → `POST /sessoes` (sessão de leitura do dia)
   - marcar como `lido` → `POST /leituras` (conclusão do livro)
   - tirar do status `lido` → `DELETE /leituras/...`
   - remover o livro → `DELETE /leituras/...` e `DELETE /sessoes/...`
4. As rotas `/metas` e `/estatisticas` da Estante API repassam as requisições para a API secundária,
   usando o id do usuário autenticado.

A estante continua funcionando mesmo se a API de metas estiver fora do ar: a falha é registrada no log
e só as rotas de metas e estatísticas retornam `503`.

---

## ✨ Funcionalidades

- **Autenticação JWT**: cadastro, login e rotas protegidas por usuário.
- **Catálogo**: busca de livros na Open Library por título, autor ou ISBN, detalhes da obra com descrição
  e livros populares por gênero.
- **Estante (CRUD)**: adicionar, listar, detalhar, atualizar e remover livros.
  - status `quero_ler`, `lendo`, `lido` ou `abandonado`
  - progresso de leitura em páginas e em porcentagem
  - nota de 1 a 5, resenha e favoritos
- **Listagem avançada**: filtros por status, gênero, favorito e texto (título ou autor), ordenação e paginação.
- **Resumo da estante**: quantidade de livros por status.
- **Classificação automática de gênero**: os assuntos em inglês da Open Library viram gêneros em português
  (Fantasia, Ficção científica, Romance, etc.).
- **Recomendações personalizadas**: descobre o gênero favorito do usuário (favoritos, lidos e notas
  altas pesam mais) e sugere livros populares desse gênero que ainda não estão na estante.
- **Metas e estatísticas** (via API secundária): meta anual de livros e páginas, situação da meta
  (adiantado, no ritmo, atrasado), ritmo necessário por mês, sequência de dias lendo, livros por mês e por gênero.

---

## 🌐 API externa: Open Library

| Item | Detalhe |
|---|---|
| **Site / documentação** | https://openlibrary.org/developers/api |
| **Mantenedor** | Internet Archive (organização sem fins lucrativos) |
| **Custo** | Gratuita |
| **Cadastro / chave** | **Não é necessário.** A aplicação se identifica pelo cabeçalho `User-Agent`, como a Open Library recomenda. |
| **Licença de uso** | Dados bibliográficos abertos. Termos em https://openlibrary.org/developers/licensing. As capas vêm da Covers API, que pede para não fazer downloads em massa. |
| **Limites** | Uso moderado. Sem limite formal para chamadas pontuais como as desta aplicação. |

### Rotas utilizadas

| Rota da Open Library | Usada em | Para quê |
|---|---|---|
| `GET /search.json?q=...&page=...&limit=...&fields=...` | `GET /catalogo/busca` | Buscar livros |
| `GET /search.json?q=key:/works/{id}` | `GET /catalogo/livros/{livro_ref}` e `POST /estante` | Título, autores, páginas, capa e assuntos de uma obra |
| `GET /works/{id}.json` | `GET /catalogo/livros/{livro_ref}` | Descrição da obra |
| `GET /subjects/{assunto}.json?limit=...` | `GET /catalogo/generos/{genero}` e `GET /recomendacoes` | Livros populares de um gênero |
| `https://covers.openlibrary.org/b/id/{id}-M.jpg` | campo `capa_url` | Imagem da capa |

---

## 🛣️ Rotas da Estante API

Documentação interativa (Swagger): **http://localhost:8000/docs**

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| POST | `/auth/registro` | Cria uma conta | — |
| POST | `/auth/login` | Faz login e retorna o token JWT | — |
| GET | `/auth/me` | Dados do usuário logado | ✅ |
| GET | `/catalogo/busca` | Busca livros na Open Library | — |
| GET | `/catalogo/livros/{livro_ref}` | Detalhes de um livro da Open Library | — |
| GET | `/catalogo/generos` | Gêneros disponíveis | — |
| GET | `/catalogo/generos/{genero}` | Livros populares de um gênero | — |
| POST | `/estante` | Adiciona um livro à estante | ✅ |
| GET | `/estante` | Lista com filtros, ordenação e paginação | ✅ |
| GET | `/estante/resumo` | Quantidade de livros por status | ✅ |
| GET | `/estante/{livro_id}` | Detalhes de um livro da estante | ✅ |
| PATCH | `/estante/{livro_id}` | Atualiza status, progresso, nota, resenha ou favorito | ✅ |
| DELETE | `/estante/{livro_id}` | Remove um livro da estante | ✅ |
| GET | `/recomendacoes` | Recomendações personalizadas | ✅ |
| POST | `/metas` | Define a meta do ano → API secundária | ✅ |
| GET | `/metas/{ano}` | Consulta a meta → API secundária | ✅ |
| PUT | `/metas/{ano}` | Altera a meta → API secundária | ✅ |
| DELETE | `/metas/{ano}` | Remove a meta → API secundária | ✅ |
| GET | `/estatisticas?ano=` | Estatísticas e progresso da meta → API secundária | ✅ |
| GET | `/health` | Verifica se a API está no ar | — |

### Parâmetros de `GET /estante`

| Parâmetro | Exemplo | Descrição |
|---|---|---|
| `status` | `lendo` | `quero_ler`, `lendo`, `lido` ou `abandonado` |
| `genero` | `Fantasia` | Gênero (não diferencia maiúsculas) |
| `favorito` | `true` | Só os favoritos |
| `busca` | `tolkien` | Trecho do título ou do autor |
| `ordenar_por` | `titulo` | `adicionado_em`, `atualizado_em`, `titulo` ou `nota` |
| `ordem` | `asc` | `asc` ou `desc` |
| `pagina` / `tamanho` | `1` / `10` | Paginação (tamanho máximo 50) |

---

## 🚀 Como executar

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e Docker Compose
- [Git](https://git-scm.com/)
- (Opcional, para rodar sem Docker) [Python 3.12+](https://www.python.org/downloads/)

### Opção 1: Docker Compose (recomendada, sobe as duas APIs)

O `docker-compose.yml` fica na raiz deste repositório e espera o repositório da API secundária
**clonado ao lado** deste, na mesma pasta:

```bash
mkdir estante-de-leitura && cd estante-de-leitura
git clone https://github.com/lucasmelomcg/estante-api.git
git clone https://github.com/lucasmelomcg/metas-leitura-api.git

cd estante-api
docker compose up --build
```

A estrutura fica assim:

```
estante-de-leitura/
├── estante-api/          ← docker-compose.yml aqui
└── metas-leitura-api/
```

Pronto:

- Estante API: http://localhost:8000/docs
- Metas de Leitura API: http://localhost:8001/docs

Para parar: `docker compose down`. Para também apagar os bancos: `docker compose down -v`.

### Opção 2: só o Dockerfile deste repositório

```bash
docker build -t estante-api .
docker run -d --name estante-api -p 8000:8000 \
  -e METAS_API_URL=http://host.docker.internal:8001 \
  -e METAS_API_KEY=chave-interna-dev \
  -v estante-dados:/app/data \
  estante-api
```

> Nesse caso a Metas de Leitura API precisa estar rodando na porta 8001 da sua máquina
> (veja o README dela).

### Opção 3: localmente, sem Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # ajuste as variáveis se quiser
uvicorn app.main:app --reload --port 8000
```

### Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/estante.db` | Conexão com o banco |
| `JWT_SECRET` | *(valor de desenvolvimento)* | Chave de assinatura dos tokens. **Troque em produção.** |
| `JWT_EXPIRACAO_MINUTOS` | `480` | Validade do token |
| `OPEN_LIBRARY_URL` | `https://openlibrary.org` | URL da API externa |
| `METAS_API_URL` | `http://localhost:8001` | URL da API secundária |
| `METAS_API_KEY` | `chave-interna-dev` | Chave enviada no cabeçalho `X-API-Key` (igual à `API_KEY` da API secundária) |

---

## 🧪 Roteiro rápido no Swagger

1. `POST /auth/registro` com `{"nome": "Ana", "email": "ana@email.com", "senha": "senhaSegura123"}`
2. Clique em **Authorize** e informe `ana@email.com` / `senhaSegura123`
3. `GET /catalogo/busca?q=dom casmurro` e copie o `livro_ref` (ex.: `OL1003040W`)
4. `POST /estante` com `{"livro_ref": "OL1003040W", "status": "lendo"}`
5. `PATCH /estante/1` com `{"pagina_atual": 120}` (registra uma sessão na API de metas)
6. `POST /metas` com `{"ano": 2026, "meta_livros": 12}`
7. `PATCH /estante/1` com `{"status": "lido", "nota": 5}` (registra a conclusão)
8. `GET /estatisticas?ano=2026` para ver o progresso da meta
9. `GET /recomendacoes` para ver sugestões do seu gênero favorito
10. `DELETE /estante/1` para remover o livro e o histórico dele

---

## ✅ Testes automatizados

```bash
pip install -r requirements-dev.txt
pytest
```

Nos testes, a Open Library e a API de metas são substituídas por versões falsas, então eles rodam
sem internet.

---

## 📁 Estrutura do projeto

```
estante-api/
├── app/
│   ├── main.py               # criação da aplicação FastAPI e registro das rotas
│   ├── config.py             # configurações (variáveis de ambiente)
│   ├── database.py           # conexão SQLAlchemy
│   ├── models.py             # tabelas: usuarios e livros_estante
│   ├── excecoes.py           # erro de comunicação com serviços externos
│   ├── routers/              # rotas (auth, catalogo, estante, recomendacoes, metas)
│   ├── schemas/              # modelos Pydantic de entrada e saída
│   └── services/
│       ├── open_library.py   # cliente da API externa
│       ├── metas_client.py   # cliente da API secundária
│       ├── generos.py        # tradução de assuntos para gêneros
│       └── seguranca.py      # hash de senha e JWT
├── tests/                    # testes com pytest
├── docs/arquitetura.png      # fluxograma da arquitetura
├── Dockerfile
├── docker-compose.yml        # sobe a Estante API e a Metas de Leitura API
├── requirements.txt
└── requirements-dev.txt
```

---

## 🧰 Tecnologias

Python 3.12 · FastAPI · SQLAlchemy 2 · SQLite · Pydantic 2 · HTTPX · PyJWT · bcrypt · Pytest · Docker
