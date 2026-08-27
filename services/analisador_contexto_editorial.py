# 63.8738, -149.7525

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True, slots=True)
class SinalContextoEditorial:
    tipo: str
    severidade: int
    referencia: str
    detalhe: str
    valor: float | None = None


@dataclass(frozen=True, slots=True)
class ResultadoContextoEditorial:
    sinais: tuple[SinalContextoEditorial, ...]

    @property
    def principal(self) -> SinalContextoEditorial | None:
        if not self.sinais:
            return None
        return max(self.sinais, key=lambda sinal: sinal.severidade)

    @property
    def tem_contexto(self) -> bool:
        return bool(self.sinais)


class AnalisadorContextoEditorial:
    """Detecta sinais técnicos objetivos que merecem comentário editorial."""

    GPUS_ENTRADA_OU_ANTIGAS = (
        "gt 710",
        "gt 730",
        "gt 740",
        "gt 1030",
        "gtx 750",
        "gtx 750 ti",
        "gtx 950",
        "gtx 960",
        "gtx 1050",
        "gtx 1050 ti",
        "rx 550",
        "rx 560",
        "r7 240",
        "r7 250",
        "r7 260",
    )

    TERMOS_MARKETING_FORTE = (
        "4k",
        "ultra",
        "high end",
        "top gamer",
        "gamer 4k",
    )

    def analisar(self, oferta: Oferta) -> ResultadoContextoEditorial:
        titulo = self._normalizar(oferta.nome)
        categoria = self._normalizar(str(getattr(oferta, "categoria", "") or ""))

        sinais: list[SinalContextoEditorial] = []

        for detector in (
            self._detectar_intel_core_antigo,
            self._detectar_ryzen_antigo,
            self._detectar_xeon_antigo,
            self._detectar_gpu_antiga_ou_entrada,
            self._detectar_ram_baixa,
            self._detectar_ddr3,
        ):
            sinal = detector(titulo)
            if sinal is not None:
                sinais.append(sinal)

        armazenamento = self._detectar_armazenamento_apertado(titulo, categoria)
        if armazenamento is not None:
            sinais.append(armazenamento)

        monitor = self._detectar_monitor_gamer_basico(titulo, categoria)
        if monitor is not None:
            sinais.append(monitor)

        marketing = self._detectar_marketing_desproporcional(
            titulo=titulo,
            sinais=sinais,
        )
        if marketing is not None:
            sinais.append(marketing)

        upgrade = self._detectar_upgrade_antigo(
            titulo=titulo,
            sinais=sinais,
        )
        if upgrade is not None:
            sinais.append(upgrade)

        return ResultadoContextoEditorial(
            sinais=tuple(
                sorted(
                    sinais,
                    key=lambda sinal: sinal.severidade,
                    reverse=True,
                )
            )
        )

    @staticmethod
    def _normalizar(texto: str) -> str:
        decomposed = unicodedata.normalize("NFKD", texto)
        sem_acentos = "".join(
            caractere for caractere in decomposed if not unicodedata.combining(caractere)
        )
        texto_limpo = re.sub(
            r"[^a-z0-9+./ -]+",
            " ",
            sem_acentos.casefold(),
        )
        return re.sub(r"\s+", " ", texto_limpo).strip()

    @staticmethod
    def _geracao_intel(modelo: str) -> int | None:
        digitos = re.sub(r"\D", "", modelo)
        if len(digitos) == 4:
            return int(digitos[0])
        if len(digitos) == 5:
            return int(digitos[:2])
        return None

    def _detectar_intel_core_antigo(
        self,
        titulo: str,
    ) -> SinalContextoEditorial | None:
        match = re.search(r"\bi([3579])[- ]?(\d{4,5})([a-z]{0,2})\b", titulo)
        if match is None:
            return None

        familia = match.group(1)
        modelo = match.group(2)
        sufixo = match.group(3).upper()
        geracao = self._geracao_intel(modelo)

        if geracao is None or geracao >= 8:
            return None

        return SinalContextoEditorial(
            tipo="cpu_antiga",
            severidade=3 if geracao <= 4 else 2,
            referencia=f"Intel Core i{familia}-{modelo}{sufixo}",
            detalhe=f"Intel Core de {geracao}ª geração",
            valor=float(geracao),
        )

    @staticmethod
    def _detectar_ryzen_antigo(
        titulo: str,
    ) -> SinalContextoEditorial | None:
        match = re.search(r"\bryzen\s+([3579])\s+([12]\d{3})([a-z]{0,2})\b", titulo)
        if match is None:
            return None

        serie = int(match.group(2)[0]) * 1000
        return SinalContextoEditorial(
            tipo="cpu_antiga",
            severidade=2,
            referencia=f"Ryzen {match.group(1)} {match.group(2)}{match.group(3).upper()}",
            detalhe=f"Ryzen série {serie}",
            valor=float(serie),
        )

    @staticmethod
    def _detectar_xeon_antigo(
        titulo: str,
    ) -> SinalContextoEditorial | None:
        match = re.search(r"\bxeon\s+e5[- ]?(\d{4})(?:\s*v([1-4]))?\b", titulo)
        if match is None:
            return None

        referencia = f"Xeon E5-{match.group(1)}"
        if match.group(2):
            referencia += f" v{match.group(2)}"

        return SinalContextoEditorial(
            tipo="xeon_antigo",
            severidade=3,
            referencia=referencia,
            detalhe="plataforma Xeon E5 antiga",
        )

    def _detectar_gpu_antiga_ou_entrada(
        self,
        titulo: str,
    ) -> SinalContextoEditorial | None:
        for gpu in sorted(self.GPUS_ENTRADA_OU_ANTIGAS, key=len, reverse=True):
            if re.search(rf"(?<![a-z0-9]){re.escape(gpu)}(?![a-z0-9])", titulo):
                return SinalContextoEditorial(
                    tipo="gpu_antiga_entrada",
                    severidade=3,
                    referencia=gpu.upper(),
                    detalhe="GPU antiga ou de entrada",
                )
        return None

    @staticmethod
    def _detectar_ram_baixa(
        titulo: str,
    ) -> SinalContextoEditorial | None:
        padroes = (
            r"\b(\d{1,2})\s*gb\s+(?:de\s+)?(?:ram|memoria)\b",
            r"\b(?:ram|memoria)\s+(?:de\s+)?(\d{1,2})\s*gb\b",
        )
        for padrao in padroes:
            match = re.search(padrao, titulo)
            if match is None:
                continue

            quantidade = int(match.group(1))
            if quantidade > 4:
                return None

            return SinalContextoEditorial(
                tipo="ram_baixa",
                severidade=3,
                referencia=f"{quantidade} GB de RAM",
                detalhe="quantidade de memória muito apertada",
                valor=float(quantidade),
            )
        return None

    @staticmethod
    def _detectar_armazenamento_apertado(
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if "ssd" not in titulo and "nvme" not in titulo and "armazenamento" not in categoria:
            return None

        padroes = (
            r"\b(?:ssd|nvme)\D{0,24}(\d{2,4})\s*gb\b",
            r"\b(\d{2,4})\s*gb\D{0,24}(?:ssd|nvme)\b",
        )
        for padrao in padroes:
            match = re.search(padrao, titulo)
            if match is None:
                continue

            capacidade = int(match.group(1))
            if capacidade > 128:
                return None

            return SinalContextoEditorial(
                tipo="armazenamento_apertado",
                severidade=2,
                referencia=f"SSD de {capacidade} GB",
                detalhe="capacidade de armazenamento muito pequena",
                valor=float(capacidade),
            )
        return None

    @staticmethod
    def _detectar_ddr3(
        titulo: str,
    ) -> SinalContextoEditorial | None:
        if "ddr3" not in titulo:
            return None
        return SinalContextoEditorial(
            tipo="ddr3",
            severidade=2,
            referencia="DDR3",
            detalhe="plataforma de memória antiga",
        )

    @staticmethod
    def _detectar_monitor_gamer_basico(
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if "gamer" not in titulo:
            return None
        if "monitor" not in titulo and "monitor" not in categoria:
            return None

        match = re.search(r"\b(60|75)\s*hz\b", titulo)
        if match is None:
            return None

        hz = int(match.group(1))
        return SinalContextoEditorial(
            tipo="monitor_gamer_basico",
            severidade=2,
            referencia=f"{hz} Hz",
            detalhe="taxa de atualização básica para um anúncio gamer",
            valor=float(hz),
        )

    def _detectar_marketing_desproporcional(
        self,
        *,
        titulo: str,
        sinais: list[SinalContextoEditorial],
    ) -> SinalContextoEditorial | None:
        gpu_fraca = next(
            (sinal for sinal in sinais if sinal.tipo == "gpu_antiga_entrada"),
            None,
        )
        if gpu_fraca is None:
            return None
        if not any(termo in titulo for termo in self.TERMOS_MARKETING_FORTE):
            return None

        return SinalContextoEditorial(
            tipo="marketing_gpu_desproporcional",
            severidade=4,
            referencia=gpu_fraca.referencia,
            detalhe="marketing forte combinado com GPU antiga ou de entrada",
        )

    @staticmethod
    def _detectar_upgrade_antigo(
        *,
        titulo: str,
        sinais: list[SinalContextoEditorial],
    ) -> SinalContextoEditorial | None:
        if "upgrade" not in titulo:
            return None

        antigo = next(
            (sinal for sinal in sinais if sinal.tipo in {"cpu_antiga", "xeon_antigo", "ddr3"}),
            None,
        )
        if antigo is None:
            return None

        return SinalContextoEditorial(
            tipo="upgrade_antigo",
            severidade=4,
            referencia=antigo.referencia,
            detalhe="produto antigo vendido explicitamente como upgrade",
            valor=antigo.valor,
        )
