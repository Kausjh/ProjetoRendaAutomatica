import {
  CommunityDiscoveryCollection,
  CommunityDiscoveryCreateResult,
  CommunityDiscoveryItem,
  CommunityDiscoveryStatus,
} from "@/src/discoveries/discovery-types";

type UnknownRecord = Record<string, unknown>;

const VALID_STATUSES = new Set<CommunityDiscoveryStatus>([
  "received",
  "processing",
  "retry",
  "approved",
  "rejected",
]);

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(
  record: UnknownRecord,
  key: string,
): string | null {
  const value = record[key];
  return typeof value === "string" && value.trim()
    ? value.trim()
    : null;
}

function nullableString(
  record: UnknownRecord,
  key: string,
): string | null {
  const value = record[key];
  if (value === null || value === undefined) {
    return null;
  }
  return typeof value === "string" && value.trim()
    ? value.trim()
    : null;
}

function normalizeItem(value: unknown): CommunityDiscoveryItem | null {
  if (!isRecord(value)) {
    return null;
  }

  const id = stringValue(value, "id");
  const url = stringValue(value, "url");
  const statusRaw = stringValue(value, "status");
  const createdAt = stringValue(value, "criado_em");
  const updatedAt = stringValue(value, "atualizado_em");

  if (
    !id ||
    !url ||
    !statusRaw ||
    !VALID_STATUSES.has(statusRaw as CommunityDiscoveryStatus) ||
    !createdAt ||
    !updatedAt
  ) {
    return null;
  }

  return {
    id,
    url,
    marketplace: nullableString(value, "marketplace"),
    status: statusRaw as CommunityDiscoveryStatus,
    statusReason: nullableString(value, "motivo_status"),
    canonicalKey: nullableString(value, "canonical_key"),
    createdAt,
    updatedAt,
  };
}

export function presentCommunityDiscoveries(
  payload: unknown,
): CommunityDiscoveryCollection {
  if (!isRecord(payload)) {
    return { total: 0, items: [] };
  }

  const rawItems = Array.isArray(payload.itens)
    ? payload.itens
    : [];
  const items = rawItems
    .map(normalizeItem)
    .filter((item): item is CommunityDiscoveryItem => item !== null);

  const total =
    typeof payload.total === "number" && Number.isFinite(payload.total)
      ? Math.max(0, Math.trunc(payload.total))
      : items.length;

  return { total, items };
}

export function presentCommunityDiscoveryCreate(
  payload: unknown,
): CommunityDiscoveryCreateResult {
  if (!isRecord(payload)) {
    throw new Error("A API retornou uma descoberta inválida.");
  }

  const item = normalizeItem(payload.item);
  if (!item) {
    throw new Error("A API retornou uma descoberta inválida.");
  }

  return {
    item,
    duplicate: payload.duplicada === true,
  };
}
