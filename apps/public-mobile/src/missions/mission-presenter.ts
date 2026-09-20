import {
  MissionItem,
  MissionReward,
  MissionRewardStatus,
  MissionsSnapshot,
} from "@/src/missions/mission-types";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function asRecord(value: unknown): UnknownRecord {
  return isRecord(value) ? value : {};
}

function asString(
  value: unknown,
  fallback = "",
): string {
  return typeof value === "string"
    ? value.trim() || fallback
    : fallback;
}

function asNullableString(
  value: unknown,
): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();

  return normalized || null;
}

function asNumber(
  value: unknown,
  fallback = 0,
): number {
  if (
    typeof value === "number" &&
    Number.isFinite(value)
  ) {
    return value;
  }

  if (
    typeof value === "string" &&
    value.trim()
  ) {
    const parsed = Number(value);

    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function asBoolean(value: unknown): boolean {
  return value === true;
}

function unwrap(payload: unknown): UnknownRecord {
  const root = asRecord(payload);

  return isRecord(root.dados)
    ? root.dados
    : root;
}

function presentReward(
  value: unknown,
): MissionReward {
  const reward = asRecord(value);

  const rawStatus = asString(
    reward.status,
    "locked",
  );

  const status: MissionRewardStatus =
    rawStatus === "pending" ||
    rawStatus === "granted"
      ? rawStatus
      : "locked";

  return {
    type: asString(
      reward.tipo,
      "xp",
    ),
    amount: asNumber(
      reward.quantidade,
    ),
    status,
    grantedAt: asNullableString(
      reward.concedida_em,
    ),
  };
}

function presentMission(
  value: unknown,
): MissionItem | null {
  if (!isRecord(value)) {
    return null;
  }

  const code = asString(
    value.codigo,
  );

  if (!code) {
    return null;
  }

  return {
    code,
    title: asString(
      value.titulo,
      code.replaceAll("_", " "),
    ),
    description: asString(
      value.descricao,
    ),
    currentProgress: asNumber(
      value.progresso_atual,
    ),
    targetProgress: asNumber(
      value.progresso_alvo,
    ),
    percent: asNumber(
      value.percentual,
    ),
    completed: asBoolean(
      value.concluida,
    ),
    completedAt: asNullableString(
      value.concluida_em,
    ),
    updatedAt: asNullableString(
      value.atualizado_em,
    ),
    reward: presentReward(
      value.recompensa,
    ),
  };
}

export function presentMissions(
  payload: unknown,
): MissionsSnapshot {
  const root = unwrap(payload);
  const summary = asRecord(
    root.resumo,
  );

  const rawMissions = Array.isArray(
    root.missoes,
  )
    ? root.missoes
    : [];

  const missions = rawMissions
    .map(presentMission)
    .filter(
      (item): item is MissionItem =>
        item !== null,
    );

  return {
    rulesetVersion: asString(
      root.ruleset_version,
      "unknown",
    ),
    instanceKey: asString(
      root.instancia_chave,
      "unknown",
    ),
    summary: {
      total: asNumber(
        summary.total,
      ),
      completed: asNumber(
        summary.concluidas,
      ),
      inProgress: asNumber(
        summary.em_andamento,
      ),
      notStarted: asNumber(
        summary.nao_iniciadas,
      ),
      rewardsPending: asNumber(
        summary.rewards_pending,
      ),
      rewardsGranted: asNumber(
        summary.rewards_granted,
      ),
    },
    missions,
  };
}
