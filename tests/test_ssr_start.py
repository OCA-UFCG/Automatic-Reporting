import socket

from utils import ssr


def test_nao_sobe_segundo_node_se_a_porta_ja_responde(monkeypatch):
    monkeypatch.setattr(ssr, "_porta_ocupada", lambda: True)
    chamou = []
    monkeypatch.setattr(ssr.subprocess, "Popen", lambda *a, **k: chamou.append(a))

    assert ssr.start_server() is None
    assert chamou == []


def test_porta_ocupada_detecta_listener_real():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        porta = s.getsockname()[1]
        assert ssr._porta_ocupada(porta) is True
    assert ssr._porta_ocupada(porta) is False
