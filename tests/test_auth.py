def test_registro_login_e_me(client):
    registro = client.post(
        "/auth/registro",
        json={"nome": "Ana", "email": "Ana@Email.com", "senha": "senhaSegura123"},
    )
    assert registro.status_code == 201
    assert registro.json()["email"] == "ana@email.com"
    assert "senha" not in registro.json()

    login = client.post("/auth/login", data={"username": "ana@email.com", "password": "senhaSegura123"})
    assert login.status_code == 200

    token = login.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["nome"] == "Ana"


def test_email_duplicado(client):
    dados = {"nome": "Ana", "email": "ana@email.com", "senha": "senhaSegura123"}
    client.post("/auth/registro", json=dados)
    assert client.post("/auth/registro", json=dados).status_code == 409


def test_login_com_senha_errada(client):
    client.post("/auth/registro", json={"nome": "Ana", "email": "ana@email.com", "senha": "senhaSegura123"})
    resposta = client.post("/auth/login", data={"username": "ana@email.com", "password": "errada123"})
    assert resposta.status_code == 401


def test_rotas_protegidas_exigem_token(client):
    assert client.get("/estante").status_code == 401
    assert client.get("/estante", headers={"Authorization": "Bearer invalido"}).status_code == 401
