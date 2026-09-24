import {
  CommunityTrustClassification,
  CommunityTrustEvidenceHistoryPage,
  CommunityTrustEvidenceItem,
  CommunityTrustProfile,
} from "@/src/trust/trust-types";

type UnknownRecord = Readonly<Record<string, unknown>>;

export class CommunityTrustPayloadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CommunityTrustPayloadError";
  }
}

function asRecord(value: unknown, label: string): UnknownRecord {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new CommunityTrustPayloadError(`${label} invalido.`);
  }

  return value as UnknownRecord;
}

function asNonNegativeInteger(value: unknown, label: string): number {
  if (
    typeof value !== "number" ||
    !Number.isInteger(value) ||
    value < 0
  ) {
    throw new CommunityTrustPayloadError(`${label} invalido.`);
  }

  return value;
}

function asPositiveInteger(value: unknown, label: string): number {
  const parsed = asNonNegativeInteger(value, label);

  if (parsed < 1) {
    throw new CommunityTrustPayloadError(`${label} invalido.`);
  }

  return parsed;
}

function asString(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new CommunityTrustPayloadError(`${label} invalido.`);
  }

  return value;
}

function asNullableString(
  value: unknown,
  label: string,
): string | null {
  if (value === null) {
    return null;
  }

  return asString(value, label);
}

function asFalse(value: unknown, label: string): false {
  if (value !== false) {
    throw new CommunityTrustPayloadError(`${label} invalido.`);
  }

  return false;
}

function asClassification(
  value: unknown,
): CommunityTrustClassification {
  if (
    value !== "positive" &&
    value !== "negative" &&
    value !== "neutral"
  ) {
    throw new CommunityTrustPayloadError(
      "classificacao de Trust invalida.",
    );
  }

  return value;
}

export function presentCommunityTrustProfile(
  payload: unknown,
): CommunityTrustProfile {
  const root = asRecord(payload, "payload de Trust");
  const profile = asRecord(root.perfil, "perfil de Trust");
  const model = asRecord(root.modelo, "modelo de Trust");

  return {
    evidenceTotal: asNonNegativeInteger(
      profile.evidencias_total,
      "evidencias_total",
    ),
    positiveTotal: asNonNegativeInteger(
      profile.positivas_total,
      "positivas_total",
    ),
    negativeTotal: asNonNegativeInteger(
      profile.negativas_total,
      "negativas_total",
    ),
    neutralTotal: asNonNegativeInteger(
      profile.neutras_total,
      "neutras_total",
    ),
    updatedAt: asNullableString(
      profile.atualizado_em,
      "atualizado_em",
    ),
    modelVersion: asPositiveInteger(
      model.versao,
      "versao do modelo",
    ),
    numericScoreDefined: asFalse(
      model.score_numerico_definido,
      "score_numerico_definido",
    ),
  };
}

function presentEvidenceItem(
  value: unknown,
): CommunityTrustEvidenceItem {
  const item = asRecord(
    value,
    "evidencia de Trust",
  );

  return {
    type: asString(
      item.tipo_evidencia,
      "tipo_evidencia",
    ),
    classification: asClassification(
      item.classificacao,
    ),
    occurredAt: asString(
      item.ocorrido_em,
      "ocorrido_em",
    ),
  };
}

export function presentCommunityTrustEvidenceHistory(
  payload: unknown,
): CommunityTrustEvidenceHistoryPage {
  const root = asRecord(
    payload,
    "historico de Trust",
  );

  if (!Array.isArray(root.itens)) {
    throw new CommunityTrustPayloadError(
      "itens do historico de Trust invalidos.",
    );
  }

  const items = root.itens.map(
    presentEvidenceItem,
  );

  const limit = asPositiveInteger(
    root.limite,
    "limite",
  );

  if (limit > 100) {
    throw new CommunityTrustPayloadError(
      "limite de Trust invalido.",
    );
  }

  const offset = asNonNegativeInteger(
    root.offset,
    "offset",
  );

  const count = asNonNegativeInteger(
    root.quantidade,
    "quantidade",
  );

  if (count !== items.length) {
    throw new CommunityTrustPayloadError(
      "quantidade do historico de Trust divergente.",
    );
  }

  return {
    items,
    limit,
    offset,
    count,
  };
}
