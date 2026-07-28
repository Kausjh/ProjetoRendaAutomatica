from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ConfiguracaoNavegador:
    """Configurações centrais do navegador dedicado ao projeto."""

    pasta_perfil: Path
    headless: bool = False
    largura_viewport: int | None = None
    altura_viewport: int | None = None
    timeout_padrao_ms: int = 30_000
    timeout_navegacao_ms: int = 60_000

    @classmethod
    def padrao(cls) -> "ConfiguracaoNavegador":
        raiz_projeto = Path(__file__).resolve().parent.parent

        return cls(
            pasta_perfil=raiz_projeto / "browser_profile",
        )

    def preparar_diretorios(self) -> None:
        self.pasta_perfil.mkdir(
            parents=True,
            exist_ok=True,
        )
