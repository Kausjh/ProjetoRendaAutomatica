# 63.8738, -149.7525

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from services.controle.estado import (
    EstadoAdministrativo,
    EstadoConectividade,
    EstadoFila,
    EstadoProcesso,
)
from services.launcher.chrome_launcher import cdp_esta_funcional

if TYPE_CHECKING:
    from services.runtime.orquestrador import OrquestradorRuntime


class ProcessoGerenciado(Protocol):
    pid: int

    def poll(self) -> int | None: ...


class ControladorAdministrativo:
    """Expõe o estado operacional do runtime sem duplicar sua lógica."""

    def __init__(
        self,
        orquestrador: OrquestradorRuntime,
        fila: FilaPublicacaoRepository | None = None,
        verificador_chrome: Callable[[], bool] | None = None,
    ) -> None:
        self.orquestrador = orquestrador
        self.fila = fila or FilaPublicacaoRepository()
        self.verificador_chrome = verificador_chrome or cdp_esta_funcional

    @staticmethod
    def _estado_processo(
        processo: ProcessoGerenciado | None,
    ) -> EstadoProcesso:
        if processo is None:
            return EstadoProcesso(ativo=False, pid=None)

        ativo = processo.poll() is None

        return EstadoProcesso(
            ativo=ativo,
            pid=processo.pid if ativo else None,
        )

    def obter_saude(self) -> dict[str, object]:
        estado = self.obter_estado()

        try:
            chrome_funcional = bool(self.verificador_chrome())
        except Exception:
            chrome_funcional = False

        componentes = {
            "runtime": estado.runtime_ativo,
            "pipeline": estado.pipeline.ativo,
            "publicador": estado.publicador.ativo,
            "bot": estado.bot.ativo,
            "internet": estado.conectividade.internet,
            "telegram": estado.conectividade.telegram,
            "mercado_livre": estado.conectividade.mercado_livre,
            "chrome_cdp": chrome_funcional,
        }

        essenciais = (
            "runtime",
            "publicador",
            "bot",
            "internet",
            "telegram",
            "mercado_livre",
            "chrome_cdp",
        )

        saudavel = all(componentes[nome] for nome in essenciais)

        return {
            "saudavel": saudavel,
            "componentes": componentes,
            "coletado_em": estado.coletado_em,
        }

    def obter_metricas(self) -> dict[str, object]:
        publicacoes_24h = self.fila.historico_publicacoes_recentes(
            minutos=1440.0,
            limite=1000,
        )

        publicacoes_1h = self.fila.historico_publicacoes_recentes(
            minutos=60.0,
            limite=1000,
        )

        resumo_fila = self.fila.resumo_familias_pendentes()

        pontuacoes = [
            float(item["pontuacao"])
            for item in publicacoes_24h
            if item.get("pontuacao") is not None
        ]

        pontuacao_media = (
            round(
                sum(pontuacoes) / len(pontuacoes),
                2,
            )
            if pontuacoes
            else None
        )

        categorias = Counter(
            str(item["categoria"]) for item in publicacoes_24h if item.get("categoria")
        )

        categorias_mais_publicadas = [
            {
                "categoria": categoria,
                "quantidade": quantidade,
            }
            for categoria, quantidade in categorias.most_common(10)
        ]

        ultima_publicacao = publicacoes_24h[0] if publicacoes_24h else None

        return {
            "publicacoes_24h": len(publicacoes_24h),
            "publicacoes_1h": len(publicacoes_1h),
            "fila_pendente": resumo_fila["itens"],
            "familias_pendentes": resumo_fila["familias"],
            "pontuacao_media_24h": pontuacao_media,
            "ultima_publicacao": ultima_publicacao,
            "categorias_mais_publicadas": (categorias_mais_publicadas),
            "coletado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        }

    def listar_fila(self, limite: int = 50) -> dict[str, object]:
        limite = max(1, min(limite, 100))
        itens = self.fila.listar_pendentes(limite=limite)

        resultado: list[dict[str, object]] = []

        for item in itens:
            oferta = item.oferta

            resultado.append(
                {
                    "id": item.id,
                    "nome": oferta.nome,
                    "loja": oferta.loja,
                    "preco": float(oferta.preco),
                    "preco_antigo": (
                        float(oferta.preco_antigo) if oferta.preco_antigo is not None else None
                    ),
                    "link": oferta.link,
                    "imagem": oferta.imagem,
                    "marketplace": getattr(
                        oferta,
                        "marketplace",
                        None,
                    ),
                    "categoria": getattr(
                        oferta,
                        "categoria",
                        None,
                    ),
                    "marca": getattr(
                        oferta,
                        "marca",
                        None,
                    ),
                    "pontuacao": float(item.pontuacao),
                    "prioridade": float(item.prioridade),
                    "deve_republicar_por_queda": (item.deve_republicar_por_queda),
                    "criado_em": item.criado_em.isoformat(),
                    "atualizado_em": item.atualizado_em.isoformat(),
                    "status": item.status,
                }
            )

        return {
            "quantidade": len(resultado),
            "itens": resultado,
        }

    def listar_publicacoes(
        self,
        minutos: float = 1440.0,
        limite: int = 50,
    ) -> dict[str, object]:
        minutos = max(1.0, minutos)
        limite = max(1, min(limite, 100))

        itens = self.fila.historico_publicacoes_recentes(
            minutos=minutos,
            limite=limite,
        )

        return {
            "quantidade": len(itens),
            "periodo_minutos": minutos,
            "itens": itens,
        }

    def obter_estado(self) -> EstadoAdministrativo:
        resumo_fila = self.fila.resumo_familias_pendentes()

        conectividade = EstadoConectividade(
            internet=self.orquestrador.internet_disponivel(),
            telegram=self.orquestrador.telegram_disponivel(),
            mercado_livre=self.orquestrador.mercado_livre_disponivel(),
        )

        return EstadoAdministrativo(
            runtime_ativo=not self.orquestrador._encerrando,
            runtime_pid=os.getpid(),
            encerrando=self.orquestrador._encerrando,
            pipeline=self._estado_processo(self.orquestrador.processo_pipeline),
            publicador=self._estado_processo(self.orquestrador.processo_publicador),
            bot=self._estado_processo(self.orquestrador.processo_bot),
            fila=EstadoFila(
                pendentes=resumo_fila["itens"],
                familias=resumo_fila["familias"],
                itens_com_familia=resumo_fila["itens_com_familia"],
            ),
            conectividade=conectividade,
            coletado_em=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
