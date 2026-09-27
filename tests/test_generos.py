from app.services.generos import inferir_genero


def test_genero_especifico_vence_o_generico():
    assert inferir_genero(["Fiction", "Fantasy", "Dragons"]) == "Fantasia"


def test_ficcao_antes_de_historia():
    assert inferir_genero(["Fiction", "History and criticism"]) == "Ficção"


def test_sem_assuntos():
    assert inferir_genero([]) == "Outros"
    assert inferir_genero(None) == "Outros"
