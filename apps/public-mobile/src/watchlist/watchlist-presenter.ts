import {
  WatchlistCollection,
  WatchlistItem,
} from "@/src/watchlist/watchlist-types";

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
      const parsed = Number(
        value
          .trim()
          .replace(/\s/g, "")
          .replace(/^R\$/i, "")
          .replace(",", "."),
      );

      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return null;
}

function firstBoolean(
  record: UnknownRecord,
  keys: readonly string[],
  fallback: boolean,
): boolean {
  for (const key of keys) {
    const value = record[key];

    if (typeof value === "boolean") {
      return value;
    }

    if (value === 1 || value === "1" || value === "true") {
      return true;
    }

    if (value === 0 || value === "0" || value === "false") {
      return false;
    }
  }

  return fallback;
}

function extractArray(payload: unknown): unknown[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (!isRecord(payload)) {
    return [];
  }

  for (const key of [
    "watchlist",
    "itens",
    "items",
    "dados",
    "resultados",
  ]) {
    const value = payload[key];

    if (Array.isArray(value)) {
      return value;
    }

    if (isRecord(value)) {
      for (const nestedKey of [
        "watchlist",
        "itens",
        "items",
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

function normalizeItem(
  record: UnknownRecord,
): WatchlistItem | null {
  const canonicalKey = firstString(record, [
    "chave_canonica",
    "canonical_key",
    "canonicalKey",
  ]);

  if (!canonicalKey) {
    return null;
  }

  return {
    canonicalKey,
    targetPrice: firstNumber(record, [
      "preco_alvo",
      "target_price",
      "targetPrice",
    ]),
    notifyPriceDrop: firstBoolean(
      record,
      [
        "notificar_queda_preco",
        "notify_price_drop",
        "notifyPriceDrop",
      ],
      true,
    ),
  };
}

export function presentWatchlist(
  payload: unknown,
): WatchlistCollection {
  const items = extractArray(payload)
    .filter(isRecord)
    .map(normalizeItem)
    .filter((item): item is WatchlistItem => item !== null);

  return { items };
}
