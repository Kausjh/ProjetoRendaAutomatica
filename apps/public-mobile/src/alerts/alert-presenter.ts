import {
  AlertCard,
  AlertListPage,
} from "@/src/alerts/alert-types";

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

    if (
      (typeof value === "number" || typeof value === "bigint") &&
      String(value).trim()
    ) {
      return String(value);
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

function extractArray(payload: unknown): unknown[] {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (!isRecord(payload)) {
    return [];
  }

  for (const key of [
    "alertas",
    "alerts",
    "eventos",
    "events",
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
        "alertas",
        "alerts",
        "eventos",
        "events",
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

function titleForType(type: string): string {
  const normalized = type.trim().toLowerCase();

  if (
    normalized.includes("novo_menor_preco") ||
    normalized.includes("historical_low") ||
    normalized.includes("menor_preco")
  ) {
    return "Novo menor preço";
  }

  if (
    normalized.includes("mudanca_preco") ||
    normalized.includes("price_change")
  ) {
    return "Mudança de preço";
  }

  if (
    normalized.includes("queda_preco") ||
    normalized.includes("price_drop")
  ) {
    return "Queda de preço";
  }

  if (
    normalized.includes("promoc") ||
    normalized.includes("deal")
  ) {
    return "Oportunidade detectada";
  }

  return type || "Alerta";
}

function normalizeAlert(
  record: UnknownRecord,
  index: number,
): AlertCard {
  const type =
    firstString(record, [
      "tipo",
      "type",
      "tipo_evento",
      "event_type",
      "evento",
    ]) ?? "alerta";

  const canonicalKey = firstString(record, [
    "chave_canonica",
    "canonical_key",
    "canonicalKey",
  ]);

  const marketplace = firstString(record, [
    "marketplace",
    "origem",
    "source",
    "loja",
  ]);

  const occurredAt = firstString(record, [
    "ocorrido_em",
    "created_at",
    "criado_em",
    "timestamp",
    "data",
    "registrado_em",
  ]);

  const explicitId = firstString(record, [
    "id",
    "alerta_id",
    "evento_id",
    "event_id",
  ]);

  const message = firstString(record, [
    "mensagem",
    "message",
    "descricao",
    "description",
    "motivo",
    "reason",
  ]);

  return {
    id:
      explicitId ??
      [
        type,
        canonicalKey ?? "sem-produto",
        occurredAt ?? "sem-data",
        String(index),
      ].join(":"),
    type,
    title: titleForType(type),
    message,
    canonicalKey,
    marketplace,
    previousPrice: firstNumber(record, [
      "preco_anterior",
      "previous_price",
      "old_price",
      "preco_de",
    ]),
    currentPrice: firstNumber(record, [
      "preco_atual",
      "current_price",
      "new_price",
      "preco",
      "price",
    ]),
    occurredAt,
  };
}

export function presentAlertList(payload: unknown): AlertListPage {
  const source = extractArray(payload);

  const items = source
    .filter(isRecord)
    .map((record, index) => normalizeAlert(record, index));

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

export function formatAlertTimestamp(
  value: string | null,
): string {
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
