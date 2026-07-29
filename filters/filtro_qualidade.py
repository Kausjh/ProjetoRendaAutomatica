from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any

from config.filtro_ofertas import (
    CATEGORIAS_PRIORITARIAS,
    FAIXA_PRECO_IDEAL_MAXIMA,
    FAIXA_PRECO_IDEAL_MINIMA,
    HARDWARE_ULTRAPASSADO,
    LIMITE_OFERTAS_APROVADAS,
    LIMITE_PALAVRAS_TITULO_LONGO,
    LIMITE_PALAVRAS_TITULO_MUITO_LONGO,
    LIMITE_PRODUTOS_MESMO_MODELO,
    LIMITES_POR_TIPO,
    MARCADORES_COMPATIBILIDADE,
    MARCAS_PRIORITARIAS,
    NOTA_MINIMA_PUBLICACAO,
    PALAVRAS_ANUNCIO_GENERICO,
    PALAVRAS_PROIBIDAS,
    PALAVRAS_TECNOLOGIA,
    PENALIDADE_ACESSORIO_SEM_MARCA,
    PENALIDADE_ALEGACAO_SUSPEITA,
    PENALIDADE_ANUNCIO_GENERICO,
    PENALIDADE_HARDWARE_ULTRAPASSADO,
    PENALIDADE_PALAVRA_PROIBIDA,
    PENALIDADE_PRECO_FORA_DA_FAIXA,
    PENALIDADE_SEM_IMAGEM,
    PENALIDADE_SEM_LINK,
    PENALIDADE_SEM_PRECO,
    PENALIDADE_TITULO_LONGO,
    PENALIDADE_TITULO_MUITO_LONGO,
    PONTOS_DESCONTO_20,
    PONTOS_DESCONTO_30,
    PONTOS_DESCONTO_40,
    PONTOS_DESCONTO_50,
    PONTOS_PRECO_ACEITAVEL,
    PONTOS_PRECO_IDEAL,
    PRECO_MAXIMO,
    PRECO_MINIMO,
    PREFIXOS_COMPATIBILIDADE_MARCA,
    TIPOS_ACESSORIOS_COMPATIVEIS,
)


class FiltroQualidade:
    def analisar_produtos(
        self,
        produtos: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ranking = [self.analisar_produto(produto) for produto in produtos]

        ranking.sort(
            key=lambda produto: (
                produto.get("nota", 0),
                produto.get("desconto", 0) or 0,
                -(produto.get("preco", 0) or 0),
            ),
            reverse=True,
        )

        return ranking

    def obter_aprovados(
        self,
        ranking: list[dict[str, Any]],
        limite: int = LIMITE_OFERTAS_APROVADAS,
    ) -> list[dict[str, Any]]:
        candidatos = [produto for produto in ranking if produto.get("aprovado") is True]

        selecionados: list[dict[str, Any]] = []
        quantidade_por_tipo: dict[str, int] = {}
        quantidade_por_modelo: dict[str, int] = {}

        for produto in candidatos:
            if len(selecionados) >= limite:
                break

            tipo = produto.get("tipo_detectado") or "outros"

            limite_tipo = LIMITES_POR_TIPO.get(
                tipo,
                3,
            )

            quantidade_tipo = quantidade_por_tipo.get(
                tipo,
                0,
            )

            if quantidade_tipo >= limite_tipo:
                continue

            chave_modelo = self._criar_chave_modelo(produto)

            quantidade_modelo = quantidade_por_modelo.get(
                chave_modelo,
                0,
            )

            if quantidade_modelo >= LIMITE_PRODUTOS_MESMO_MODELO:
                continue

            selecionados.append(produto)

            quantidade_por_tipo[tipo] = quantidade_tipo + 1

            quantidade_por_modelo[chave_modelo] = quantidade_modelo + 1

        return selecionados

    def analisar_produto(
        self,
        produto_original: dict[str, Any],
    ) -> dict[str, Any]:
        produto = deepcopy(produto_original)

        titulo = self._obter_texto(
            produto,
            "titulo",
            "title",
            "nome",
        )

        categoria = self._obter_texto(
            produto,
            "categoria",
            "category",
        )

        link = self._obter_texto(
            produto,
            "link",
            "url",
            "produto_url",
        )

        imagem = self._obter_texto(
            produto,
            "imagem",
            "image",
            "image_url",
        )

        preco = self._obter_numero(
            produto,
            "preco",
            "price",
            "preco_atual",
        )

        desconto = self._obter_numero(
            produto,
            "desconto",
            "discount",
            "percentual_desconto",
        )

        titulo_normalizado = self._normalizar_texto(titulo)

        categoria_normalizada = self._normalizar_texto(categoria)

        nota = 0
        motivos: list[str] = []
        bloqueado = False

        pontos, novos_motivos, bloqueia = self._avaliar_palavras_proibidas(titulo_normalizado)
        nota += pontos
        motivos.extend(novos_motivos)
        bloqueado = bloqueado or bloqueia

        tipo_produto, pontos, novos_motivos = self._avaliar_tipo_produto(titulo_normalizado)
        nota += pontos
        motivos.extend(novos_motivos)

        marca, pontos, novos_motivos = self._avaliar_marca(
            titulo=titulo_normalizado,
            tipo_produto=tipo_produto,
        )
        nota += pontos
        motivos.extend(novos_motivos)

        pontos, novos_motivos = self._avaliar_acessorio_sem_marca(
            tipo_produto=tipo_produto,
            marca=marca,
        )
        nota += pontos
        motivos.extend(novos_motivos)

        pontos, novos_motivos, bloqueia = self._avaliar_hardware_ultrapassado(titulo_normalizado)
        nota += pontos
        motivos.extend(novos_motivos)
        bloqueado = bloqueado or bloqueia

        pontos, novos_motivos, bloqueia = self._avaliar_alegacoes_suspeitas(
            titulo=titulo_normalizado,
            marca=marca,
            tipo_produto=tipo_produto,
        )
        nota += pontos
        motivos.extend(novos_motivos)
        bloqueado = bloqueado or bloqueia

        pontos, novos_motivos = self._avaliar_qualidade_titulo(titulo_normalizado)
        nota += pontos
        motivos.extend(novos_motivos)

        pontos, novos_motivos, bloqueia = self._avaliar_preco(preco)
        nota += pontos
        motivos.extend(novos_motivos)
        bloqueado = bloqueado or bloqueia

        pontos, novos_motivos = self._avaliar_desconto(desconto)
        nota += pontos
        motivos.extend(novos_motivos)

        pontos, novos_motivos = self._avaliar_categoria(categoria_normalizada)
        nota += pontos
        motivos.extend(novos_motivos)

        pontos, novos_motivos, bloqueia = self._avaliar_link(link)
        nota += pontos
        motivos.extend(novos_motivos)
        bloqueado = bloqueado or bloqueia

        pontos, novos_motivos = self._avaliar_imagem(imagem)
        nota += pontos
        motivos.extend(novos_motivos)

        aprovado = not bloqueado and nota >= NOTA_MINIMA_PUBLICACAO

        produto["titulo"] = titulo
        produto["categoria"] = categoria
        produto["preco"] = preco
        produto["desconto"] = desconto
        produto["link"] = link
        produto["imagem"] = imagem
        produto["marca_detectada"] = marca
        produto["tipo_detectado"] = tipo_produto
        produto["nota"] = nota
        produto["bloqueado"] = bloqueado
        produto["aprovado"] = aprovado
        produto["motivos"] = motivos

        return produto

    def _avaliar_palavras_proibidas(
        self,
        titulo: str,
    ) -> tuple[int, list[str], bool]:
        encontradas = [
            palavra
            for palavra in PALAVRAS_PROIBIDAS
            if self._contem_termo_ou_frase(
                titulo,
                palavra,
            )
        ]

        if not encontradas:
            return 0, [], False

        palavra = sorted(encontradas)[0]

        return (
            PENALIDADE_PALAVRA_PROIBIDA,
            [f"{PENALIDADE_PALAVRA_PROIBIDA} " f"Palavra proibida: {palavra}"],
            True,
        )

    def _avaliar_marca(
        self,
        titulo: str,
        tipo_produto: str,
    ) -> tuple[str, int, list[str]]:
        marca_declarada = self._extrair_marca_declarada(titulo)

        if marca_declarada:
            if marca_declarada in MARCAS_PRIORITARIAS:
                pontos = MARCAS_PRIORITARIAS[marca_declarada]

                return (
                    marca_declarada,
                    pontos,
                    [f"+{pontos} Marca declarada: " f"{marca_declarada}"],
                )

            return (
                marca_declarada,
                0,
                ["0 Marca declarada não prioritária: " f"{marca_declarada}"],
            )

        marcas_encontradas: list[tuple[int, str, int]] = []

        for marca, pontos in MARCAS_PRIORITARIAS.items():
            posicoes = self._encontrar_todas_posicoes_termo(
                titulo,
                marca,
            )

            for posicao in posicoes:
                if self._marca_eh_compatibilidade(
                    titulo=titulo,
                    marca=marca,
                    posicao=posicao,
                    tipo_produto=tipo_produto,
                ):
                    continue

                marcas_encontradas.append((posicao, marca, pontos))

        if not marcas_encontradas:
            return (
                "",
                0,
                ["0 Marca prioritária não identificada"],
            )

        marcas_encontradas.sort(
            key=lambda item: (
                item[0],
                -item[2],
            )
        )

        _, marca, pontos = marcas_encontradas[0]

        return (
            marca,
            pontos,
            [f"+{pontos} Marca prioritária: " f"{marca}"],
        )

    def _marca_eh_compatibilidade(
        self,
        titulo: str,
        marca: str,
        posicao: int,
        tipo_produto: str,
    ) -> bool:
        inicio_contexto = max(
            0,
            posicao - 45,
        )

        contexto_anterior = titulo[inicio_contexto:posicao].strip()

        for prefixo in PREFIXOS_COMPATIBILIDADE_MARCA:
            prefixo_normalizado = self._normalizar_texto(prefixo)

            if contexto_anterior.endswith(prefixo_normalizado):
                return True

        if tipo_produto in TIPOS_ACESSORIOS_COMPATIVEIS:
            palavras_antes = contexto_anterior.split()

            if palavras_antes:
                ultimas_palavras = " ".join(palavras_antes[-5:])

                marcadores = (
                    "para",
                    "compativel",
                    "compatível",
                    "notebook",
                    "celular",
                    "smartphone",
                    "iphone",
                    "galaxy",
                    "ideapad",
                    "moto",
                    "redmi",
                    "poco",
                )

                if any(marcador in ultimas_palavras for marcador in marcadores):
                    return True

        trecho_principal = self._obter_trecho_principal_marca(titulo)

        if posicao >= len(trecho_principal):
            return True

        return False

    def _avaliar_tipo_produto(
        self,
        titulo: str,
    ) -> tuple[str, int, list[str]]:
        encontrados: list[tuple[int, int, str, int]] = []

        for termo, pontos in PALAVRAS_TECNOLOGIA.items():
            posicao = self._encontrar_posicao_termo(
                titulo,
                termo,
            )

            if posicao is None:
                continue

            encontrados.append(
                (
                    posicao,
                    -len(termo),
                    termo,
                    pontos,
                )
            )

        if not encontrados:
            return (
                "",
                0,
                ["0 Tipo de produto não identificado"],
            )

        encontrados.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        _, _, termo, pontos = encontrados[0]

        return (
            termo,
            pontos,
            [f"+{pontos} Produto relevante: " f"{termo}"],
        )

    @staticmethod
    def _avaliar_acessorio_sem_marca(
        tipo_produto: str,
        marca: str,
    ) -> tuple[int, list[str]]:
        if tipo_produto not in TIPOS_ACESSORIOS_COMPATIVEIS:
            return 0, []

        if marca:
            return 0, []

        return (
            PENALIDADE_ACESSORIO_SEM_MARCA,
            [f"{PENALIDADE_ACESSORIO_SEM_MARCA} " "Acessório sem fabricante confiável"],
        )

    def _avaliar_hardware_ultrapassado(
        self,
        titulo: str,
    ) -> tuple[int, list[str], bool]:
        encontrados = [
            termo
            for termo in HARDWARE_ULTRAPASSADO
            if self._contem_termo_ou_frase(
                titulo,
                termo,
            )
        ]

        if not encontrados:
            return 0, [], False

        termo = encontrados[0]

        return (
            PENALIDADE_HARDWARE_ULTRAPASSADO,
            [f"{PENALIDADE_HARDWARE_ULTRAPASSADO} " f"Hardware ultrapassado: {termo}"],
            True,
        )

    def _avaliar_alegacoes_suspeitas(
        self,
        titulo: str,
        marca: str,
        tipo_produto: str,
    ) -> tuple[int, list[str], bool]:
        marca_confiavel = marca in MARCAS_PRIORITARIAS

        if marca_confiavel:
            return 0, [], False

        capacidade = self._extrair_capacidade_mah(titulo)

        if (
            tipo_produto
            in {
                "power bank",
                "carregador portátil",
                "carregador portatil",
            }
            and capacidade is not None
            and capacidade >= 30000
        ):
            return (
                PENALIDADE_ALEGACAO_SUSPEITA,
                [
                    f"{PENALIDADE_ALEGACAO_SUSPEITA} "
                    "Capacidade suspeita em produto "
                    f"sem marca confiável: {capacidade}mAh"
                ],
                True,
            )

        potencia = self._extrair_potencia_watts(titulo)

        if tipo_produto == "carregador" and potencia is not None and potencia >= 100:
            return (
                PENALIDADE_ALEGACAO_SUSPEITA,
                [
                    f"{PENALIDADE_ALEGACAO_SUSPEITA} "
                    "Potência suspeita em carregador "
                    f"sem marca confiável: {potencia}W"
                ],
                True,
            )

        return 0, [], False

    def _avaliar_qualidade_titulo(
        self,
        titulo: str,
    ) -> tuple[int, list[str]]:
        quantidade_palavras = len(titulo.split())

        pontos = 0
        motivos: list[str] = []

        if quantidade_palavras >= LIMITE_PALAVRAS_TITULO_MUITO_LONGO:
            pontos += PENALIDADE_TITULO_MUITO_LONGO

            motivos.append(
                f"{PENALIDADE_TITULO_MUITO_LONGO} "
                "Título excessivamente longo: "
                f"{quantidade_palavras} palavras"
            )

        elif quantidade_palavras >= LIMITE_PALAVRAS_TITULO_LONGO:
            pontos += PENALIDADE_TITULO_LONGO

            motivos.append(
                f"{PENALIDADE_TITULO_LONGO} "
                "Título muito longo: "
                f"{quantidade_palavras} palavras"
            )

        palavras_genericas = [
            palavra
            for palavra in PALAVRAS_ANUNCIO_GENERICO
            if self._contem_termo_ou_frase(
                titulo,
                palavra,
            )
        ]

        if len(palavras_genericas) >= 2:
            pontos += PENALIDADE_ANUNCIO_GENERICO

            motivos.append(
                f"{PENALIDADE_ANUNCIO_GENERICO} "
                "Anúncio com excesso de termos genéricos: " + ", ".join(palavras_genericas[:4])
            )

        return pontos, motivos

    def _avaliar_preco(
        self,
        preco: float | None,
    ) -> tuple[int, list[str], bool]:
        if preco is None or preco <= 0:
            return (
                PENALIDADE_SEM_PRECO,
                [f"{PENALIDADE_SEM_PRECO} " "Produto sem preço válido"],
                True,
            )

        if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
            return (
                PENALIDADE_PRECO_FORA_DA_FAIXA,
                [f"{PENALIDADE_PRECO_FORA_DA_FAIXA} " f"Preço fora da faixa: R$ {preco:.2f}"],
                True,
            )

        if FAIXA_PRECO_IDEAL_MINIMA <= preco <= FAIXA_PRECO_IDEAL_MAXIMA:
            return (
                PONTOS_PRECO_IDEAL,
                [f"+{PONTOS_PRECO_IDEAL} " "Preço na faixa ideal"],
                False,
            )

        return (
            PONTOS_PRECO_ACEITAVEL,
            [f"+{PONTOS_PRECO_ACEITAVEL} " "Preço aceitável"],
            False,
        )

    def _avaliar_desconto(
        self,
        desconto: float | None,
    ) -> tuple[int, list[str]]:
        if desconto is None or desconto <= 0:
            return 0, ["0 Desconto não informado"]

        if desconto >= 50:
            pontos = PONTOS_DESCONTO_50
        elif desconto >= 40:
            pontos = PONTOS_DESCONTO_40
        elif desconto >= 30:
            pontos = PONTOS_DESCONTO_30
        elif desconto >= 20:
            pontos = PONTOS_DESCONTO_20
        else:
            return (
                0,
                [f"0 Desconto baixo: " f"{desconto:.0f}%"],
            )

        return (
            pontos,
            [f"+{pontos} Desconto de " f"{desconto:.0f}%"],
        )

    def _avaliar_categoria(
        self,
        categoria: str,
    ) -> tuple[int, list[str]]:
        for nome, pontos in CATEGORIAS_PRIORITARIAS.items():
            nome_normalizado = self._normalizar_texto(nome)

            if nome_normalizado in categoria:
                return (
                    pontos,
                    [f"+{pontos} Categoria prioritária: " f"{nome}"],
                )

        return 0, ["0 Categoria não reconhecida"]

    @staticmethod
    def _avaliar_link(
        link: str,
    ) -> tuple[int, list[str], bool]:
        if not link:
            return (
                PENALIDADE_SEM_LINK,
                [f"{PENALIDADE_SEM_LINK} " "Produto sem link"],
                True,
            )

        if not link.startswith(("http://", "https://")):
            return (
                PENALIDADE_SEM_LINK,
                [f"{PENALIDADE_SEM_LINK} " "Link inválido"],
                True,
            )

        return 0, [], False

    @staticmethod
    def _avaliar_imagem(
        imagem: str,
    ) -> tuple[int, list[str]]:
        if imagem:
            return 0, []

        return (
            PENALIDADE_SEM_IMAGEM,
            [f"{PENALIDADE_SEM_IMAGEM} " "Produto sem imagem"],
        )

    def _obter_trecho_principal_marca(
        self,
        titulo: str,
    ) -> str:
        limite = len(titulo)

        for marcador in MARCADORES_COMPATIBILIDADE:
            marcador_normalizado = self._normalizar_texto(marcador)

            posicao = titulo.find(marcador_normalizado)

            if posicao >= 0:
                limite = min(
                    limite,
                    posicao,
                )

        return titulo[:limite].strip()

    def _extrair_marca_declarada(
        self,
        titulo: str,
    ) -> str:
        padroes = (
            r"\bmarca\s*[:\-]?\s*([a-z0-9][a-z0-9\-]{1,25})",
            r"\bfabricante\s*[:\-]?\s*([a-z0-9][a-z0-9\-]{1,25})",
        )

        for padrao in padroes:
            correspondencia = re.search(
                padrao,
                titulo,
                flags=re.IGNORECASE,
            )

            if correspondencia:
                return self._normalizar_texto(correspondencia.group(1))

        return ""

    def _criar_chave_modelo(
        self,
        produto: dict[str, Any],
    ) -> str:
        titulo = self._normalizar_texto(str(produto.get("titulo") or ""))

        marca = self._normalizar_texto(str(produto.get("marca_detectada") or ""))

        tipo = self._normalizar_texto(str(produto.get("tipo_detectado") or ""))

        palavras_ignoradas = {
            "preto",
            "preta",
            "branco",
            "branca",
            "azul",
            "rosa",
            "rose",
            "vermelho",
            "vermelha",
            "cinza",
            "verde",
            "cor",
            "bivolt",
            "novo",
            "nova",
            "original",
            "gamer",
        }

        tokens = re.findall(
            r"[a-z0-9]+",
            titulo,
        )

        tokens_filtrados = [token for token in tokens if token not in palavras_ignoradas]

        tokens_modelo = tokens_filtrados[:10]

        return f"{marca}|{tipo}|" + " ".join(tokens_modelo)

    @staticmethod
    def _extrair_capacidade_mah(
        titulo: str,
    ) -> int | None:
        correspondencia = re.search(
            r"\b(\d{4,6})\s*mah\b",
            titulo,
            flags=re.IGNORECASE,
        )

        if not correspondencia:
            return None

        try:
            return int(correspondencia.group(1))
        except ValueError:
            return None

    @staticmethod
    def _extrair_potencia_watts(
        titulo: str,
    ) -> int | None:
        correspondencia = re.search(
            r"\b(\d{2,4})\s*w\b",
            titulo,
            flags=re.IGNORECASE,
        )

        if not correspondencia:
            return None

        try:
            return int(correspondencia.group(1))
        except ValueError:
            return None

    @staticmethod
    def _obter_texto(
        produto: dict[str, Any],
        *chaves: str,
    ) -> str:
        for chave in chaves:
            valor = produto.get(chave)

            if valor is not None:
                texto = str(valor).strip()

                if texto:
                    return texto

        return ""

    @classmethod
    def _obter_numero(
        cls,
        produto: dict[str, Any],
        *chaves: str,
    ) -> float | None:
        for chave in chaves:
            valor = produto.get(chave)

            numero = cls._converter_para_float(valor)

            if numero is not None:
                return numero

        return None

    @staticmethod
    def _converter_para_float(
        valor: Any,
    ) -> float | None:
        if valor is None:
            return None

        if isinstance(valor, bool):
            return None

        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()

        if not texto:
            return None

        texto = texto.replace("R$", "")
        texto = texto.replace("%", "")
        texto = texto.replace(" ", "")

        if "," in texto and "." in texto:
            texto = texto.replace(".", "")
            texto = texto.replace(",", ".")

        elif "," in texto:
            texto = texto.replace(",", ".")

        texto = re.sub(
            r"[^0-9.\-]",
            "",
            texto,
        )

        try:
            return float(texto)
        except ValueError:
            return None

    @staticmethod
    def _normalizar_texto(
        texto: str,
    ) -> str:
        texto = unicodedata.normalize(
            "NFKD",
            texto,
        )

        texto = texto.encode(
            "ascii",
            "ignore",
        ).decode("ascii")

        texto = texto.lower()

        texto = re.sub(
            r"\s+",
            " ",
            texto,
        )

        return texto.strip()

    @staticmethod
    def _encontrar_posicao_termo(
        texto: str,
        termo: str,
    ) -> int | None:
        posicoes = FiltroQualidade._encontrar_todas_posicoes_termo(
            texto,
            termo,
        )

        if not posicoes:
            return None

        return posicoes[0]

    @staticmethod
    def _encontrar_todas_posicoes_termo(
        texto: str,
        termo: str,
    ) -> list[int]:
        termo_normalizado = FiltroQualidade._normalizar_texto(termo)

        termo_escapado = re.escape(termo_normalizado)

        padrao = rf"(?<![a-z0-9])" rf"{termo_escapado}" rf"(?![a-z0-9])"

        return [
            correspondencia.start()
            for correspondencia in re.finditer(
                padrao,
                texto,
                flags=re.IGNORECASE,
            )
        ]

    @classmethod
    def _contem_termo_ou_frase(
        cls,
        texto: str,
        termo: str,
    ) -> bool:
        return (
            cls._encontrar_posicao_termo(
                texto,
                termo,
            )
            is not None
        )
