# 63.8738, -149.7525

from __future__ import annotations

import hashlib
import ipaddress
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import SplitResult, urlsplit, urlunsplit

from models.community_discovery import DescobertaComunitaria
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)


class LimiteDescobertasComunitariasExcedido(ValueError):
    pass


class CommunityDiscoveryService:
    def __init__(
        self,
        repository: CommunityDiscoveryRepository,
        *,
        limite_por_hora: int = 30,
    ) -> None:
        if limite_por_hora < 1:
            raise ValueError("limite_por_hora precisa ser positivo.")

        self.repository = repository
        self.limite_por_hora = int(limite_por_hora)

    @staticmethod
    def _agora() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _host_corresponde(host: str, dominio: str) -> bool:
        return host == dominio or host.endswith("." + dominio)

    @classmethod
    def _marketplace(cls, host: str) -> str | None:
        dominios = (
            ("mercado_livre", ("mercadolivre.com.br", "mercadolivre.com", "meli.la")),
            ("kabum", ("kabum.com.br",)),
            ("shopee", ("shopee.com.br", "shope.ee")),
            ("aliexpress", ("aliexpress.com",)),
            ("amazon", ("amazon.com.br", "amzn.to", "link.amazon")),
        )

        for marketplace, candidatos in dominios:
            if any(cls._host_corresponde(host, dominio) for dominio in candidatos):
                return marketplace

        return None

    @staticmethod
    def _normalizar_netloc(parsed: SplitResult, host: str) -> str:
        try:
            porta = parsed.port
        except ValueError as erro:
            raise ValueError("Porta invalida no link enviado.") from erro

        host_formatado = f"[{host}]" if ":" in host else host
        if porta is None:
            return host_formatado

        if (parsed.scheme == "http" and porta == 80) or (parsed.scheme == "https" and porta == 443):
            return host_formatado

        return f"{host_formatado}:{porta}"

    @classmethod
    def normalizar_url(cls, url: str) -> tuple[str, str, str | None]:
        original = str(url or "").strip()

        if not original:
            raise ValueError("Informe o link da oferta.")
        if len(original) > 2048:
            raise ValueError("O link excede o limite permitido.")

        parsed = urlsplit(original)
        esquema = parsed.scheme.lower()

        if esquema not in {"http", "https"}:
            raise ValueError("O link precisa usar http ou https.")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Links com credenciais embutidas nao sao aceitos.")

        host = str(parsed.hostname or "").strip().rstrip(".").lower()
        if not host:
            raise ValueError("O link precisa informar um dominio valido.")

        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            raise ValueError("Enderecos locais nao sao aceitos.")

        try:
            endereco_ip = ipaddress.ip_address(host)
        except ValueError:
            endereco_ip = None

        if endereco_ip is not None and not endereco_ip.is_global:
            raise ValueError("Enderecos de rede privada ou local nao sao aceitos.")

        netloc = cls._normalizar_netloc(parsed, host)
        caminho = parsed.path or "/"
        normalizada = urlunsplit(
            (
                esquema,
                netloc,
                caminho,
                parsed.query,
                "",
            )
        )

        return original, normalizada, cls._marketplace(host)

    def registrar(
        self,
        *,
        conta_id: str,
        url: str,
    ) -> tuple[DescobertaComunitaria, bool]:
        conta = str(conta_id or "").strip()
        if not conta:
            raise ValueError("Conta de origem invalida.")

        original, normalizada, marketplace = self.normalizar_url(url)
        url_hash = hashlib.sha256(normalizada.encode("utf-8")).hexdigest()

        existente = self.repository.obter_por_conta_hash(
            conta_id=conta,
            url_hash=url_hash,
        )
        if existente is not None:
            return existente, False

        agora = self._agora()
        janela = (agora - timedelta(hours=1)).isoformat()

        if (
            self.repository.contar_recentes(
                conta_id=conta,
                criado_desde=janela,
            )
            >= self.limite_por_hora
        ):
            raise LimiteDescobertasComunitariasExcedido(
                "Limite de contribuicoes por hora atingido."
            )

        return self.repository.registrar(
            descoberta_id=f"dsc_{uuid.uuid4().hex}",
            conta_id=conta,
            url=original,
            url_normalizada=normalizada,
            url_hash=url_hash,
            marketplace=marketplace,
            agora=agora.isoformat(),
        )

    def listar(
        self,
        *,
        conta_id: str,
        limite: int = 50,
    ) -> list[DescobertaComunitaria]:
        return self.repository.listar_por_conta(
            str(conta_id or "").strip(),
            limite=limite,
        )
