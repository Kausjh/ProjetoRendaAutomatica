# 63.8738, -149.7525

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol

from repositories.controle_administrativo_repository import (
    MODO_OPERACAO_PADRAO,
    MODOS_OPERACAO_PUBLICACAO,
    PONTUACAO_MINIMA_AUTOMATICA_HIBRIDO,
    ControleAdministrativoRepository,
)
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from services.controle.estado import (
    EstadoAdministrativo,
    EstadoConectividade,
    EstadoFila,
    EstadoProcesso,
)
from services.controle.politica_publicacao_administrativa import (
    requer_aprovacao_hibrida,
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

    def _modo_operacao(self) -> str:
        if self.repositorio_admin is None:
            return MODO_OPERACAO_PADRAO

        return self.repositorio_admin.obter_modo_operacao()

    def _intervalo_previsao_publicacao(self) -> float:
        if self.repositorio_admin is None:
            return 130.0

        valor = self.repositorio_admin.obter_estado(
            "intervalo_previsao_publicacao_segundos",
            "130",
        )

        try:
            return max(1.0, float(valor or 130.0))
        except (TypeError, ValueError):
            return 130.0

    def _proxima_previsao_base(
        self,
        agora: datetime,
    ) -> datetime:
        if self.repositorio_admin is None:
            return agora

        valor = self.repositorio_admin.obter_estado(
            "proxima_publicacao_estimada_em",
        )

        if not valor:
            return agora

        try:
            prevista = datetime.fromisoformat(valor)
        except ValueError:
            return agora

        if prevista.tzinfo is None or prevista.utcoffset() is None:
            return agora

        prevista_local = prevista.astimezone()

        return max(agora, prevista_local)

    def obter_operacao(self) -> dict[str, object]:
        modo = self._modo_operacao()

        publicador_pausado = bool(
            getattr(
                self.orquestrador,
                "publicador_pausado",
                False,
            )
        )
        pipeline_ativo = self._estado_processo(self.orquestrador.processo_pipeline).ativo
        publicador_ativo = self._estado_processo(self.orquestrador.processo_publicador).ativo
        bot_ativo = self._estado_processo(self.orquestrador.processo_bot).ativo

        proxima_publicacao_estimada_em = None

        if publicador_ativo and not publicador_pausado:
            fila = self.listar_fila(limite=100)

            previsoes: list[datetime] = []

            for item in fila["itens"]:
                valor = item.get("previsao_publicacao")

                if not valor:
                    continue

                try:
                    previsao = datetime.fromisoformat(str(valor))
                except ValueError:
                    continue

                if previsao.tzinfo is None or previsao.utcoffset() is None:
                    continue

                previsoes.append(previsao.astimezone())

            if previsoes:
                proxima_publicacao_estimada_em = min(previsoes).isoformat(timespec="seconds")

        return {
            "publicador_pausado": publicador_pausado,
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
            "pipeline_ativo": pipeline_ativo,
            "publicador_ativo": publicador_ativo,
            "bot_ativo": bot_ativo,
            "modo_operacao": modo,
            "pontuacao_minima_automatica_hibrido": (PONTUACAO_MINIMA_AUTOMATICA_HIBRIDO),
            "proxima_publicacao_estimada_em": (proxima_publicacao_estimada_em),
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

        agora = datetime.now().astimezone()
        modo = self._modo_operacao()
        intervalo_previsao = self._intervalo_previsao_publicacao()
        proxima_base = self._proxima_previsao_base(agora)
        indice_automatico = 0

        resultado: list[dict[str, object]] = []

        for ordem, item in enumerate(itens, start=1):
            oferta = item.oferta
            requer_aprovacao = requer_aprovacao_hibrida(
                item=item,
                modo=modo,
            )

            segurado_futuro = item.segurado_ate is not None and item.segurado_ate > agora

            previsao: datetime | None
            tipo_previsao: str
            estado_agenda: str

            if item.agendado_para is not None:
                candidatos = [
                    agora,
                    item.agendado_para,
                ]

                if segurado_futuro and item.segurado_ate is not None:
                    candidatos.append(item.segurado_ate)

                previsao = max(candidatos)
                tipo_previsao = "agendado"
                estado_agenda = "agendado"
            elif segurado_futuro:
                previsao = item.segurado_ate
                tipo_previsao = "liberacao_estimada"
                estado_agenda = "segurado"
            elif modo == "manual":
                previsao = None
                tipo_previsao = "manual"
                estado_agenda = "aguardando_manual"
            elif requer_aprovacao:
                previsao = None
                tipo_previsao = "aprovacao"
                estado_agenda = "aguardando_aprovacao"
            else:
                previsao = proxima_base + timedelta(
                    seconds=intervalo_previsao * indice_automatico,
                )
                indice_automatico += 1
                tipo_previsao = "estimado"
                estado_agenda = "liberado"

            segundos_para_previsao = (
                max(0, int((previsao - agora).total_seconds())) if previsao is not None else None
            )

            resultado.append(
                {
                    "id": item.id,
                    "ordem": ordem,
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
                    "segurado_ate": (
                        item.segurado_ate.isoformat() if item.segurado_ate is not None else None
                    ),
                    "agendado_para": (
                        item.agendado_para.isoformat() if item.agendado_para is not None else None
                    ),
                    "aprovado_manualmente": item.aprovado_manualmente,
                    "requer_aprovacao_hibrida": requer_aprovacao,
                    "estado_agenda": estado_agenda,
                    "previsao_publicacao": (
                        previsao.isoformat(timespec="seconds") if previsao is not None else None
                    ),
                    "tipo_previsao": tipo_previsao,
                    "segundos_para_previsao": segundos_para_previsao,
                    "criado_em": item.criado_em.isoformat(),
                    "atualizado_em": item.atualizado_em.isoformat(),
                    "status": item.status,
                }
            )

        return {
            "quantidade": len(resultado),
            "modo_operacao": modo,
            "intervalo_previsao_segundos": intervalo_previsao,
            "itens": resultado,
        }

    def executar_acao_fila(
        self,
        item_id: int,
        acao: str,
        dispositivo: str | None = None,
        agendar_para: str | None = None,
    ) -> dict[str, object]:
        if item_id <= 0:
            raise ValueError("ID do item precisa ser maior que zero.")

        detalhes: dict[str, object] | None = None

        acoes_simples = {
            "adiantar": self.fila.adiantar_item,
            "adiar": self.fila.adiar_item,
            "descartar": self.fila.descartar_administrativamente,
            "publicar-agora": self.fila.solicitar_publicacao_imediata,
            "liberar": self.fila.liberar_item,
            "aprovar": self.fila.aprovar_item,
            "revisar": self.fila.revisar_item,
        }

        retencoes = {
            "segurar-5": 5,
            "segurar-15": 15,
            "segurar-30": 30,
            "segurar-60": 60,
        }

        try:
            if acao in acoes_simples:
                executado = acoes_simples[acao](item_id)
            elif acao in retencoes:
                minutos = retencoes[acao]
                executado = self.fila.segurar_item(
                    item_id,
                    minutos,
                )
                detalhes = {
                    "minutos": minutos,
                }
            elif acao == "agendar":
                if not agendar_para:
                    raise ValueError("Parametro 'para' e obrigatorio para agendar.")

                try:
                    horario = datetime.fromisoformat(
                        agendar_para.strip(),
                    )
                except ValueError as erro:
                    raise ValueError(
                        "Parametro 'para' precisa ser um horario ISO 8601 valido."
                    ) from erro

                executado = self.fila.agendar_item(
                    item_id,
                    horario,
                )
                detalhes = {
                    "agendado_para": horario.astimezone().isoformat(timespec="seconds"),
                }
            else:
                self._auditar(
                    acao=f"fila.{acao}",
                    alvo=str(item_id),
                    detalhes=None,
                    dispositivo=dispositivo,
                    resultado="acao_invalida",
                )
                raise ValueError(f"Acao administrativa desconhecida: {acao}.")
        except ValueError:
            if acao != "agendar":
                raise

            self._auditar(
                acao=f"fila.{acao}",
                alvo=str(item_id),
                detalhes={
                    "agendado_para": agendar_para,
                },
                dispositivo=dispositivo,
                resultado="dados_invalidos",
            )
            raise

        if not executado:
            self._auditar(
                acao=f"fila.{acao}",
                alvo=str(item_id),
                detalhes=detalhes,
                dispositivo=dispositivo,
                resultado="item_indisponivel",
            )
            raise ValueError("Item nao encontrado ou nao esta mais pendente.")

        self._auditar(
            acao=f"fila.{acao}",
            alvo=str(item_id),
            detalhes=detalhes,
            dispositivo=dispositivo,
            resultado="sucesso",
        )

        return {
            "sucesso": True,
            "item_id": item_id,
            "acao": acao,
            "detalhes": detalhes,
            "fila": self.listar_fila(limite=100),
            "executado_em": (datetime.now().astimezone().isoformat(timespec="seconds")),
        }

    def executar_acao_operacional(
        self,
        componente: str,
        acao: str,
        dispositivo: str | None = None,
    ) -> dict[str, object]:
        nome_acao = f"operacao.{componente}.{acao}"

        if componente == "modo":
            if acao not in MODOS_OPERACAO_PUBLICACAO:
                self._auditar(
                    acao=nome_acao,
                    alvo="modo",
                    detalhes=None,
                    dispositivo=dispositivo,
                    resultado="acao_invalida",
                )
                raise ValueError("Modo de operacao desconhecido.")

            if self.repositorio_admin is None:
                raise ValueError("Repositorio administrativo indisponivel.")

            anterior = self.repositorio_admin.obter_modo_operacao()
            self.repositorio_admin.definir_modo_operacao(acao)

            resultado_operacao = "mantido" if anterior == acao else f"alterado_para_{acao}"

            self._auditar(
                acao=nome_acao,
                alvo="modo",
                detalhes={
                    "anterior": anterior,
                    "novo": acao,
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

        acoes = {
            ("publicador", "pausar"): (self.orquestrador.pausar_publicador),
            ("publicador", "retomar"): (self.orquestrador.retomar_publicador),
            ("pipeline", "executar"): (self.orquestrador.solicitar_pipeline_imediato),
            ("bot", "reiniciar"): (self.orquestrador.reiniciar_bot_administrativamente),
            ("chrome", "reiniciar"): (self.orquestrador.solicitar_reinicio_chrome),
        }

        funcao = acoes.get((componente, acao))

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

    def obter_agenda(
        self,
        limite: int = 100,
    ) -> dict[str, object]:
        fila = self.listar_fila(
            limite=limite,
        )
        operacao = self.obter_operacao()

        itens = [
            {
                "id": item["id"],
                "ordem": item["ordem"],
                "nome": item["nome"],
                "pontuacao": item["pontuacao"],
                "prioridade": item["prioridade"],
                "estado_agenda": item["estado_agenda"],
                "segurado_ate": item["segurado_ate"],
                "agendado_para": item["agendado_para"],
                "previsao_publicacao": item["previsao_publicacao"],
                "tipo_previsao": item["tipo_previsao"],
                "segundos_para_previsao": item["segundos_para_previsao"],
                "aprovado_manualmente": item["aprovado_manualmente"],
                "requer_aprovacao_hibrida": (item["requer_aprovacao_hibrida"]),
            }
            for item in fila["itens"]
        ]

        return {
            "modo_operacao": fila["modo_operacao"],
            "pontuacao_minima_automatica_hibrido": (PONTUACAO_MINIMA_AUTOMATICA_HIBRIDO),
            "intervalo_previsao_segundos": (fila["intervalo_previsao_segundos"]),
            "proxima_publicacao_estimada_em": (operacao["proxima_publicacao_estimada_em"]),
            "quantidade": len(itens),
            "itens": itens,
            "coletado_em": (datetime.now().astimezone().isoformat(timespec="seconds")),
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
