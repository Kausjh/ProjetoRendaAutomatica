from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config.filtro_ofertas import (
    LIMITE_OFERTAS_APROVADAS,
)
from config.historico_precos import (
    ARQUIVO_APROVADAS_ML,
    ARQUIVO_HISTORICO_ML,
    ARQUIVO_RANKING_ML,
    ARQUIVOS_COLETA_ML,
    LIMITE_REGISTROS_POR_PRODUTO,
)
from filters.filtro_qualidade import FiltroQualidade
from repositories.historico_precos_repository import (
    HistoricoPrecosRepository,
)
from services.analisador_historico_precos import (
    AnalisadorHistoricoPrecos,
)


RAIZ_PROJETO = Path(__file__).resolve().parents[1]


def carregar_json(
    caminho: Path,
) -> Any:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}"
        )

    with caminho.open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        return json.load(arquivo)


def salvar_json(
    caminho: Path,
    dados: Any,
) -> None:
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho_temporario = caminho.with_suffix(
        ".tmp"
    )

    with caminho_temporario.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    caminho_temporario.replace(
        caminho
    )


def localizar_arquivos_coleta() -> list[Path]:
    pasta_data = RAIZ_PROJETO / "data"

    encontrados: list[Path] = []

    for nome_arquivo in ARQUIVOS_COLETA_ML:
        candidatos = list(
            pasta_data.rglob(
                nome_arquivo
            )
        )

        candidatos = [
            caminho
            for caminho in candidatos
            if "processado" not in caminho.parts
            and "historico" not in caminho.parts
        ]

        if not candidatos:
            print(
                f"[AVISO] Não encontrado: {nome_arquivo}"
            )

            continue

        candidatos.sort(
            key=lambda caminho: caminho.stat().st_mtime,
            reverse=True,
        )

        encontrados.append(
            candidatos[0]
        )

    return encontrados


def extrair_lista_produtos(
    dados: Any,
) -> list[dict[str, Any]]:
    if isinstance(dados, list):
        return [
            produto
            for produto in dados
            if isinstance(
                produto,
                dict,
            )
        ]

    if not isinstance(dados, dict):
        return []

    for chave in (
        "produtos",
        "items",
        "resultados",
        "ofertas",
    ):
        valor = dados.get(
            chave
        )

        if isinstance(
            valor,
            list,
        ):
            return [
                produto
                for produto in valor
                if isinstance(
                    produto,
                    dict,
                )
            ]

    return []


def obter_texto(
    produto: dict[str, Any],
    *chaves: str,
) -> str:
    for chave in chaves:
        valor = produto.get(
            chave
        )

        if valor is None:
            continue

        texto = str(
            valor
        ).strip()

        if texto:
            return texto

    return ""


def obter_preco(
    produto: dict[str, Any],
) -> float | None:
    for chave in (
        "preco",
        "price",
        "preco_atual",
    ):
        valor = produto.get(
            chave
        )

        if valor is None or isinstance(
            valor,
            bool,
        ):
            continue

        if isinstance(
            valor,
            (int, float),
        ):
            preco = float(
                valor
            )

            if preco > 0:
                return preco

            continue

        texto = str(
            valor
        ).strip()

        texto = texto.replace(
            "R$",
            "",
        ).replace(
            " ",
            "",
        )

        if "," in texto and "." in texto:
            texto = texto.replace(
                ".",
                "",
            ).replace(
                ",",
                ".",
            )

        elif "," in texto:
            texto = texto.replace(
                ",",
                ".",
            )

        try:
            preco = float(
                texto
            )

        except ValueError:
            continue

        if preco > 0:
            return preco

    return None


def carregar_produtos_coletados() -> list[dict[str, Any]]:
    arquivos = localizar_arquivos_coleta()

    print()
    print("=" * 70)
    print("ARQUIVOS DE COLETA")
    print("=" * 70)

    todos_produtos: list[dict[str, Any]] = []

    for caminho in arquivos:
        dados = carregar_json(
            caminho
        )

        produtos = extrair_lista_produtos(
            dados
        )

        print(
            f"- {caminho.name}: "
            f"{len(produtos)} produtos"
        )

        todos_produtos.extend(
            produtos
        )

    return todos_produtos


def criar_mapa_analises(
    produtos: list[dict[str, Any]],
    repositorio: HistoricoPrecosRepository,
    analisador: AnalisadorHistoricoPrecos,
) -> dict[str, dict[str, Any]]:
    analises: dict[
        str,
        dict[str, Any],
    ] = {}

    for produto in produtos:
        preco = obter_preco(
            produto
        )

        if preco is None:
            continue

        chave = analisador.criar_chave_produto(
            produto
        )

        registros_anteriores = (
            repositorio.obter_registros(
                chave
            )
        )

        analise = analisador.analisar(
            preco_atual=preco,
            registros_anteriores=registros_anteriores,
        )

        analises[chave] = analise

    return analises


def registrar_precos_atuais(
    produtos: list[dict[str, Any]],
    repositorio: HistoricoPrecosRepository,
    analisador: AnalisadorHistoricoPrecos,
) -> tuple[int, int]:
    coletado_em = (
        datetime.now()
        .astimezone()
        .isoformat(timespec="seconds")
    )

    processados = 0
    alterados = 0

    for produto in produtos:
        preco = obter_preco(
            produto
        )

        if preco is None:
            continue

        chave = analisador.criar_chave_produto(
            produto
        )

        titulo = obter_texto(
            produto,
            "titulo",
            "nome",
            "title",
        )

        link = obter_texto(
            produto,
            "link",
            "url",
            "produto_url",
        )

        categoria = obter_texto(
            produto,
            "categoria",
            "category",
        )

        mudou = repositorio.registrar_preco(
            chave_produto=chave,
            titulo=titulo,
            link=link,
            categoria=categoria,
            preco=preco,
            coletado_em=coletado_em,
        )

        processados += 1

        if mudou:
            alterados += 1

    repositorio.salvar()

    return processados, alterados


def aplicar_historico_ao_ranking(
    ranking: list[dict[str, Any]],
    analises: dict[str, dict[str, Any]],
    analisador: AnalisadorHistoricoPrecos,
) -> list[dict[str, Any]]:
    ranking_atualizado: list[
        dict[str, Any]
    ] = []

    for produto in ranking:
        chave = analisador.criar_chave_produto(
            produto
        )

        analise = analises.get(
            chave
        )

        if analise is None:
            preco = obter_preco(
                produto
            )

            analise = analisador.analisar(
                preco_atual=preco,
                registros_anteriores=[],
            )

        nota_tecnica = produto.get(
            "nota_tecnica"
        )

        if not isinstance(
            nota_tecnica,
            (int, float),
        ):
            nota_tecnica = produto.get(
                "nota",
                0,
            )

        nota_historico = analise.get(
            "nota_historico",
            0,
        )

        nota_final = round(
            float(nota_tecnica)
            + float(nota_historico)
        )

        produto_atualizado = {
            **produto,
            "chave_historico": chave,
            "nota_tecnica": nota_tecnica,
            **analise,
            "nota": nota_final,
            "nota_final": nota_final,
        }

        motivos = list(
            produto.get(
                "motivos",
                [],
            )
        )

        motivo_historico = analise.get(
            "motivo_historico"
        )

        if motivo_historico:
            prefixo = (
                "+"
                if nota_historico > 0
                else ""
            )

            motivos.append(
                f"{prefixo}{nota_historico} Histórico: "
                f"{motivo_historico}"
            )

        produto_atualizado["motivos"] = motivos

        ranking_atualizado.append(
            produto_atualizado
        )

    ranking_atualizado.sort(
        key=lambda produto: (
            produto.get(
                "nota_final",
                0,
            ),
            produto.get(
                "nota_historico",
                0,
            ),
            produto.get(
                "desconto",
                0,
            )
            or 0,
            -(
                produto.get(
                    "preco",
                    0,
                )
                or 0
            ),
        ),
        reverse=True,
    )

    return ranking_atualizado


def exibir_top(
    produtos: list[dict[str, Any]],
    limite: int = 20,
) -> None:
    print()
    print("=" * 70)
    print("RANKING COM HISTÓRICO")
    print("=" * 70)

    for indice, produto in enumerate(
        produtos[:limite],
        start=1,
    ):
        titulo = produto.get(
            "titulo",
            "Sem título",
        )

        preco = produto.get(
            "preco"
        )

        nota_tecnica = produto.get(
            "nota_tecnica",
            0,
        )

        nota_historico = produto.get(
            "nota_historico",
            0,
        )

        nota_final = produto.get(
            "nota_final",
            0,
        )

        classificacao = produto.get(
            "classificacao_historico",
            "histórico insuficiente",
        )

        observacoes = produto.get(
            "quantidade_observacoes_anteriores",
            0,
        )

        preco_formatado = (
            f"R$ {float(preco):.2f}"
            if isinstance(
                preco,
                (int, float),
            )
            else "não informado"
        )

        print()
        print(
            f"{indice:02d}. {titulo}"
        )

        print(
            f"Preço: {preco_formatado}"
        )

        print(
            f"Nota técnica: {nota_tecnica}"
        )

        print(
            f"Nota histórica: {nota_historico}"
        )

        print(
            f"Nota final: {nota_final}"
        )

        print(
            f"Histórico: {classificacao} "
            f"({observacoes} registros anteriores)"
        )

        mediana = produto.get(
            "preco_mediano_historico"
        )

        minimo = produto.get(
            "preco_minimo_historico"
        )

        if isinstance(
            mediana,
            (int, float),
        ):
            print(
                f"Mediana histórica: "
                f"R$ {mediana:.2f}"
            )

        if isinstance(
            minimo,
            (int, float),
        ):
            print(
                f"Menor preço anterior: "
                f"R$ {minimo:.2f}"
            )


def main() -> None:
    print("=" * 70)
    print("HISTÓRICO DE PREÇOS - MERCADO LIVRE")
    print("=" * 70)

    caminho_historico = (
        RAIZ_PROJETO
        / ARQUIVO_HISTORICO_ML
    )

    caminho_ranking = (
        RAIZ_PROJETO
        / ARQUIVO_RANKING_ML
    )

    caminho_aprovadas = (
        RAIZ_PROJETO
        / ARQUIVO_APROVADAS_ML
    )

    repositorio = HistoricoPrecosRepository(
        caminho_arquivo=caminho_historico,
        limite_registros_por_produto=(
            LIMITE_REGISTROS_POR_PRODUTO
        ),
    )

    analisador = AnalisadorHistoricoPrecos()

    produtos_coletados = (
        carregar_produtos_coletados()
    )

    if not produtos_coletados:
        raise RuntimeError(
            "Nenhum produto coletado foi encontrado."
        )

    analises = criar_mapa_analises(
        produtos=produtos_coletados,
        repositorio=repositorio,
        analisador=analisador,
    )

    ranking = carregar_json(
        caminho_ranking
    )

    if not isinstance(
        ranking,
        list,
    ):
        raise RuntimeError(
            "O ranking completo precisa ser "
            "uma lista de produtos."
        )

    ranking_atualizado = (
        aplicar_historico_ao_ranking(
            ranking=ranking,
            analises=analises,
            analisador=analisador,
        )
    )

    filtro = FiltroQualidade()

    aprovadas = filtro.obter_aprovados(
        ranking=ranking_atualizado,
        limite=LIMITE_OFERTAS_APROVADAS,
    )

    salvar_json(
        caminho_ranking,
        ranking_atualizado,
    )

    salvar_json(
        caminho_aprovadas,
        aprovadas,
    )

    processados, alterados = (
        registrar_precos_atuais(
            produtos=produtos_coletados,
            repositorio=repositorio,
            analisador=analisador,
        )
    )

    print()
    print("=" * 70)
    print("RESUMO DO HISTÓRICO")
    print("=" * 70)

    print(
        f"Produtos coletados: "
        f"{len(produtos_coletados)}"
    )

    print(
        f"Preços válidos processados: "
        f"{processados}"
    )

    print(
        f"Registros inseridos ou atualizados: "
        f"{alterados}"
    )

    print(
        f"Produtos existentes no histórico: "
        f"{repositorio.quantidade_produtos()}"
    )

    print(
        f"Produtos selecionados: "
        f"{len(aprovadas)}"
    )

    exibir_top(
        aprovadas
    )

    print()
    print("=" * 70)
    print("ARQUIVOS SALVOS")
    print("=" * 70)

    print()
    print("Histórico:")
    print(
        caminho_historico
    )

    print()
    print("Ranking atualizado:")
    print(
        caminho_ranking
    )

    print()
    print("Ofertas aprovadas:")
    print(
        caminho_aprovadas
    )


if __name__ == "__main__":
    main()