from unittest.mock import patch

from config import DB_STATEMENT_TIMEOUT_MS
from utils.database import get_connection


def test_get_connection_sets_connect_and_statement_timeout():
    # Guard do CLAUDE.md: a conexão precisa sempre levar um statement_timeout de
    # sessão (via `options` libpq), senão uma vw_perfil_* lenta pendura o worker.
    with patch("utils.database.psycopg2.connect") as mock_connect:
        get_connection()

    _, kwargs = mock_connect.call_args
    assert kwargs["connect_timeout"] == 5
    assert kwargs["options"] == f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}"
    assert DB_STATEMENT_TIMEOUT_MS == 15000
