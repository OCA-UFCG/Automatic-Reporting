"""Onde os contratos publicados ficam guardados.

O armazenamento é **append-only**: publicar nunca apaga a versão anterior, só
acrescenta uma nova e arquiva a antiga em ``historico/``. Isso é o que permite
desfazer uma edição infeliz sem depender de backup — e é a razão de a tabela
futura no Postgres também ser append-only (docs/PLANO-PAINEL-EDITORIAL.md §2).

Hoje a implementação é de arquivos, em ``output/contratos/``. A troca para o
schema próprio no Postgres muda **apenas esta classe**: o adaptador, o painel e
o pipeline conversam com a interface, não com o disco.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.editorial.contrato import exigir_contrato_valido

_NOME_SEGURO = re.compile(r"^[a-z0-9-]+$")


class ConflitoDeVersao(RuntimeError):
    """Alguém publicou uma versão nova enquanto esta edição estava aberta.

    Sem lock e sem edição colaborativa ao vivo: quem chega depois é recusado e
    vê o que mudou, em vez de sobrescrever o trabalho do outro em silêncio.
    """

    def __init__(self, versao_esperada: int | None, versao_atual: int, autor: str | None):
        self.versao_esperada = versao_esperada
        self.versao_atual = versao_atual
        self.autor = autor
        por = f" por {autor}" if autor else ""
        super().__init__(
            f"O contrato já está na versão {versao_atual} (publicada{por}); "
            f"esta edição partiu da versão {versao_esperada}. "
            "Recarregue e reaplique a alteração."
        )


class RepositorioDeContratos:
    """Contratos em arquivos JSON, com histórico ao lado."""

    def __init__(self, diretorio: Path) -> None:
        self.diretorio = Path(diretorio)

    # -- caminhos ---------------------------------------------------------

    def _validar_slug(self, slug: str) -> str:
        # O slug vem da URL e vira nome de arquivo; sem isso, "../../etc" é um
        # caminho válido.
        if not _NOME_SEGURO.match(slug):
            raise ValueError(f"Slug inválido: {slug!r}")
        return slug

    def caminho(self, slug: str) -> Path:
        return self.diretorio / f"{self._validar_slug(slug)}.json"

    def caminho_historico(self, slug: str, versao: int) -> Path:
        return self.diretorio / "historico" / self._validar_slug(slug) / f"{versao:04d}.json"

    # -- leitura ----------------------------------------------------------

    def existe(self, slug: str) -> bool:
        return self.caminho(slug).exists()

    def ler(self, slug: str) -> dict[str, Any] | None:
        caminho = self.caminho(slug)
        if not caminho.exists():
            return None
        return json.loads(caminho.read_text(encoding="utf-8"))

    def metadados(self, slug: str) -> dict[str, Any] | None:
        """Só o cabeçalho: o painel lista oito temas sem carregar oito árvores."""
        contrato = self.ler(slug)
        if contrato is None:
            return None
        return {
            "versao": contrato.get("versao"),
            "publicado_em": contrato.get("publicado_em"),
            "publicado_por": contrato.get("publicado_por"),
            "blocos": len(contrato.get("corpo", {}).get("blocos", [])),
        }

    def historico(self, slug: str) -> list[dict[str, Any]]:
        pasta = self.diretorio / "historico" / self._validar_slug(slug)
        if not pasta.exists():
            return []
        versoes = []
        for arquivo in sorted(pasta.glob("*.json"), reverse=True):
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            versoes.append(
                {
                    "versao": dados.get("versao"),
                    "publicado_em": dados.get("publicado_em"),
                    "publicado_por": dados.get("publicado_por"),
                }
            )
        return versoes

    def ler_versao(self, slug: str, versao: int) -> dict[str, Any] | None:
        caminho = self.caminho_historico(slug, versao)
        if not caminho.exists():
            atual = self.ler(slug)
            return atual if atual and atual.get("versao") == versao else None
        return json.loads(caminho.read_text(encoding="utf-8"))

    # -- escrita ----------------------------------------------------------

    def publicar(
        self,
        slug: str,
        contrato: dict[str, Any],
        autor: str,
        versao_esperada: int | None = None,
    ) -> dict[str, Any]:
        """Valida, confere a versão, arquiva a anterior e grava a nova.

        ``versao_esperada`` é a versão que o painel tinha em mãos quando o
        editor começou a mexer. Se não bate com a publicada, ninguém sobrescreve
        ninguém: levanta :class:`ConflitoDeVersao`.
        """
        exigir_contrato_valido(contrato)

        atual = self.ler(slug)
        if atual is not None:
            versao_atual = atual.get("versao", 0)
            if versao_esperada is not None and versao_esperada != versao_atual:
                raise ConflitoDeVersao(
                    versao_esperada, versao_atual, atual.get("publicado_por")
                )
            self.caminho_historico(slug, versao_atual).parent.mkdir(
                parents=True, exist_ok=True
            )
            self.caminho_historico(slug, versao_atual).write_text(
                json.dumps(atual, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            proxima = versao_atual + 1
        else:
            proxima = 1

        publicado = dict(contrato)
        publicado["versao"] = proxima
        publicado["publicado_em"] = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        publicado["publicado_por"] = autor

        caminho = self.caminho(slug)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        # Escreve num temporário e renomeia: um processo lendo o contrato
        # durante a publicação vê a versão velha inteira, nunca meio arquivo.
        temporario = caminho.with_suffix(".json.tmp")
        temporario.write_text(
            json.dumps(publicado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        temporario.replace(caminho)
        return publicado
