import {
  GamificationAchievement,
  GamificationSnapshot,
} from "@/src/gamification/gamification-types";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function asRecord(value: unknown): UnknownRecord {
  return isRecord(value) ? value : {};
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();

  return normalized ? normalized : null;
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

function asNullableNumber(
  value: unknown,
): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  const parsed = asNumber(
    value,
    Number.NaN,
  );

  return Number.isFinite(parsed)
    ? parsed
    : null;
}

function asBoolean(value: unknown): boolean {
  return value === true;
}

function asStringList(
  value: unknown,
): readonly string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map(asString)
    .filter(
      (item): item is string =>
        item !== null,
    );
}

function unwrap(
  payload: unknown,
): UnknownRecord {
  const root = asRecord(payload);

  if (isRecord(root.dados)) {
    return root.dados;
  }

  return root;
}

function presentAchievement(
  value: unknown,
): GamificationAchievement | null {
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
    name:
      asString(value.nome)
      ?? code.replaceAll("_", " "),
    description:
      asString(value.descricao)
      ?? "",
    badge: asString(value.badge),
    unlocked: asBoolean(
      value.desbloqueada
    ),
    currentProgress: asNumber(
      value.progresso_atual
    ),
    targetProgress: asNumber(
      value.progresso_alvo
    ),
  };
}

export function presentGamification(
  payload: unknown,
): GamificationSnapshot {
  const root = unwrap(payload);

  const profile = asRecord(
    root.perfil
  );

  const progress = asRecord(
    root.progresso_nivel
  );

  const achievementsRaw = Array.isArray(
    root.conquistas
  )
    ? root.conquistas
    : [];

  const achievements = achievementsRaw
    .map(presentAchievement)
    .filter(
      (
        item,
      ): item is GamificationAchievement =>
        item !== null,
    );

  return {
    profile: {
      xpTotal: asNumber(
        profile.xp_total
      ),
      level: asNumber(
        profile.nivel,
        1,
      ),
      reputationTotal: asNumber(
        profile.reputacao_total
      ),
      eventsTotal: asNumber(
        profile.eventos_total
      ),
      updatedAt: asString(
        profile.atualizado_em
      ),
    },

    levelProgress: {
      currentLevel: asNumber(
        progress.nivel_atual,
        1,
      ),
      xpTotal: asNumber(
        progress.xp_total
      ),
      levelStartXp: asNumber(
        progress.xp_inicio_nivel
      ),
      nextLevelXp: asNullableNumber(
        progress.xp_proximo_nivel
      ),
      xpInLevel: asNumber(
        progress.xp_no_nivel
      ),
      xpNeededInLevel:
        asNullableNumber(
          progress.xp_necessario_no_nivel
        ),
      xpRemaining: asNumber(
        progress.xp_faltante
      ),
      percent: asNumber(
        progress.percentual
      ),
      maxLevel: asBoolean(
        progress.nivel_maximo
      ),
    },

    achievements,
    unlockedBadges: asStringList(
      root.badges_desbloqueadas
    ),
    rulesetVersion:
      asString(
        root.ruleset_version
      )
      ?? "unknown",
  };
}
