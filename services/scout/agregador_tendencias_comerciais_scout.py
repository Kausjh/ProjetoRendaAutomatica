# 63.8738, -149.7525

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)
from models.tendencia_comercial_scout import (
    ObservacaoComercialScout,
    TendenciaComercialScout,
)


class AgregadorTendenciasComerciaisScout:
    """
    Detecta recorrencia comercial em multiplos sinais independentes.

    Regras centrais:
    - um unico sinal nunca vira tendencia;
    - repeticoes do mesmo sinal nao aumentam artificialmente a recorrencia;
    - somente observacoes dentro da janela sao consideradas;
    - a direcao compara a metade recente da janela com a metade anterior;
    - advertiser/parceiro nao e tratado como seller;
    - nenhum preco e criado ou alterado.
    """

    DIMENSAO_MARKETPLACE = "marketplace"
    DIMENSAO_PARCEIRO = "parceiro"
    DIMENSAO_TERMO = "termo_discovery"
    DIMENSAO_CUPOM = "cupom"

    DIRECAO_ALTA = "alta"
    DIRECAO_ESTAVEL = "estavel"
    DIRECAO_QUEDA = "queda"

    MINIMO_COBERTURA_TEMPORAL_HORAS = 1.0
    MAXIMA_CONCENTRACAO_MESMO_MINUTO = 0.80

    def agregar(
        self,
        observacoes: list[ObservacaoComercialScout],
        *,
        agora: datetime | None = None,
        janela_horas: int = 72,
        minimo_sinais: int = 2,
    ) -> list[TendenciaComercialScout]:
        janela_horas = int(janela_horas)

        minimo_sinais = int(minimo_sinais)

        if janela_horas <= 0:
            raise ValueError("janela_horas deve ser maior que zero.")

        if minimo_sinais < 2:
            raise ValueError("minimo_sinais deve ser pelo menos 2.")

        if agora is None:
            agora = datetime.now(UTC)

        agora = self._normalizar_data(
            agora,
            campo="agora",
        )

        inicio_janela = agora - timedelta(hours=janela_horas)

        meio_janela = inicio_janela + (agora - inicio_janela) / 2

        registros_por_sinal: dict[
            tuple[
                str,
                str,
                str,
                str,
            ],
            tuple[
                datetime,
                str,
            ],
        ] = {}

        for observacao in observacoes:

            instante = self._normalizar_data(
                observacao.observado_em,
                campo="observado_em",
            )

            if instante < inicio_janela:
                continue

            if instante > agora:
                continue

            perfil = observacao.perfil

            identidade_sinal = (
                self._normalizar_chave(perfil.fonte),
                str(perfil.id_externo or "").strip(),
            )

            for (
                dimensao,
                chave,
                rotulo,
            ) in self._extrair_dimensoes(perfil):

                identidade = (
                    dimensao,
                    chave,
                    identidade_sinal[0],
                    identidade_sinal[1],
                )

                existente = registros_por_sinal.get(identidade)

                if existente is None or instante < existente[0]:
                    registros_por_sinal[identidade] = (
                        instante,
                        rotulo,
                    )

        grupos: dict[
            tuple[
                str,
                str,
            ],
            list[
                tuple[
                    datetime,
                    str,
                ]
            ],
        ] = defaultdict(list)

        for (
            dimensao,
            chave,
            _fonte,
            _id_externo,
        ), registro in registros_por_sinal.items():

            grupos[
                (
                    dimensao,
                    chave,
                )
            ].append(registro)

        tendencias: list[TendenciaComercialScout] = []

        for (
            dimensao,
            chave,
        ), registros in grupos.items():

            sinais_distintos = len(registros)

            if sinais_distintos < minimo_sinais:
                continue

            (
                qualidade_temporal,
                cobertura_horas,
                minutos_distintos,
                concentracao_maxima_minuto,
            ) = self._avaliar_qualidade_temporal(
                registros,
                meio_janela=meio_janela,
            )

            if not qualidade_temporal:
                continue

            anteriores = sum(1 for instante, _rotulo in registros if instante < meio_janela)

            recentes = sum(1 for instante, _rotulo in registros if instante >= meio_janela)

            if recentes > anteriores:
                direcao = self.DIRECAO_ALTA

            elif recentes < anteriores:
                direcao = self.DIRECAO_QUEDA

            else:
                direcao = self.DIRECAO_ESTAVEL

            rotulo = self._escolher_rotulo(registros)

            evidencias = (
                "multiplos_sinais_distintos",
                f"sinais_distintos:{sinais_distintos}",
                f"janela_horas:{janela_horas}",
                f"periodo_anterior:{anteriores}",
                f"periodo_recente:{recentes}",
                "qualidade_temporal:aprovada",
                f"cobertura_horas:{cobertura_horas:.3f}",
                f"minutos_distintos:{minutos_distintos}",
                ("concentracao_maxima_minuto:" f"{concentracao_maxima_minuto:.3f}"),
                "ambas_metades_tem_sinais",
            )

            tendencias.append(
                TendenciaComercialScout(
                    dimensao=dimensao,
                    chave=chave,
                    rotulo=rotulo,
                    janela_horas=janela_horas,
                    sinais_distintos=(sinais_distintos),
                    ocorrencias_anteriores=(anteriores),
                    ocorrencias_recentes=(recentes),
                    direcao=direcao,
                    evidencias=evidencias,
                )
            )

        tendencias.sort(
            key=lambda item: (
                -item.sinais_distintos,
                item.dimensao,
                item.rotulo.casefold(),
                item.chave,
            )
        )

        return tendencias

    @classmethod
    def _avaliar_qualidade_temporal(
        cls,
        registros: list[
            tuple[
                datetime,
                str,
            ]
        ],
        *,
        meio_janela: datetime,
    ) -> tuple[
        bool,
        float,
        int,
        float,
    ]:
        """
        Impede que um lote concentrado ou um cold start
        seja interpretado como tendencia comercial.

        A verificacao e feita por dimensao/chave depois
        da deduplicacao por sinal.
        """

        if len(registros) < 2:
            return (
                False,
                0.0,
                0,
                1.0,
            )

        instantes = sorted(instante for instante, _rotulo in registros)

        cobertura_horas = (instantes[-1] - instantes[0]).total_seconds() / 3600.0

        minutos = Counter(
            instante.replace(
                second=0,
                microsecond=0,
            )
            for instante in instantes
        )

        minutos_distintos = len(minutos)

        concentracao_maxima_minuto = max(minutos.values()) / len(instantes)

        possui_periodo_anterior = any(instante < meio_janela for instante in instantes)

        possui_periodo_recente = any(instante >= meio_janela for instante in instantes)

        qualidade_temporal = (
            cobertura_horas >= cls.MINIMO_COBERTURA_TEMPORAL_HORAS
            and concentracao_maxima_minuto < cls.MAXIMA_CONCENTRACAO_MESMO_MINUTO
            and possui_periodo_anterior
            and possui_periodo_recente
        )

        return (
            qualidade_temporal,
            cobertura_horas,
            minutos_distintos,
            concentracao_maxima_minuto,
        )

    @classmethod
    def _extrair_dimensoes(
        cls,
        perfil: PerfilComercialScout,
    ) -> tuple[
        tuple[
            str,
            str,
            str,
        ],
        ...,
    ]:
        dimensoes: list[
            tuple[
                str,
                str,
                str,
            ]
        ] = []

        marketplace = str(perfil.marketplace or "").strip()

        if marketplace:

            chave = cls._normalizar_chave(marketplace)

            dimensoes.append(
                (
                    cls.DIMENSAO_MARKETPLACE,
                    chave,
                    marketplace,
                )
            )

        parceiro_id = str(perfil.parceiro_id or "").strip()

        parceiro_nome = str(perfil.parceiro_nome or "").strip()

        if parceiro_id:

            chave = "id:" + cls._normalizar_chave(parceiro_id)

            rotulo = parceiro_nome or parceiro_id

            dimensoes.append(
                (
                    cls.DIMENSAO_PARCEIRO,
                    chave,
                    rotulo,
                )
            )

        elif parceiro_nome:

            chave = "nome:" + cls._normalizar_chave(parceiro_nome)

            dimensoes.append(
                (
                    cls.DIMENSAO_PARCEIRO,
                    chave,
                    parceiro_nome,
                )
            )

        for termo in perfil.termos_descoberta or ():

            rotulo = str(termo or "").strip()

            if not rotulo:
                continue

            chave = cls._normalizar_chave(rotulo)

            dimensoes.append(
                (
                    cls.DIMENSAO_TERMO,
                    chave,
                    rotulo,
                )
            )

        codigo_cupom = str(perfil.codigo_voucher or "").strip()

        if codigo_cupom:

            dimensoes.append(
                (
                    cls.DIMENSAO_CUPOM,
                    cls._normalizar_chave(codigo_cupom),
                    codigo_cupom,
                )
            )

        resultado: list[
            tuple[
                str,
                str,
                str,
            ]
        ] = []

        vistos: set[
            tuple[
                str,
                str,
            ]
        ] = set()

        for (
            dimensao,
            chave,
            rotulo,
        ) in dimensoes:

            identidade = (
                dimensao,
                chave,
            )

            if identidade in vistos:
                continue

            vistos.add(identidade)

            resultado.append(
                (
                    dimensao,
                    chave,
                    rotulo,
                )
            )

        return tuple(resultado)

    @staticmethod
    def _escolher_rotulo(
        registros: list[
            tuple[
                datetime,
                str,
            ]
        ],
    ) -> str:
        contagem = Counter(rotulo for _instante, rotulo in registros if rotulo)

        if not contagem:
            return ""

        maior = max(contagem.values())

        candidatos = sorted(
            (rotulo for rotulo, quantidade in contagem.items() if quantidade == maior),
            key=str.casefold,
        )

        return candidatos[0]

    @staticmethod
    def _normalizar_chave(
        valor,
    ) -> str:
        texto = str(valor or "").strip().casefold()

        return re.sub(
            r"\s+",
            " ",
            texto,
        )

    @staticmethod
    def _normalizar_data(
        valor: datetime,
        *,
        campo: str,
    ) -> datetime:
        if not isinstance(
            valor,
            datetime,
        ):
            raise TypeError(f"{campo} deve ser datetime.")

        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError(f"{campo} deve possuir timezone.")

        return valor.astimezone(UTC)
