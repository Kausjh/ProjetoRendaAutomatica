import {
  CommunityReportCreateResult,
  CommunityReportDetail,
  CommunityReportPage,
  CommunityReportReason,
  CommunityReportStatus,
  CommunityReportSummary,
} from "@/src/reporting/reporting-types";

type UnknownRecord = Record<string, unknown>;

const VALID_REASONS = new Set<CommunityReportReason>([
  "spam",
  "fraud",
  "malicious_link",
  "abuse",
  "off_topic",
  "duplicate",
  "other",
]);

const VALID_STATUSES = new Set<CommunityReportStatus>([
  "received",
  "under_review",
  "resolved",
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

function nonNegativeInteger(
  value: unknown,
  fallback: number,
): number {
  return typeof value === "number" &&
    Number.isFinite(value) &&
    value >= 0
    ? Math.trunc(value)
    : fallback;
}

function normalizeSummary(
  value: unknown,
): CommunityReportSummary | null {
  if (!isRecord(value)) {
    return null;
  }

  const id = stringValue(value, "id");
  const targetType = stringValue(value, "target_type");
  const targetId = stringValue(value, "target_id");
  const reasonRaw = stringValue(value, "motivo");
  const statusRaw = stringValue(value, "estado");
  const createdAt = stringValue(value, "criado_em");
  const updatedAt = stringValue(value, "atualizado_em");

  if (
    !id ||
    targetType !== "community_discovery" ||
    !targetId ||
    !reasonRaw ||
    !VALID_REASONS.has(reasonRaw as CommunityReportReason) ||
    !statusRaw ||
    !VALID_STATUSES.has(statusRaw as CommunityReportStatus) ||
    !createdAt ||
    !updatedAt
  ) {
    return null;
  }

  return {
    id,
    targetType: "community_discovery",
    targetId,
    reason: reasonRaw as CommunityReportReason,
    status: statusRaw as CommunityReportStatus,
    createdAt,
    updatedAt,
  };
}

function normalizeDetail(
  value: unknown,
): CommunityReportDetail | null {
  if (!isRecord(value)) {
    return null;
  }

  const summary = normalizeSummary(value);

  if (!summary) {
    return null;
  }

  return {
    ...summary,
    details: nullableString(value, "detalhes"),
  };
}

export function presentCommunityReports(
  payload: unknown,
): CommunityReportPage {
  if (!isRecord(payload)) {
    return {
      items: [],
      limit: 20,
      offset: 0,
      count: 0,
    };
  }

  const rawItems = Array.isArray(payload.itens)
    ? payload.itens
    : [];

  const items = rawItems
    .map(normalizeSummary)
    .filter(
      (item): item is CommunityReportSummary =>
        item !== null,
    );

  return {
    items,
    limit: nonNegativeInteger(payload.limite, 20),
    offset: nonNegativeInteger(payload.offset, 0),
    count: nonNegativeInteger(
      payload.quantidade,
      items.length,
    ),
  };
}

export function presentCommunityReportDetail(
  payload: unknown,
): CommunityReportDetail {
  if (!isRecord(payload)) {
    throw new Error("A API retornou uma denúncia inválida.");
  }

  const report = normalizeDetail(payload.denuncia);

  if (!report) {
    throw new Error("A API retornou uma denúncia inválida.");
  }

  return report;
}

export function presentCommunityReportCreate(
  payload: unknown,
): CommunityReportCreateResult {
  if (!isRecord(payload)) {
    throw new Error("A API retornou uma denúncia inválida.");
  }

  const report = normalizeDetail(payload.denuncia);

  if (!report) {
    throw new Error("A API retornou uma denúncia inválida.");
  }

  if (
    typeof payload.criada !== "boolean" ||
    typeof payload.idempotent_replay !== "boolean"
  ) {
    throw new Error(
      "A API retornou um resultado de denúncia inválido.",
    );
  }

  return {
    report,
    created: payload.criada,
    idempotentReplay: payload.idempotent_replay,
  };
}
