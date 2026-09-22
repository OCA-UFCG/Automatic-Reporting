import socket

from utils import ssr


def test_nao_sobe_segundo_node_se_a_porta_ja_responde(monkeypatch):
    monkeypatch.setattr(ssr, "_porta_ocupada", lambda: True)
    chamou = []
    monkeypatch.setattr(ssr.subprocess, "Popen", lambda *a, **k: chamou.append(a))

    assert ssr.start_server() is None
    assert chamou == []


def test_porta_ocupada_true_com_listener_ativo():
    """Com alguém de fato ouvindo na porta, _porta_ocupada deve enxergar True."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        porta = s.getsockname()[1]
        assert ssr._porta_ocupada(porta) is True


def test_porta_ocupada_false_com_porta_reservada_sem_listen():
    """Um bind sem listen() reserva a porta mas não aceita conexão: a porta
    está "tomada" no sentido de bind, porém não há ninguém ouvindo, e
    _porta_ocupada deve responder False. É exatamente essa distinção que
    justifica usar connect_ex em vez de bind na implementação: um checador
    baseado em bind reportaria True aqui e, fora do Docker, deixaria a app
    sem servidor de SSR nenhum rodando, silenciosamente.

    Segurar o socket aberto (sem listen) durante o assert também impede que o
    kernel devolva essa porta como porta de origem efêmera para o socket de
    cliente que _porta_ocupada abre internamente — o que eliminaria o
    self-connect (client:P -> server:P) que tornava a versão anterior deste
    teste instável.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
        assert ssr._porta_ocupada(porta) is False
