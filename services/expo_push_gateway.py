from __future__ import annotations

import re
from collections.abc import Sequence

import httpx

from models.push_dispatcher import MensagemPushExpo, ReciboPushExpo, TicketPushExpo

EXPO_PUSH_SEND_URL = "https://exp.host/--/api/v2/push/send"
EXPO_PUSH_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"

_MAX_MENSAGENS = 100
_MAX_RECIBOS = 1000
_TOKEN_RE = re.compile(r"(?:Exponent|Expo)PushToken\[[^\]]+\]")


class ErroExpoPush(RuntimeError):
    def __init__(
        self,
        mensagem: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        retry_after_seconds: int | None = None,
        codigo: str | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.codigo = codigo


class ExpoPushGateway:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
        send_url: str = EXPO_PUSH_SEND_URL,
        receipts_url: str = EXPO_PUSH_RECEIPTS_URL,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds precisa ser positivo.")

        self.send_url = send_url
        self.receipts_url = receipts_url
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> ExpoPushGateway:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def enviar(self, mensagens: Sequence[MensagemPushExpo]) -> list[TicketPushExpo]:
        if not mensagens:
            return []
        if len(mensagens) > _MAX_MENSAGENS:
            raise ValueError("Expo aceita no maximo 100 mensagens por request.")

        response = self._post(
            self.send_url,
            json=[mensagem.como_payload() for mensagem in mensagens],
        )
        payload = self._json_objeto(response)

        erros_globais = payload.get("errors")
        data = payload.get("data")

        if erros_globais and not data:
            codigo, mensagem = self._primeiro_erro_global(erros_globais)
            raise ErroExpoPush(
                mensagem,
                status_code=response.status_code,
                retryable=False,
                codigo=codigo,
            )

        if isinstance(data, dict) and len(mensagens) == 1:
            itens = [data]
        elif isinstance(data, list):
            itens = data
        else:
            raise ErroExpoPush(
                "Resposta de tickets Expo em formato invalido.",
                status_code=response.status_code,
            )

        if len(itens) != len(mensagens):
            raise ErroExpoPush(
                "Quantidade de tickets Expo diverge das mensagens enviadas.",
                status_code=response.status_code,
            )

        tickets: list[TicketPushExpo] = []

        for item in itens:
            if not isinstance(item, dict):
                raise ErroExpoPush("Ticket Expo em formato invalido.")

            status = str(item.get("status") or "").strip().lower()

            if status == "ok":
                ticket_id = str(item.get("id") or "").strip()
                if not ticket_id:
                    raise ErroExpoPush("Ticket Expo aceito sem receipt id.")

                tickets.append(
                    TicketPushExpo(
                        status="ok",
                        ticket_id=ticket_id,
                        erro_codigo=None,
                        erro_mensagem=None,
                    )
                )
                continue

            if status == "error":
                details = item.get("details")
                codigo = None
                if isinstance(details, dict):
                    valor = details.get("error")
                    if valor is not None:
                        codigo = str(valor).strip() or None

                tickets.append(
                    TicketPushExpo(
                        status="error",
                        ticket_id=None,
                        erro_codigo=codigo,
                        erro_mensagem=self._sanitizar_erro(item.get("message")),
                    )
                )
                continue

            raise ErroExpoPush("Ticket Expo com status desconhecido.")

        return tickets

    def obter_recibos(self, ticket_ids: Sequence[str]) -> dict[str, ReciboPushExpo]:
        ids = [str(ticket_id).strip() for ticket_id in ticket_ids if str(ticket_id).strip()]

        if not ids:
            return {}
        if len(ids) > _MAX_RECIBOS:
            raise ValueError("Expo aceita no maximo 1000 receipt ids por request.")

        response = self._post(self.receipts_url, json={"ids": ids})
        payload = self._json_objeto(response)

        erros_globais = payload.get("errors")
        data = payload.get("data")

        if erros_globais and not data:
            codigo, mensagem = self._primeiro_erro_global(erros_globais)
            raise ErroExpoPush(
                mensagem,
                status_code=response.status_code,
                retryable=False,
                codigo=codigo,
            )

        if not isinstance(data, dict):
            raise ErroExpoPush(
                "Resposta de receipts Expo em formato invalido.",
                status_code=response.status_code,
            )

        recibos: dict[str, ReciboPushExpo] = {}

        for ticket_id, item in data.items():
            if not isinstance(item, dict):
                raise ErroExpoPush("Receipt Expo em formato invalido.")

            status = str(item.get("status") or "").strip().lower()
            ticket = str(ticket_id).strip()

            if not ticket:
                continue

            if status == "ok":
                recibos[ticket] = ReciboPushExpo(
                    ticket_id=ticket,
                    status="ok",
                    erro_codigo=None,
                    erro_mensagem=None,
                )
                continue

            if status == "error":
                details = item.get("details")
                codigo = None
                if isinstance(details, dict):
                    valor = details.get("error")
                    if valor is not None:
                        codigo = str(valor).strip() or None

                recibos[ticket] = ReciboPushExpo(
                    ticket_id=ticket,
                    status="error",
                    erro_codigo=codigo,
                    erro_mensagem=self._sanitizar_erro(item.get("message")),
                )
                continue

            raise ErroExpoPush("Receipt Expo com status desconhecido.")

        return recibos

    def _post(self, url: str, *, json: object) -> httpx.Response:
        try:
            response = self.client.post(
                url,
                json=json,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        except (httpx.TimeoutException, httpx.NetworkError) as erro:
            raise ErroExpoPush(
                "Falha temporaria de transporte com Expo Push Service.",
                retryable=True,
            ) from erro
        except httpx.HTTPError as erro:
            raise ErroExpoPush(
                "Falha HTTP ao acessar Expo Push Service.",
                retryable=True,
            ) from erro

        if response.status_code == 429 or response.status_code >= 500:
            raise ErroExpoPush(
                "Expo Push Service temporariamente indisponivel.",
                status_code=response.status_code,
                retryable=True,
                retry_after_seconds=self._retry_after(response),
            )

        if response.status_code >= 400:
            raise ErroExpoPush(
                "Expo Push Service rejeitou a requisicao.",
                status_code=response.status_code,
                retryable=False,
            )

        return response

    @staticmethod
    def _retry_after(response: httpx.Response) -> int | None:
        valor = response.headers.get("Retry-After")
        if valor is None:
            return None

        try:
            segundos = int(valor)
        except ValueError:
            return None

        return max(1, segundos)

    @staticmethod
    def _json_objeto(response: httpx.Response) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError as erro:
            raise ErroExpoPush(
                "Expo Push Service retornou JSON invalido.",
                status_code=response.status_code,
            ) from erro

        if not isinstance(payload, dict):
            raise ErroExpoPush(
                "Expo Push Service retornou payload invalido.",
                status_code=response.status_code,
            )

        return payload

    @staticmethod
    def _sanitizar_erro(valor: object) -> str | None:
        if valor is None:
            return None

        texto = str(valor).strip()
        if not texto:
            return None

        return _TOKEN_RE.sub("[push-token-redacted]", texto)[:500]

    @classmethod
    def _primeiro_erro_global(cls, erros: object) -> tuple[str | None, str]:
        if not isinstance(erros, list) or not erros:
            return None, "Expo Push Service retornou erro global."

        primeiro = erros[0]
        if not isinstance(primeiro, dict):
            return None, "Expo Push Service retornou erro global."

        codigo_raw = primeiro.get("code")
        codigo = str(codigo_raw).strip() if codigo_raw is not None else None
        mensagem = cls._sanitizar_erro(primeiro.get("message"))

        return codigo or None, mensagem or "Expo Push Service retornou erro global."
