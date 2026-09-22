from __future__ import annotations

import hmac
import ipaddress
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
)
from services.api_aplicacao.controlador import ControladorApiAplicacao
from services.api_aplicacao.user_facing_abuse_controls import (
    DecisaoAbuseControl,
    UserFacingAbuseControls,
)
from services.api_aplicacao.user_facing_auth import UserFacingAuthController
from services.api_aplicacao.user_facing_community_discovery import (
    UserFacingCommunityDiscoveryController,
)
from services.api_aplicacao.user_facing_devices import UserFacingDevicesController
from services.api_aplicacao.user_facing_feed import UserFacingFeedController
from services.api_aplicacao.user_facing_gamification import UserFacingGamificationController
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
    UserFacingHttpFoundation,
)
from services.api_aplicacao.user_facing_missions import UserFacingMissionsController
from services.api_aplicacao.user_facing_preferences import (
    UserFacingPreferencesController,
)
from services.api_aplicacao.user_facing_reporting import (
    UserFacingCommunityReportingController,
)
from services.api_aplicacao.user_facing_watchlist import (
    UserFacingWatchlistController,
)
from services.community_discovery_service import CommunityDiscoveryService
from services.gamification_read_service import GamificationReadService
from services.mission_read_service import MissionReadService

if TYPE_CHECKING:
    from models.user_identity import ContaUsuario
    from services.personalized_feed_service import PersonalizedFeedService
    from services.user_identity_service import UserIdentityService
    from services.user_personalization_service import (
        UserPersonalizationService,
    )


class ServidorApiAplicacao:
    def __init__(
        self,
        controlador: ControladorApiAplicacao,
        *,
        host: str | None = None,
        porta: int | None = None,
        token: str | None = None,
        user_identity_service: UserIdentityService | None = None,
        user_personalization_service: UserPersonalizationService | None = None,
        personalized_feed_service: PersonalizedFeedService | None = None,
        gamification_read_service: GamificationReadService | None = None,
        community_discovery_service: CommunityDiscoveryService | None = None,
        user_facing_abuse_controls: UserFacingAbuseControls | None = None,
        mission_read_service: MissionReadService | None = None,
        community_moderation_repository: CommunityModerationRepository | None = None,
    ) -> None:
        load_dotenv()

        host_ambiente = os.getenv("API_APLICACAO_HOST", "").strip()
        porta_ambiente = os.getenv("API_APLICACAO_PORTA", "").strip()
        token_ambiente = os.getenv("API_APLICACAO_TOKEN", "").strip()

        self.controlador = controlador
        self.host = host.strip() if host is not None else host_ambiente or "127.0.0.1"
        self.porta = self._resolver_porta(
            porta=porta,
            porta_ambiente=porta_ambiente,
        )
        self.token = token.strip() if token is not None else token_ambiente
        self.user_facing_http = UserFacingHttpFoundation(
            user_identity_service=user_identity_service,
        )
        self.user_facing_auth = UserFacingAuthController(
            user_identity_service,
        )
        self.user_facing_devices = UserFacingDevicesController(
            user_identity_service,
        )
        self.user_facing_preferences = UserFacingPreferencesController(
            user_personalization_service,
        )
        self.user_facing_watchlist = UserFacingWatchlistController(
            user_personalization_service,
        )
        self.user_facing_feed = UserFacingFeedController(
            personalized_feed_service,
        )
        self.user_facing_gamification = UserFacingGamificationController(
            gamification_read_service,
        )
        self.user_facing_missions = UserFacingMissionsController(mission_read_service)
        self.user_facing_reporting = UserFacingCommunityReportingController(
            community_moderation_repository,
        )

        if community_discovery_service is None and user_identity_service is not None:
            identity_repository = getattr(
                user_identity_service,
                "repository",
                None,
            )
            identity_database = getattr(
                identity_repository,
                "caminho_banco",
                None,
            )
            if identity_database is not None:
                community_discovery_service = CommunityDiscoveryService(
                    CommunityDiscoveryRepository(identity_database)
                )

        self.user_facing_community_discovery = UserFacingCommunityDiscoveryController(
            community_discovery_service,
        )
        self.user_facing_abuse_controls = (
            user_facing_abuse_controls
            if user_facing_abuse_controls is not None
            else UserFacingAbuseControls.from_env()
        )

        if not self._host_loopback(self.host) and not self.token:
            raise ValueError("API_APLICACAO_TOKEN e obrigatorio para bind " "fora de loopback.")

        self._servidor: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @staticmethod
    def _resolver_porta(
        *,
        porta: int | None,
        porta_ambiente: str,
    ) -> int:
        if porta is not None:
            valor = int(porta)
        elif porta_ambiente:
            try:
                valor = int(porta_ambiente)
            except ValueError as erro:
                raise ValueError("API_APLICACAO_PORTA precisa ser um inteiro.") from erro
        else:
            valor = 8766

        if valor < 0 or valor > 65535:
            raise ValueError("API_APLICACAO_PORTA precisa estar entre 0 e 65535.")

        return valor

    @staticmethod
    def _host_loopback(host: str) -> bool:
        normalizado = host.strip().lower()
        if normalizado == "localhost":
            return True

        try:
            return ipaddress.ip_address(normalizado).is_loopback
        except ValueError:
            return False

    @property
    def endereco(self) -> tuple[str, int] | None:
        servidor = self._servidor
        if servidor is None:
            return None

        host, porta = servidor.server_address[:2]
        return str(host), int(porta)

    def iniciar(self) -> None:
        if self._servidor is not None:
            return

        controlador = self.controlador
        token_api = self.token
        user_facing_http = self.user_facing_http
        user_facing_auth = self.user_facing_auth
        user_facing_devices = self.user_facing_devices
        user_facing_preferences = self.user_facing_preferences
        user_facing_watchlist = self.user_facing_watchlist
        user_facing_feed = self.user_facing_feed
        user_facing_gamification = self.user_facing_gamification
        user_facing_missions = self.user_facing_missions
        user_facing_reporting = self.user_facing_reporting
        user_facing_community_discovery = self.user_facing_community_discovery
        abuse_controls = self.user_facing_abuse_controls

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                url = urlparse(self.path)
                rota = url.path.rstrip("/") or "/"
                query = parse_qs(url.query)

                if rota == "/api/v1/health":
                    self._responder_json(
                        200,
                        controlador.health(),
                    )
                    return

                if token_api and not self._autorizado(token_api):
                    if rota.startswith("/api/v1/me/reports/") or rota in {
                        "/api/v1/me",
                        "/api/v1/me/preferences",
                        "/api/v1/me/watchlist",
                        "/api/v1/me/devices",
                        "/api/v1/me/feed",
                        "/api/v1/me/gamification",
                        "/api/v1/me/missions",
                        "/api/v1/me/discoveries",
                        "/api/v1/me/reports",
                    }:
                        self._responder_erro_user_facing(
                            ErroHttpUserFacing(
                                401,
                                "infraestrutura_nao_autorizada",
                                "Nao autorizado.",
                            )
                        )
                    else:
                        self._responder_json(
                            401,
                            {"erro": "Nao autorizado."},
                        )
                    return

                if rota == "/api/v1/me/reports":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_reporting.listar_status(
                            conta,
                            limite=query.get(
                                "limite",
                                ["20"],
                            )[0],
                            offset=query.get(
                                "offset",
                                ["0"],
                            )[0],
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                partes_reports = [unquote(parte) for parte in rota.split("/") if parte]

                if len(partes_reports) == 5 and partes_reports[:4] == [
                    "api",
                    "v1",
                    "me",
                    "reports",
                ]:
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_reporting.obter_status(
                            conta,
                            partes_reports[4],
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/discoveries":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_community_discovery.listar(
                            conta,
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/gamification":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_gamification.obter(
                            conta,
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/missions":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_missions.obter(
                            conta,
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/feed":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_feed.listar(
                            conta,
                            limite=query.get("limite", ["20"])[0],
                            offset=query.get("offset", ["0"])[0],
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/devices":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_devices.listar(conta)
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/watchlist":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_watchlist.listar(conta)
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/preferences":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    try:
                        status, dados = user_facing_preferences.obter(conta)
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    status, dados = user_facing_auth.me(conta)
                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/produtos":
                    dados = controlador.listar_produtos(
                        limite=query.get("limite", ["50"])[0],
                        offset=query.get("offset", ["0"])[0],
                    )
                    self._responder_json(200, dados)
                    return

                if rota == "/api/v1/alertas":
                    dados = controlador.listar_alertas(
                        limite=query.get("limite", ["50"])[0],
                        offset=query.get("offset", ["0"])[0],
                    )
                    self._responder_json(200, dados)
                    return

                partes = [unquote(parte) for parte in rota.split("/") if parte]

                if len(partes) == 4 and partes[:3] == ["api", "v1", "produtos"]:
                    dados = controlador.obter_produto(partes[3])
                    if dados is None:
                        self._responder_json(
                            404,
                            {"erro": "Produto nao encontrado."},
                        )
                        return

                    self._responder_json(200, dados)
                    return

                if (
                    len(partes) == 5
                    and partes[:3] == ["api", "v1", "produtos"]
                    and partes[4] == "historico"
                ):
                    dados = controlador.listar_historico_produto(
                        partes[3],
                        limite=query.get("limite", ["50"])[0],
                        offset=query.get("offset", ["0"])[0],
                    )
                    if dados is None:
                        self._responder_json(
                            404,
                            {"erro": "Produto nao encontrado."},
                        )
                        return

                    self._responder_json(200, dados)
                    return

                self._responder_json(
                    404,
                    {"erro": "Rota nao encontrada."},
                )

            def do_POST(self) -> None:
                url = urlparse(self.path)
                rota = url.path.rstrip("/") or "/"

                if rota not in {
                    "/api/v1/auth/register",
                    "/api/v1/auth/login",
                    "/api/v1/auth/logout",
                    "/api/v1/me/discoveries",
                    "/api/v1/me/reports",
                }:
                    self._metodo_nao_permitido()
                    return

                if token_api and not self._autorizado(token_api):
                    self._responder_erro_user_facing(
                        ErroHttpUserFacing(
                            401,
                            "infraestrutura_nao_autorizada",
                            "Nao autorizado.",
                        )
                    )
                    return

                if rota == "/api/v1/me/reports":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    payload = self._ler_json_user_facing()
                    if payload is None:
                        return

                    try:
                        status, dados = user_facing_reporting.criar_idempotente(
                            conta,
                            payload,
                            idempotency_key=self.headers.get("Idempotency-Key"),
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/me/discoveries":
                    conta = self._resolver_usuario_user_facing()
                    if conta is None:
                        return

                    payload = self._ler_json_user_facing()
                    if payload is None:
                        return

                    try:
                        status, dados = user_facing_community_discovery.criar(
                            conta,
                            payload,
                        )
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                if rota == "/api/v1/auth/logout":
                    try:
                        token_usuario = user_facing_http.extrair_token_sessao(
                            self.headers,
                            obrigatorio=True,
                        )
                        assert token_usuario is not None

                        user_facing_http.resolver_usuario(
                            self.headers,
                        )
                        status, dados = user_facing_auth.logout(token_usuario)
                    except ErroHttpUserFacing as erro:
                        self._responder_erro_user_facing(erro)
                        return

                    self._responder_json(
                        status,
                        user_facing_http.sucesso(dados),
                    )
                    return

                payload = self._ler_json_user_facing()
                if payload is None:
                    return

                decisao_abuse = self._avaliar_abuse_user_facing(
                    rota,
                    payload,
                )
                if not decisao_abuse.permitido:
                    self._responder_abuse_limit(decisao_abuse)
                    return

                try:
                    if rota == "/api/v1/auth/register":
                        status, dados = user_facing_auth.registrar(payload)
                    else:
                        status, dados = user_facing_auth.login(payload)
                except ErroHttpUserFacing as erro:
                    self._responder_erro_user_facing(erro)
                    return

                self._responder_json(
                    status,
                    user_facing_http.sucesso(dados),
                )

            def do_PUT(self) -> None:
                url = urlparse(self.path)
                rota = url.path.rstrip("/") or "/"
                partes = [unquote(parte) for parte in rota.split("/") if parte]

                if not (
                    len(partes) == 5
                    and partes[:3] == ["api", "v1", "me"]
                    and partes[3] in {"watchlist", "devices"}
                ):
                    self._metodo_nao_permitido()
                    return

                if token_api and not self._autorizado(token_api):
                    self._responder_erro_user_facing(
                        ErroHttpUserFacing(
                            401,
                            "infraestrutura_nao_autorizada",
                            "Nao autorizado.",
                        )
                    )
                    return

                conta = self._resolver_usuario_user_facing()
                if conta is None:
                    return

                payload = self._ler_json_user_facing()
                if payload is None:
                    return

                try:
                    if partes[3] == "watchlist":
                        status, dados = user_facing_watchlist.salvar(
                            conta,
                            partes[4],
                            payload,
                        )
                    else:
                        status, dados = user_facing_devices.salvar(
                            conta,
                            partes[4],
                            payload,
                        )
                except ErroHttpUserFacing as erro:
                    self._responder_erro_user_facing(erro)
                    return

                self._responder_json(
                    status,
                    user_facing_http.sucesso(dados),
                )

            def do_PATCH(self) -> None:
                url = urlparse(self.path)
                rota = url.path.rstrip("/") or "/"

                if rota != "/api/v1/me/preferences":
                    self._metodo_nao_permitido()
                    return

                if token_api and not self._autorizado(token_api):
                    self._responder_erro_user_facing(
                        ErroHttpUserFacing(
                            401,
                            "infraestrutura_nao_autorizada",
                            "Nao autorizado.",
                        )
                    )
                    return

                conta = self._resolver_usuario_user_facing()
                if conta is None:
                    return

                payload = self._ler_json_user_facing()
                if payload is None:
                    return

                try:
                    status, dados = user_facing_preferences.atualizar(
                        conta,
                        payload,
                    )
                except ErroHttpUserFacing as erro:
                    self._responder_erro_user_facing(erro)
                    return

                self._responder_json(
                    status,
                    user_facing_http.sucesso(dados),
                )

            def do_DELETE(self) -> None:
                url = urlparse(self.path)
                rota = url.path.rstrip("/") or "/"
                partes = [unquote(parte) for parte in rota.split("/") if parte]

                if not (
                    len(partes) == 5
                    and partes[:3] == ["api", "v1", "me"]
                    and partes[3] in {"watchlist", "devices"}
                ):
                    self._metodo_nao_permitido()
                    return

                if token_api and not self._autorizado(token_api):
                    self._responder_erro_user_facing(
                        ErroHttpUserFacing(
                            401,
                            "infraestrutura_nao_autorizada",
                            "Nao autorizado.",
                        )
                    )
                    return

                conta = self._resolver_usuario_user_facing()
                if conta is None:
                    return

                try:
                    if partes[3] == "watchlist":
                        status, dados = user_facing_watchlist.remover(
                            conta,
                            partes[4],
                        )
                    else:
                        status, dados = user_facing_devices.remover(
                            conta,
                            partes[4],
                        )
                except ErroHttpUserFacing as erro:
                    self._responder_erro_user_facing(erro)
                    return

                self._responder_json(
                    status,
                    user_facing_http.sucesso(dados),
                )

            def _client_key_user_facing(self) -> str:
                return str(self.client_address[0])

            def _avaliar_abuse_user_facing(
                self,
                rota: str,
                payload: dict[str, object],
            ) -> DecisaoAbuseControl:
                client_key = self._client_key_user_facing()

                if rota == "/api/v1/auth/register":
                    return abuse_controls.avaliar_register(client_key)

                if rota == "/api/v1/auth/login":
                    email = payload.get("email")
                    subject = email if isinstance(email, str) else None
                    return abuse_controls.avaliar_login(
                        client_key,
                        subject=subject,
                    )

                return DecisaoAbuseControl(permitido=True)

            def _responder_abuse_limit(
                self,
                decisao: DecisaoAbuseControl,
            ) -> None:
                erro = ErroHttpUserFacing(
                    429,
                    "limite_requisicoes_excedido",
                    "Muitas tentativas. Tente novamente mais tarde.",
                )
                self._responder_json(
                    429,
                    erro.payload(),
                    headers_adicionais={"Retry-After": str(decisao.retry_after_seconds)},
                )

            def _metodo_nao_permitido(self) -> None:
                self._responder_json(
                    405,
                    {"erro": "Metodo nao permitido."},
                )

            def _autorizado(self, esperado: str) -> bool:
                autorizacao = self.headers.get(
                    "Authorization",
                    "",
                )
                prefixo = "Bearer "
                recebido = (
                    autorizacao[len(prefixo) :].strip() if autorizacao.startswith(prefixo) else ""
                )
                return hmac.compare_digest(
                    recebido,
                    esperado,
                )

            def _ler_json_user_facing(
                self,
            ) -> dict[str, object] | None:
                try:
                    return user_facing_http.ler_json_objeto(
                        headers=self.headers,
                        stream=self.rfile,
                    )
                except ErroHttpUserFacing as erro:
                    self._responder_erro_user_facing(erro)
                    return None

            def _resolver_usuario_user_facing(
                self,
            ) -> ContaUsuario | None:
                try:
                    return user_facing_http.resolver_usuario(
                        self.headers,
                    )
                except ErroHttpUserFacing as erro:
                    self._responder_erro_user_facing(erro)
                    return None

            def _responder_erro_user_facing(
                self,
                erro: ErroHttpUserFacing,
            ) -> None:
                self._responder_json(
                    erro.status,
                    erro.payload(),
                )

            def _responder_json(
                self,
                status: int,
                payload: object,
                *,
                headers_adicionais: dict[str, str] | None = None,
            ) -> None:
                corpo = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")

                self.send_response(status)
                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
                self.send_header(
                    "Content-Length",
                    str(len(corpo)),
                )
                self.send_header(
                    "Cache-Control",
                    "no-store",
                )
                if headers_adicionais:
                    for nome, valor in headers_adicionais.items():
                        self.send_header(nome, valor)
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(
                self,
                format: str,
                *args: object,
            ) -> None:
                return

        self._servidor = ThreadingHTTPServer(
            (self.host, self.porta),
            Handler,
        )
        self._thread = threading.Thread(
            target=self._servidor.serve_forever,
            name="servidor-api-aplicacao",
            daemon=True,
        )
        self._thread.start()

    def encerrar(self) -> None:
        servidor = self._servidor
        if servidor is None:
            return

        servidor.shutdown()
        servidor.server_close()
        self._servidor = None

        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)

        self._thread = None
