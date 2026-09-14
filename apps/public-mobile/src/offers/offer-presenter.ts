import {
  PriceHistoryPoint,
  ProductCard,
  ProductDetail,
  ProductListPage,
} from "@/src/offers/offer-types";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function firstString(
  record: UnknownRecord,
  keys: readonly string[],
): string | null {
  for (const key of keys) {
    const value = record[key];

    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }

  return null;
}

function firstNumber(
  record: UnknownRecord,
  keys: readonly string[],
): number | null {
  for (const key of keys) {
    const value = record[key];

    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }

    if (typeof value === "string" && value.trim()) {
      const normalized = value
        .trim()
        .replace(/\s/g, "")
        .replace(/^R\$/i, "")
        .replace(",", ".");

      const parsed = Number(normalized);

      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return null;
}

function unwrapSingleRecord(payload: unknown): UnknownRecord | null {
  if (!isRecord(payload)) {
    return null;
  }

  for (const key of ["produto", "item", "dados", "resultado"]) {
    const nested = payload[key];

    if (isRecord(nested)) {
      return nested;
    }
  }

  return payload;
}

function extractArray(payload: unknown): unknown[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (!isRecord(payload)) {
    return [];
  }

  for (const key of [
    "produtos",
    "itens",
    "items",
    "resultados",
    "dados",
    "historico",
    "registros",
  ]) {
    const value = payload[key];

    if (Array.isArray(value)) {
      return value;
    }

    if (isRecord(value)) {
      for (const nestedKey of [
        "produtos",
        "itens",
        "items",
        "historico",
        "registros",
      ]) {
        const nested = value[nestedKey];

        if (Array.isArray(nested)) {
          return nested;
        }
      }
    }
  }

  return [];
}

function normalizeProduct(record: UnknownRecord): ProductCard | null {
  const canonicalKey = firstString(record, [
    "chave_canonica",
    "canonical_key",
    "canonicalKey",
    "id_canonico",
    "id",
  ]);

  if (!canonicalKey) {
    return null;
  }

  const title =
    firstString(record, [
      "titulo",
      "title",
      "nome",
      "name",
      "produto",
    ]) ?? canonicalKey;

  return {
    canonicalKey,
    title,
    marketplace: firstString(record, [
      "marketplace",
      "origem",
      "source",
      "loja",
    ]),
    currentPrice: firstNumber(record, [
      "preco_atual",
      "preco",
      "price",
      "current_price",
      "melhor_preco",
    ]),
    originalPrice: firstNumber(record, [
      "preco_original",
      "original_price",
      "preco_de",
      "list_price",
    ]),
    discountPercent: firstNumber(record, [
      "desconto_percentual",
      "desconto",
      "discount_percent",
      "discount",
    ]),
    productUrl: firstString(record, [
      "url",
      "link",
      "link_publicacao",
      "product_url",
    ]),
  };
}

export function presentProductList(payload: unknown): ProductListPage {
  const source = extractArray(payload);

  const items = source
    .filter(isRecord)
    .map(normalizeProduct)
    .filter((item): item is ProductCard => item !== null);

  let total: number | null = null;

  if (isRecord(payload)) {
    total = firstNumber(payload, [
      "total",
      "quantidade",
      "count",
    ]);
  }

  return {
    items,
    total,
  };
}

export function presentProductDetail(
  payload: unknown,
  fallbackCanonicalKey: string,
): ProductDetail {
  const record = unwrapSingleRecord(payload) ?? {};
  const normalized = normalizeProduct({
    ...record,
    chave_canonica:
      firstString(record, [
        "chave_canonica",
        "canonical_key",
        "canonicalKey",
        "id_canonico",
        "id",
      ]) ?? fallbackCanonicalKey,
  });

  const card =
    normalized ??
    ({
      canonicalKey: fallbackCanonicalKey,
      title: fallbackCanonicalKey,
      marketplace: null,
      currentPrice: null,
      originalPrice: null,
      discountPercent: null,
      productUrl: null,
    } satisfies ProductCard);

  return {
    ...card,
    raw: record,
  };
}

export function presentPriceHistory(
  payload: unknown,
): readonly PriceHistoryPoint[] {
  return extractArray(payload)
    .filter(isRecord)
    .map((record) => ({
      timestamp: firstString(record, [
        "capturado_em",
        "timestamp",
        "data",
        "created_at",
        "registrado_em",
      ]),
      price: firstNumber(record, [
        "preco",
        "price",
        "preco_atual",
        "valor",
      ]),
      marketplace: firstString(record, [
        "marketplace",
        "origem",
        "source",
        "loja",
      ]),
    }));
}

export function formatPrice(value: number | null): string {
  if (value === null) {
    return "Preço indisponível";
  }

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

export function formatHistoryTimestamp(value: string | null): string {
  if (!value) {
    return "Data não informada";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}
