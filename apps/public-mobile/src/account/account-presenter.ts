import {
  AccountPreferences,
} from "@/src/account/account-types";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
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

function firstStringArray(
  record: UnknownRecord,
  keys: readonly string[],
): readonly string[] {
  for (const key of keys) {
    const value = record[key];

    if (!Array.isArray(value)) {
      continue;
    }

    const normalized = value
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter(Boolean);

    return [...new Set(normalized)];
  }

  return [];
}

function unwrapPreferences(payload: unknown): UnknownRecord {
  if (!isRecord(payload)) {
    return {};
  }

  for (const key of [
    "preferencias",
    "preferences",
    "dados",
  ]) {
    const nested = payload[key];

    if (isRecord(nested)) {
      return nested;
    }
  }

  return payload;
}

export function presentAccountPreferences(
  payload: unknown,
): AccountPreferences {
  const record = unwrapPreferences(payload);

  return {
    priceNotificationsEnabled: firstBoolean(
      record,
      [
        "notificacoes_preco_habilitadas",
        "price_notifications_enabled",
        "priceNotificationsEnabled",
      ],
      true,
    ),
    preferredMarketplaces: firstStringArray(
      record,
      [
        "marketplaces_preferidos",
        "preferred_marketplaces",
        "preferredMarketplaces",
      ],
    ),
  };
}

export function normalizeMarketplaceInput(
  value: string,
): readonly string[] {
  const normalized = value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  return [...new Set(normalized)];
}
