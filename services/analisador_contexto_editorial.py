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
    """Detecta sinais técnicos objetivos sem penalizar peças antigas só por serem antigas."""

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

    CPUS_BASICAS = (
        "celeron",
        "pentium",
        "intel atom",
        "intel n95",
        "intel n97",
        "intel n100",
        "n5095",
        "n5105",
        "j4105",
        "j4125",
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
            self._detectar_incompatibilidade_socket,
            self._detectar_incompatibilidade_memoria,
            self._detectar_marketing_cpu_basica,
        ):
            sinal = detector(titulo, categoria)
            if sinal is not None:
                sinais.append(sinal)

        for detector in (
            self._detectar_intel_core_antigo,
            self._detectar_ryzen_antigo,
            self._detectar_xeon_antigo,
            self._detectar_gpu_antiga_ou_entrada,
            self._detectar_ram_baixa,
            self._detectar_ddr3,
        ):
            sinal = detector(titulo, categoria)
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

    @staticmethod
    def _eh_sistema_ou_kit(titulo: str, categoria: str) -> bool:
        termos_categoria = (
            "computador",
            "notebook",
            "desktop",
            "kit upgrade",
            "placa mae",
            "motherboard",
        )
        if any(termo in categoria for termo in termos_categoria):
            return True

        return bool(
            re.search(
                r"\b(?:pc gamer|pc completo|computador|desktop|notebook|kit upgrade|placa mae|motherboard)\b",
                titulo,
            )
        )

    @classmethod
    def _eh_cpu_avulsa(cls, titulo: str, categoria: str) -> bool:
        if cls._eh_sistema_ou_kit(titulo, categoria):
            return False
        return "processador" in categoria or titulo.startswith("processador ")

    @classmethod
    def _eh_gpu_avulsa(cls, titulo: str, categoria: str) -> bool:
        if cls._eh_sistema_ou_kit(titulo, categoria):
            return False
        return (
            "placa de video" in categoria
            or "gpu" in categoria
            or titulo.startswith("placa de video ")
        )

    @classmethod
    def _eh_memoria_avulsa(cls, titulo: str, categoria: str) -> bool:
        if cls._eh_sistema_ou_kit(titulo, categoria):
            return False
        return "memoria" in categoria or "ram" in categoria or titulo.startswith("memoria ")

    @classmethod
    def _eh_armazenamento_avulso(cls, titulo: str, categoria: str) -> bool:
        if cls._eh_sistema_ou_kit(titulo, categoria):
            return False
        return (
            "armazenamento" in categoria or titulo.startswith("ssd ") or titulo.startswith("nvme ")
        )

    @classmethod
    def _contexto_exige_plataforma(cls, titulo: str, categoria: str) -> bool:
        if cls._eh_sistema_ou_kit(titulo, categoria):
            return True
        return "processador" in categoria or "placa mae" in categoria or "motherboard" in categoria

    @classmethod
    def _detectar_incompatibilidade_socket(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if not cls._contexto_exige_plataforma(titulo, categoria):
            return None

        tem_ryzen = bool(re.search(r"\bryzen\b", titulo))
        tem_intel_core = bool(
            re.search(r"\b(?:intel\s+)?core\s+i[3579]\b|\bi[3579][- ]?\d{4,5}\b", titulo)
        )
        lga = re.search(r"\blga\s*[- ]?(\d{3,4})\b", titulo)
        am = re.search(r"\bam\s*[- ]?([45])\b", titulo)

        if tem_ryzen and lga is not None:
            return SinalContextoEditorial(
                tipo="incompatibilidade_socket",
                severidade=5,
                referencia=f"Ryzen + LGA {lga.group(1)}",
                detalhe="processador Ryzen combinado com socket Intel LGA no mesmo anúncio",
            )

        if tem_intel_core and am is not None:
            return SinalContextoEditorial(
                tipo="incompatibilidade_socket",
                severidade=5,
                referencia=f"Intel Core + AM{am.group(1)}",
                detalhe="processador Intel Core combinado com socket AMD no mesmo anúncio",
            )

        return None

    @classmethod
    def _detectar_incompatibilidade_memoria(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if not cls._contexto_exige_plataforma(titulo, categoria):
            return None

        if "ddr3" in titulo and re.search(r"\bryzen\b", titulo):
            return SinalContextoEditorial(
                tipo="incompatibilidade_memoria",
                severidade=5,
                referencia="Ryzen + DDR3",
                detalhe="Ryzen não usa DDR3; a combinação técnica do anúncio não fecha",
            )

        intel = re.search(r"\bi([3579])[- ]?(\d{4,5})([a-z]{0,2})\b", titulo)
        if intel is not None:
            geracao = cls._geracao_intel(intel.group(2))
            if geracao is not None and geracao >= 12 and "ddr3" in titulo:
                return SinalContextoEditorial(
                    tipo="incompatibilidade_memoria",
                    severidade=5,
                    referencia=f"Intel {geracao}ª geração + DDR3",
                    detalhe="Intel Core de 12ª geração ou mais recente não combina com DDR3",
                    valor=float(geracao),
                )
            if geracao is not None and geracao <= 7 and "ddr5" in titulo:
                return SinalContextoEditorial(
                    tipo="incompatibilidade_memoria",
                    severidade=5,
                    referencia=f"Intel {geracao}ª geração + DDR5",
                    detalhe="Intel Core antigo não combina com plataforma DDR5",
                    valor=float(geracao),
                )

        ryzen_antigo = re.search(r"\bryzen\s+[3579]\s+([1-5]\d{3})([a-z0-9]{0,4})\b", titulo)
        if ryzen_antigo is not None and "ddr5" in titulo:
            serie = int(ryzen_antigo.group(1)[0]) * 1000
            return SinalContextoEditorial(
                tipo="incompatibilidade_memoria",
                severidade=5,
                referencia=f"Ryzen série {serie} + DDR5",
                detalhe="Ryzen das séries 1000 a 5000 usa plataforma DDR4, não DDR5",
                valor=float(serie),
            )

        return None

    @classmethod
    def _detectar_marketing_cpu_basica(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if "gamer" not in titulo or not cls._eh_sistema_ou_kit(titulo, categoria):
            return None

        for cpu in cls.CPUS_BASICAS:
            if re.search(rf"(?<![a-z0-9]){re.escape(cpu)}(?![a-z0-9])", titulo):
                return SinalContextoEditorial(
                    tipo="marketing_cpu_basica",
                    severidade=4,
                    referencia=cpu.upper(),
                    detalhe="CPU muito básica combinada com marketing gamer",
                )

        return None

    def _detectar_intel_core_antigo(
        self,
        titulo: str,
        categoria: str,
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

        if self._eh_cpu_avulsa(titulo, categoria):
            severidade = 1
        else:
            severidade = 3 if geracao <= 4 else 2

        return SinalContextoEditorial(
            tipo="cpu_antiga",
            severidade=severidade,
            referencia=f"Intel Core i{familia}-{modelo}{sufixo}",
            detalhe=f"Intel Core de {geracao}ª geração",
            valor=float(geracao),
        )

    @classmethod
    def _detectar_ryzen_antigo(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        match = re.search(r"\bryzen\s+([3579])\s+([12]\d{3})([a-z]{0,2})\b", titulo)
        if match is None:
            return None

        serie = int(match.group(2)[0]) * 1000
        severidade = 1 if cls._eh_cpu_avulsa(titulo, categoria) else 2
        return SinalContextoEditorial(
            tipo="cpu_antiga",
            severidade=severidade,
            referencia=f"Ryzen {match.group(1)} {match.group(2)}{match.group(3).upper()}",
            detalhe=f"Ryzen série {serie}",
            valor=float(serie),
        )

    @classmethod
    def _detectar_xeon_antigo(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        match = re.search(r"\bxeon\s+e5[- ]?(\d{4})(?:\s*v([1-4]))?\b", titulo)
        if match is None:
            return None

        referencia = f"Xeon E5-{match.group(1)}"
        if match.group(2):
            referencia += f" v{match.group(2)}"

        severidade = 1 if cls._eh_cpu_avulsa(titulo, categoria) else 3
        return SinalContextoEditorial(
            tipo="xeon_antigo",
            severidade=severidade,
            referencia=referencia,
            detalhe="plataforma Xeon E5 antiga",
        )

    def _detectar_gpu_antiga_ou_entrada(
        self,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        for gpu in sorted(self.GPUS_ENTRADA_OU_ANTIGAS, key=len, reverse=True):
            if re.search(rf"(?<![a-z0-9]){re.escape(gpu)}(?![a-z0-9])", titulo):
                severidade = 1 if self._eh_gpu_avulsa(titulo, categoria) else 3
                return SinalContextoEditorial(
                    tipo="gpu_antiga_entrada",
                    severidade=severidade,
                    referencia=gpu.upper(),
                    detalhe="GPU antiga ou de entrada",
                )
        return None

    @classmethod
    def _detectar_ram_baixa(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if cls._eh_memoria_avulsa(titulo, categoria):
            return None

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
                detalhe="quantidade de memória muito apertada no produto completo",
                valor=float(quantidade),
            )
        return None

    @classmethod
    def _detectar_armazenamento_apertado(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if "ssd" not in titulo and "nvme" not in titulo and "armazenamento" not in categoria:
            return None

        if cls._eh_armazenamento_avulso(titulo, categoria):
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
                detalhe="capacidade de armazenamento muito pequena no produto completo",
                valor=float(capacidade),
            )
        return None

    @classmethod
    def _detectar_ddr3(
        cls,
        titulo: str,
        categoria: str,
    ) -> SinalContextoEditorial | None:
        if "ddr3" not in titulo or cls._eh_memoria_avulsa(titulo, categoria):
            return None
        return SinalContextoEditorial(
            tipo="ddr3",
            severidade=2,
            referencia="DDR3",
            detalhe="plataforma de memória antiga dentro de um sistema ou kit",
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
