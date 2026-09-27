class ErroServicoExterno(Exception):
    """Falha ao se comunicar com a Open Library ou com a API de metas.

    Convertida em resposta HTTP por um exception handler registrado em ``app.main``.
    """

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
