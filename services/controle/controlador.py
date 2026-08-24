# 63.8738, -149.7525

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
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
        repositorio_admin: ControleAdministrativoRepository | None = None,
    ) -> None:
        self.orquestrador = orquestrador
        self.fila = fila or FilaPublicacaoRepository()
        self.verificador_chrome = verificador_chrome or cdp_esta_funcional
        self.repositorio_admin = repositorio_admin

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

    def _auditar(
        self,
        acao: str,
        alvo: str | None,
        detalhes: dict[str, object] | None,
        dispositivo: str | None,
        resultado: str,
    ) -> None:
        if self.repositorio_admin is None:
            return

        self.repositorio_admin.registrar_auditoria(
            acao=acao,
            alvo=alvo,
            detalhes=detalhes,
            dispositivo=dispositivo,
            resultado=resultado,
        )

    def obter_operacao(self) -> dict[str, object]:
        return {
            "publicador_pausado": bool(
                getattr(
                    self.orquestrador,
                    "publicador_pausado",
                    False,
                )
            ),
            "pipeline_imediato_pendente": bool(
                getattr(
                    self.orquestrador,
                    "pipeline_imediato_pendente",
                    False,
                )
            ),
            "reinicio_chrome_em_andamento": bool(
                getattr(
                    self.orquestrador,
                    "reinicio_chrome_em_andamento",
                    False,
                )
            ),
            "pipeline_ativo": (self._estado_processo(self.orquestrador.processo_pipeline).ativo),
            "publicador_ativo": (
                self._estado_processo(self.orquestrador.processo_publicador).ativo
            ),
            "bot_ativo": (self._estado_processo(self.orquestrador.processo_bot).ativo),
            "coletado_em": (datetime.now().astimezone().isoformat(timespec="seconds")),
        }

    def listar_auditoria(
        self,
        limite: int = 50,
    ) -> dict[str, object]:
        if self.repositorio_admin is None:
            return {
                "quantidade": 0,
                "itens": [],
            }

        itens = self.repositorio_admin.listar_auditoria(
            limite=limite,
        )

        return {
            "quantidade": len(itens),
            "itens": itens,
        }

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

    def executar_acao_fila(
        self,
        item_id: int,
        acao: str,
        dispositivo: str | None = None,
    ) -> dict[str, object]:
        if item_id <= 0:
            raise ValueError("ID do item precisa ser maior que zero.")

        acoes = {
            "adiantar": self.fila.adiantar_item,
            "adiar": self.fila.adiar_item,
            "descartar": (self.fila.descartar_administrativamente),
            "publicar-agora": (self.fila.solicitar_publicacao_imediata),
        }

        funcao = acoes.get(acao)

        if funcao is None:
            self._auditar(
                acao=f"fila.{acao}",
                alvo=str(item_id),
                detalhes=None,
                dispositivo=dispositivo,
                resultado="acao_invalida",
            )
            raise ValueError(f"Acao administrativa desconhecida: {acao}.")

        executado = funcao(item_id)

        if not executado:
            self._auditar(
                acao=f"fila.{acao}",
                alvo=str(item_id),
                detalhes=None,
                dispositivo=dispositivo,
                resultado="item_indisponivel",
            )
            raise ValueError("Item nao encontrado ou nao esta mais pendente.")

        self._auditar(
            acao=f"fila.{acao}",
            alvo=str(item_id),
            detalhes=None,
            dispositivo=dispositivo,
            resultado="sucesso",
        )

        return {
            "sucesso": True,
            "item_id": item_id,
            "acao": acao,
            "fila": self.listar_fila(limite=100),
            "executado_em": (datetime.now().astimezone().isoformat(timespec="seconds")),
        }

    def executar_acao_operacional(
        self,
        componente: str,
        acao: str,
        dispositivo: str | None = None,
    ) -> dict[str, object]:
        acoes = {
            ("publicador", "pausar"): (self.orquestrador.pausar_publicador),
            ("publicador", "retomar"): (self.orquestrador.retomar_publicador),
            ("pipeline", "executar"): (self.orquestrador.solicitar_pipeline_imediato),
            ("bot", "reiniciar"): (self.orquestrador.reiniciar_bot_administrativamente),
            ("chrome", "reiniciar"): (self.orquestrador.solicitar_reinicio_chrome),
        }

        funcao = acoes.get((componente, acao))
        nome_acao = f"operacao.{componente}.{acao}"

        if funcao is None:
            self._auditar(
                acao=nome_acao,
                alvo=componente,
                detalhes=None,
                dispositivo=dispositivo,
                resultado="acao_invalida",
            )
            raise ValueError("Acao operacional desconhecida.")

        try:
            resultado_operacao = str(funcao())
        except Exception as erro:
            self._auditar(
                acao=nome_acao,
                alvo=componente,
                detalhes={
                    "erro": type(erro).__name__,
                },
                dispositivo=dispositivo,
                resultado="erro",
            )
            raise

        self._auditar(
            acao=nome_acao,
            alvo=componente,
            detalhes={
                "resultado_operacao": resultado_operacao,
            },
            dispositivo=dispositivo,
            resultado="sucesso",
        )

        return {
            "sucesso": True,
            "componente": componente,
            "acao": acao,
            "resultado": resultado_operacao,
            "operacao": self.obter_operacao(),
            "executado_em": (datetime.now().astimezone().isoformat(timespec="seconds")),
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
