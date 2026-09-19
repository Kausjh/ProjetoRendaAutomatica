import {
  PersonalizedFeedItem,
  PersonalizedFeedPage,
} from "@/src/feed/feed-types";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();
  return normalized ? normalized : null;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function asBoolean(value: unknown): boolean {
  return value === true;
}

function asStringList(value: unknown): readonly string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map(asString)
    .filter((item): item is string => item !== null);
}

function presentItem(value: unknown): PersonalizedFeedItem | null {
  if (!isRecord(value)) {
    return null;
  }

  const canonicalKey = asString(value.canonical_key);

  if (!canonicalKey) {
    return null;
  }

  return {
    canonicalKey,
    title: asString(value.nome_canonico) ?? canonicalKey,
    category: asString(value.categoria),
    brand: asString(value.marca),
    model: asString(value.modelo),
    relevanceScore: asNumber(value.score_relevancia) ?? 0,
    reasons: asStringList(value.motivos),
    inWatchlist: asBoolean(value.em_watchlist),
    targetPrice: asNumber(value.preco_alvo),
    currentPrice: asNumber(value.preco_atual),
    marketplace: asString(value.marketplace),
    identifier: asString(value.identificador),
    productUrl: asString(value.link),
    updatedAt: asString(value.atualizado_em),
  };
}

export function presentPersonalizedFeed(
  payload: unknown,
): PersonalizedFeedPage {
  const root = isRecord(payload) ? payload : {};
  const rawItems = Array.isArray(root.itens) ? root.itens : [];
  const items = rawItems
    .map(presentItem)
    .filter((item): item is PersonalizedFeedItem => item !== null);

  return {
    total: asNumber(root.total) ?? items.length,
    limit: asNumber(root.limite) ?? 20,
    offset: asNumber(root.offset) ?? 0,
    items,
  };
}

export function personalizedFeedReasonLabel(reason: string): string {
  switch (reason) {
    case "watchlist":
      return "Na sua watchlist";
    case "preco_alvo_atingido":
      return "Preco-alvo atingido";
    case "marketplace_preferido":
      return "Marketplace preferido";
    default:
      return reason.replaceAll("_", " ");
  }
}
