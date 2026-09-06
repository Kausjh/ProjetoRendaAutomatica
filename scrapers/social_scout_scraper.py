# 63.8738, -149.7525

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict

from models.mensagem_social_scout import (
    MensagemSocialScout,
)
from models.oferta import Oferta
from repositories.mensagens_social_scout_repository import (
    MensagensSocialScoutRepository,
)
from repositories.processamentos_social_scout_repository import (
    ProcessamentosSocialScoutRepository,
)
from scrapers.base_scraper import BaseScraper
from services.classificador_produto import (
    ClassificadorProduto,
)
from services.scout.construtor_oferta_social_scout import (
    ConstrutorOfertaSocialScout,
)
from services.scout.detector_promocao_social_scout import (
    DetectorPromocaoSocialScout,
)
from services.scout.social_scout_destino_resolver import (
    ResolvedorDestinoSocialScout,
)
from services.scout.validador_preco_ml_social_scout import (
    ValidadorPrecoMercadoLivreSocialScout,
)

logger = logging.getLogger(__name__)


class SocialScoutScraper(BaseScraper):
    """
    Adapta mensagens capturadas pelo Social Scout para o
    contrato normal de scraper do ProjetoRendaAutomatica.

    Modo normal:
        ofertas validadas sao devolvidas ao ColetorOfertas.

    Modo sombra:
        a mensagem percorre deteccao, resolucao, validacao,
        construcao e classificacao, mas nenhuma Oferta sai
        deste scraper.

    Mensagens que chegaram a um estado terminal nao sao
    reabertas em cada ciclo.

    Uma edicao muda o fingerprint e permite novo processamento.

    Mudancas futuras importantes podem incrementar
    VERSAO_PROCESSADOR.
    """

    VERSAO_PROCESSADOR = "1"

    def __init__(
        self,
        repository: MensagensSocialScoutRepository | None = None,
        processamentos_repository: ProcessamentosSocialScoutRepository | None = None,
        detector=None,
        resolvedor=None,
        validador_preco=None,
        construtor=None,
        max_mensagens_por_execucao: int = 30,
        modo_sombra: bool = False,
        classificador_sombra: ClassificadorProduto | None = None,
    ) -> None:
        self.repository = repository or MensagensSocialScoutRepository()

        self.processamentos_repository = (
            processamentos_repository or ProcessamentosSocialScoutRepository()
        )

        self.detector = detector or DetectorPromocaoSocialScout()

        self.resolvedor = resolvedor or ResolvedorDestinoSocialScout()

        self.validador_preco = validador_preco or ValidadorPrecoMercadoLivreSocialScout()

        self.construtor = construtor or ConstrutorOfertaSocialScout()

        self.max_mensagens_por_execucao = max(
            int(max_mensagens_por_execucao),
            1,
        )

        self.modo_sombra = bool(modo_sombra)

        if classificador_sombra is not None:
            self.classificador_sombra = classificador_sombra

        elif self.modo_sombra:
            self.classificador_sombra = ClassificadorProduto()

        else:
            self.classificador_sombra = None

    def buscar_ofertas(
        self,
        limite: int = 5,
    ) -> list[Oferta]:
        limite = max(
            int(limite),
            0,
        )

        if limite <= 0:
            return []

        mensagens = self.repository.listar()

        if not mensagens:
            return []

        mensagens_recentes = list(reversed(mensagens))[: self.max_mensagens_por_execucao]

        ofertas: list[Oferta] = []
        chaves_vistas: set[str] = set()

        ignoradas_processadas = 0
        erros_transitorios = 0

        candidatas_sombra = 0
        nicho_sombra = 0
        fora_nicho_sombra = 0

        for mensagem in mensagens_recentes:
            if self.modo_sombra:
                if candidatas_sombra >= limite:
                    break

            elif len(ofertas) >= limite:
                break

            fingerprint = self._fingerprint_mensagem(mensagem)

            if self.processamentos_repository.esta_processada(
                mensagem,
                self.VERSAO_PROCESSADOR,
                fingerprint,
            ):
                ignoradas_processadas += 1
                continue

            try:
                deteccao = self.detector.detectar(mensagem)

                if deteccao.classificacao != DetectorPromocaoSocialScout.OFERTA_PRODUTO:
                    self._marcar_terminal(
                        mensagem=mensagem,
                        fingerprint=fingerprint,
                        status="ignorada",
                        motivo=(deteccao.motivo or deteccao.classificacao),
                    )
                    continue

                if deteccao.marketplace != "mercado_livre":
                    self._marcar_terminal(
                        mensagem=mensagem,
                        fingerprint=fingerprint,
                        status="nao_suportada",
                        motivo=("marketplace_nao_suportado:" f"{deteccao.marketplace}"),
                    )
                    continue

                resolucao = self.resolvedor.resolver(
                    mensagem,
                    deteccao,
                )

                if resolucao.status == "erro":
                    erros_transitorios += 1
                    continue

                if resolucao.status != "resolvido":
                    self._marcar_terminal(
                        mensagem=mensagem,
                        fingerprint=fingerprint,
                        status="nao_resolvida",
                        motivo=resolucao.motivo,
                    )
                    continue

                validacao = self.validador_preco.validar(
                    deteccao,
                    resolucao,
                )

                if validacao.status == "erro":
                    erros_transitorios += 1
                    continue

                if validacao.status != "validado":
                    self._marcar_terminal(
                        mensagem=mensagem,
                        fingerprint=fingerprint,
                        status="preco_rejeitado",
                        motivo=validacao.motivo,
                    )
                    continue

                construcao = self.construtor.construir(
                    deteccao,
                    resolucao,
                    validacao,
                )

                if (
                    construcao.status != ConstrutorOfertaSocialScout.STATUS_CRIADA
                    or construcao.oferta is None
                ):
                    self._marcar_terminal(
                        mensagem=mensagem,
                        fingerprint=fingerprint,
                        status="construcao_rejeitada",
                        motivo=construcao.motivo,
                    )
                    continue

                oferta = construcao.oferta

                chave = self._chave_oferta(oferta)

                if chave in chaves_vistas:
                    self._marcar_terminal(
                        mensagem=mensagem,
                        fingerprint=fingerprint,
                        status="duplicada",
                        motivo=("produto_duplicado_na_mesma_execucao"),
                    )
                    continue

                chaves_vistas.add(chave)

                if self.modo_sombra:
                    candidatas_sombra += 1

                    status_sombra = self._processar_sombra(
                        mensagem=mensagem,
                        fingerprint=fingerprint,
                        oferta=oferta,
                    )

                    if status_sombra == "sombra_nicho":
                        nicho_sombra += 1

                    else:
                        fora_nicho_sombra += 1

                    # Trava central:
                    # nenhuma Oferta em sombra sai do scraper.
                    continue

                self._marcar_terminal(
                    mensagem=mensagem,
                    fingerprint=fingerprint,
                    status="emitida",
                    motivo=("oferta_validada_emitida_para_coletor"),
                )

                ofertas.append(oferta)

            except Exception:
                erros_transitorios += 1

                logger.exception(
                    "Falha ao processar mensagem " "do Social Scout: chat=%s message=%s.",
                    mensagem.chat_id,
                    mensagem.message_id,
                )

        if self.modo_sombra:
            logger.info(
                "SocialScoutScraper MODO SOMBRA | "
                "candidatas=%s | nicho=%s | "
                "fora_nicho=%s | ja_processadas=%s | "
                "erros_transitorios=%s | "
                "ofertas_emitidas=0.",
                candidatas_sombra,
                nicho_sombra,
                fora_nicho_sombra,
                ignoradas_processadas,
                erros_transitorios,
            )

        else:
            logger.info(
                "SocialScoutScraper converteu %s oferta(s) "
                "a partir de ate %s mensagem(ns) recente(s). "
                "Ja processadas=%s | erros transitorios=%s.",
                len(ofertas),
                len(mensagens_recentes),
                ignoradas_processadas,
                erros_transitorios,
            )

        return ofertas

    def _processar_sombra(
        self,
        *,
        mensagem: MensagemSocialScout,
        fingerprint: str,
        oferta: Oferta,
    ) -> str:
        classificador = self.classificador_sombra

        if classificador is None:
            classificador = ClassificadorProduto()

            self.classificador_sombra = classificador

        classificacao = classificador.aplicar_classificacao(oferta)

        if classificacao.eh_nicho:
            status = "sombra_nicho"

        else:
            status = "sombra_fora_nicho"

        motivo = (
            "modo_sombra|"
            f"categoria={classificacao.categoria or ''}|"
            f"relevancia={classificacao.relevancia:.2f}|"
            f"{classificacao.motivo}"
        )

        self._marcar_terminal(
            mensagem=mensagem,
            fingerprint=fingerprint,
            status=status,
            motivo=motivo,
        )

        logger.info(
            "Social Scout SOMBRA | "
            "status=%s | categoria=%s | "
            "relevancia=%.2f | preco=%.2f | "
            "produto=%s | nome=%s",
            status,
            classificacao.categoria,
            classificacao.relevancia,
            oferta.preco,
            (oferta.id_anuncio or oferta.id_produto or "sem_id"),
            oferta.nome,
        )

        return status

    def _marcar_terminal(
        self,
        *,
        mensagem: MensagemSocialScout,
        fingerprint: str,
        status: str,
        motivo: str,
    ) -> None:
        self.processamentos_repository.salvar(
            mensagem=mensagem,
            versao_processador=(self.VERSAO_PROCESSADOR),
            fingerprint=fingerprint,
            status=status,
            motivo=motivo,
        )

    @staticmethod
    def _fingerprint_mensagem(
        mensagem: MensagemSocialScout,
    ) -> str:
        dados = asdict(mensagem)

        dados["links"] = list(mensagem.links)

        payload = json.dumps(
            dados,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode("utf-8")

        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _chave_oferta(
        oferta: Oferta,
    ) -> str:
        for identificador in (
            oferta.id_anuncio,
            oferta.id_produto,
        ):
            texto = str(identificador or "").strip()

            if texto:
                return "id:" + texto.upper().replace(
                    "-",
                    "",
                ).replace(
                    "_",
                    "",
                )

        return "url:" + str(oferta.link or "").strip().casefold()
