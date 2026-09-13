from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from models.user_identity import ContaUsuario, SessaoUsuarioEmitida
from repositories.user_identity_repository import UserIdentityRepository

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SALT_BYTES = 16
_MIN_PASSWORD_LENGTH = 12
_MAX_PASSWORD_LENGTH = 1024


class UserIdentityService:
    def __init__(
        self,
        repository: UserIdentityRepository,
        *,
        session_ttl: timedelta = timedelta(days=30),
    ) -> None:
        if session_ttl <= timedelta(0):
            raise ValueError("session_ttl precisa ser positivo.")

        self.repository = repository
        self.session_ttl = session_ttl

    @staticmethod
    def normalizar_email(email: str) -> str:
        normalizado = email.strip().lower()

        if len(normalizado) > 254 or not _EMAIL_RE.fullmatch(normalizado):
            raise ValueError("Email invalido.")

        return normalizado

    @staticmethod
    def _validar_senha(senha: str) -> None:
        if len(senha) < _MIN_PASSWORD_LENGTH:
            raise ValueError(f"A senha precisa ter pelo menos {_MIN_PASSWORD_LENGTH} caracteres.")

        if len(senha) > _MAX_PASSWORD_LENGTH:
            raise ValueError("Senha excede o limite permitido.")

    @staticmethod
    def _hash_senha(senha: str, salt: bytes) -> bytes:
        return hashlib.scrypt(
            senha.encode("utf-8"),
            salt=salt,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_SCRYPT_DKLEN,
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _agora() -> datetime:
        return datetime.now(UTC)

    def criar_conta(
        self,
        *,
        email: str,
        senha: str,
    ) -> ContaUsuario:
        email_normalizado = self.normalizar_email(email)
        self._validar_senha(senha)

        salt = secrets.token_bytes(_SALT_BYTES)
        senha_hash = self._hash_senha(senha, salt)
        agora = self._agora().isoformat()

        return self.repository.criar_conta(
            conta_id=f"usr_{uuid.uuid4().hex}",
            email_normalizado=email_normalizado,
            email_exibicao=email.strip(),
            senha_salt=salt,
            senha_hash=senha_hash,
            criado_em=agora,
        )

    def autenticar(
        self,
        *,
        email: str,
        senha: str,
    ) -> ContaUsuario | None:
        email_normalizado = self.normalizar_email(email)
        credencial = self.repository.obter_credencial_por_email(email_normalizado)

        if credencial is None or not credencial.conta.ativa:
            return None

        candidato = self._hash_senha(senha, credencial.senha_salt)

        if not hmac.compare_digest(candidato, credencial.senha_hash):
            return None

        return credencial.conta

    def emitir_sessao(
        self,
        conta: ContaUsuario,
    ) -> SessaoUsuarioEmitida:
        if not conta.ativa:
            raise ValueError("Conta inativa.")

        agora = self._agora()
        expira = agora + self.session_ttl
        token = f"pra_usr_v1_{secrets.token_urlsafe(32)}"

        sessao = self.repository.criar_sessao(
            sessao_id=f"ses_{uuid.uuid4().hex}",
            conta_id=conta.id,
            token_hash=self._hash_token(token),
            criado_em=agora.isoformat(),
            expira_em=expira.isoformat(),
        )

        return SessaoUsuarioEmitida(
            conta=conta,
            sessao=sessao,
            token=token,
        )

    def autenticar_e_emitir_sessao(
        self,
        *,
        email: str,
        senha: str,
    ) -> SessaoUsuarioEmitida | None:
        conta = self.autenticar(email=email, senha=senha)

        if conta is None:
            return None

        return self.emitir_sessao(conta)

    def resolver_sessao(
        self,
        token: str,
    ) -> ContaUsuario | None:
        if not token:
            return None

        sessao = self.repository.obter_sessao_por_token_hash(self._hash_token(token))

        if sessao is None or sessao.revogada_em is not None:
            return None

        agora = self._agora()
        expira_em = datetime.fromisoformat(sessao.expira_em)

        if expira_em <= agora:
            return None

        conta = self.repository.obter_conta(sessao.conta_id)

        if conta is None or not conta.ativa:
            return None

        return conta

    def revogar_sessao(self, token: str) -> bool:
        sessao = self.repository.obter_sessao_por_token_hash(self._hash_token(token))

        if sessao is None:
            return False

        return self.repository.revogar_sessao(
            sessao_id=sessao.id,
            revogada_em=self._agora().isoformat(),
        )
