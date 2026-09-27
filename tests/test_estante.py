def _adicionar(cliente, livro_ref="OL1003040W", **extra):
    return cliente.post("/estante", json={"livro_ref": livro_ref, **extra})


def test_busca_no_catalogo(client):
    resposta = client.get("/catalogo/busca", params={"q": "dom"})
    assert resposta.status_code == 200
    assert resposta.json()["livros"][0]["livro_ref"] == "OL1003040W"


def test_adicionar_livro_copia_dados_da_open_library(autenticado):
    resposta = _adicionar(autenticado)

    assert resposta.status_code == 201
    livro = resposta.json()
    assert livro["titulo"] == "Dom Casmurro"
    assert livro["autores"] == "Machado de Assis"
    assert livro["status"] == "quero_ler"
    assert livro["progresso_percentual"] == 0.0


def test_nao_adiciona_duplicado_nem_inexistente(autenticado):
    _adicionar(autenticado)
    assert _adicionar(autenticado).status_code == 409
    assert _adicionar(autenticado, "OL999W").status_code == 404
    assert _adicionar(autenticado, "invalido").status_code == 422


def test_progresso_registra_sessao_e_muda_status(autenticado, metas_falsa):
    livro_id = _adicionar(autenticado).json()["id"]

    resposta = autenticado.patch(f"/estante/{livro_id}", json={"pagina_atual": 134})

    assert resposta.json()["status"] == "lendo"
    assert resposta.json()["progresso_percentual"] == 50.0
    assert metas_falsa.chamadas == [("registrar_sessao", "OL1003040W", 134)]


def test_pagina_maior_que_o_livro(autenticado):
    livro_id = _adicionar(autenticado).json()["id"]
    assert autenticado.patch(f"/estante/{livro_id}", json={"pagina_atual": 999}).status_code == 422


def test_concluir_e_reabrir_livro_sincroniza_metas(autenticado, metas_falsa):
    livro_id = _adicionar(autenticado, status="lendo").json()["id"]
    autenticado.patch(f"/estante/{livro_id}", json={"pagina_atual": 200})

    concluido = autenticado.patch(f"/estante/{livro_id}", json={"status": "lido", "nota": 5}).json()
    assert concluido["pagina_atual"] == 268
    assert concluido["concluido_em"] is not None

    reaberto = autenticado.patch(f"/estante/{livro_id}", json={"status": "lendo"}).json()
    assert reaberto["concluido_em"] is None

    assert metas_falsa.chamadas == [
        ("registrar_sessao", "OL1003040W", 200),
        ("registrar_sessao", "OL1003040W", 68),
        ("registrar_leitura", "OL1003040W", 5),
        ("remover_leitura", "OL1003040W"),
    ]


def test_remover_livro_limpa_historico(autenticado, metas_falsa):
    livro_id = _adicionar(autenticado).json()["id"]

    assert autenticado.delete(f"/estante/{livro_id}").status_code == 204
    assert autenticado.get(f"/estante/{livro_id}").status_code == 404
    assert metas_falsa.chamadas == [
        ("remover_leitura", "OL1003040W"),
        ("remover_sessoes", "OL1003040W"),
    ]


def test_listagem_com_filtros_ordenacao_e_paginacao(autenticado):
    _adicionar(autenticado)
    id_senhor_dos_aneis = _adicionar(autenticado, "OL27448W").json()["id"]
    autenticado.patch(f"/estante/{id_senhor_dos_aneis}", json={"favorito": True, "nota": 5})

    por_genero = autenticado.get("/estante", params={"genero": "fantasia"}).json()
    assert [livro["titulo"] for livro in por_genero["itens"]] == ["The Lord of the Rings"]

    por_autor = autenticado.get("/estante", params={"busca": "machado"}).json()
    assert por_autor["total"] == 1

    por_titulo = autenticado.get("/estante", params={"ordenar_por": "titulo", "ordem": "asc"}).json()
    assert [livro["titulo"] for livro in por_titulo["itens"]] == ["Dom Casmurro", "The Lord of the Rings"]

    pagina = autenticado.get("/estante", params={"tamanho": 1, "pagina": 2}).json()
    assert pagina["total"] == 2
    assert pagina["total_paginas"] == 2
    assert len(pagina["itens"]) == 1

    resumo = autenticado.get("/estante/resumo").json()
    assert resumo == {"total": 2, "quero_ler": 2, "lendo": 0, "lido": 0, "abandonado": 0, "favoritos": 1}


def test_usuario_nao_ve_livro_de_outro(autenticado, client):
    livro_id = _adicionar(autenticado).json()["id"]

    client.post("/auth/registro", json={"nome": "Bia", "email": "bia@email.com", "senha": "senhaSegura123"})
    token = client.post(
        "/auth/login", data={"username": "bia@email.com", "password": "senhaSegura123"}
    ).json()["access_token"]

    resposta = client.get(f"/estante/{livro_id}", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 404


def test_recomendacoes_usam_genero_preferido(autenticado):
    livro_id = _adicionar(autenticado, "OL27448W").json()["id"]
    autenticado.patch(f"/estante/{livro_id}", json={"favorito": True})

    recomendacoes = autenticado.get("/recomendacoes", params={"limite": 3}).json()

    assert recomendacoes["genero_base"] == "Fantasia"
    assert len(recomendacoes["livros"]) == 3


def test_criar_meta_repassa_para_api_de_metas(autenticado, metas_falsa):
    resposta = autenticado.post("/metas", json={"ano": 2026, "meta_livros": 24})

    assert resposta.status_code == 201
    assert resposta.json()["meta_livros"] == 24
    assert metas_falsa.chamadas == [("criar_meta", 2026, 24)]
