import { Ionicons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import {
  useMissions,
} from "@/src/missions/mission-queries";
import {
  MissionItem,
} from "@/src/missions/mission-types";
import { appTheme } from "@/src/ui";

function rewardLabel(
  mission: MissionItem,
): string {
  const amount =
    `${mission.reward.amount} ${mission.reward.type.toUpperCase()}`;

  if (mission.reward.status === "granted") {
    return `${amount} recebido`;
  }

  if (mission.reward.status === "pending") {
    return `${amount} pendente`;
  }

  return `${amount} bloqueado`;
}

function MissionRow({
  mission,
}: Readonly<{
  mission: MissionItem;
}>) {
  const progressWidth =
    `${Math.max(
      0,
      Math.min(100, mission.percent),
    )}%` as `${number}%`;

  const rewardGranted =
    mission.reward.status === "granted";

  return (
    <View style={styles.missionCard}>
      <View style={styles.missionHeading}>
        <View
          style={[
            styles.missionIcon,
            mission.completed
              ? styles.missionIconCompleted
              : null,
          ]}
        >
          <Ionicons
            name={
              mission.completed
                ? "checkmark-circle"
                : "flag-outline"
            }
            size={19}
            color={
              mission.completed
                ? appTheme.colors.success
                : appTheme.colors.accent
            }
          />
        </View>

        <View style={styles.missionCopy}>
          <Text style={styles.missionTitle}>
            {mission.title}
          </Text>

          {mission.description ? (
            <Text style={styles.missionDescription}>
              {mission.description}
            </Text>
          ) : null}
        </View>
      </View>

      <View style={styles.progressBlock}>
        <View style={styles.progressTrack}>
          <View
            style={[
              styles.progressFill,
              { width: progressWidth },
              mission.completed
                ? styles.progressFillCompleted
                : null,
            ]}
          />
        </View>

        <View style={styles.progressMeta}>
          <Text style={styles.progressText}>
            {mission.currentProgress}/
            {mission.targetProgress}
          </Text>

          <Text style={styles.percentText}>
            {mission.percent.toFixed(0)}%
          </Text>
        </View>
      </View>

      <View style={styles.rewardRow}>
        <Ionicons
          name={
            rewardGranted
              ? "gift"
              : "gift-outline"
          }
          size={15}
          color={
            rewardGranted
              ? appTheme.colors.success
              : appTheme.colors.textMuted
          }
        />

        <Text
          style={[
            styles.rewardText,
            rewardGranted
              ? styles.rewardTextGranted
              : null,
          ]}
        >
          {rewardLabel(mission)}
        </Text>
      </View>
    </View>
  );
}

export function MissionsPanel({
  enabled,
}: Readonly<{
  enabled: boolean;
}>) {
  const missions = useMissions(enabled);

  if (!enabled) {
    return null;
  }

  const data = missions.data;

  return (
    <View style={styles.section}>
      <View style={styles.sectionHeading}>
        <View style={styles.sectionTitleGroup}>
          <View style={styles.sectionIcon}>
            <Ionicons
              name="flag-outline"
              size={18}
              color={appTheme.colors.accent}
            />
          </View>

          <View>
            <Text style={styles.eyebrow}>
              {"MISS\u00d5ES"}
            </Text>

            <Text style={styles.title}>
              {"Miss\u00f5es da comunidade"}
            </Text>
          </View>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            "Atualizar miss\u00f5es"
          }
          disabled={missions.isFetching}
          style={styles.refreshButton}
          onPress={() => {
            void missions.refetch();
          }}
        >
          {missions.isFetching ? (
            <ActivityIndicator
              size="small"
              color={appTheme.colors.accent}
            />
          ) : (
            <Ionicons
              name="refresh"
              size={17}
              color={appTheme.colors.text}
            />
          )}
        </Pressable>
      </View>

      {missions.isPending ? (
        <View style={styles.stateCard}>
          <ActivityIndicator
            color={appTheme.colors.accent}
          />

          <Text style={styles.stateText}>
            {"Carregando suas miss\u00f5es..."}
          </Text>
        </View>
      ) : null}

      {missions.isError ? (
        <View style={styles.errorCard}>
          <Ionicons
            name="alert-circle-outline"
            size={20}
            color={appTheme.colors.danger}
          />

          <View style={styles.errorCopy}>
            <Text style={styles.errorText}>
              {missions.error instanceof Error
                ? missions.error.message
                : "N\u00e3o foi poss\u00edvel carregar suas miss\u00f5es."}
            </Text>

            <Pressable
              accessibilityRole="button"
              style={styles.retryButton}
              onPress={() => {
                void missions.refetch();
              }}
            >
              <Text style={styles.retryButtonText}>
                Tentar novamente
              </Text>
            </Pressable>
          </View>
        </View>
      ) : null}

      {data ? (
        <View style={styles.card}>
          <View style={styles.metricsRow}>
            <View style={styles.metric}>
              <Text style={styles.metricValue}>
                {data.summary.completed}
              </Text>
              <Text style={styles.metricLabel}>
                {"Conclu\u00eddas"}
              </Text>
            </View>

            <View style={styles.metricDivider} />

            <View style={styles.metric}>
              <Text style={styles.metricValue}>
                {data.summary.inProgress}
              </Text>
              <Text style={styles.metricLabel}>
                Em andamento
              </Text>
            </View>

            <View style={styles.metricDivider} />

            <View style={styles.metric}>
              <Text style={styles.metricValue}>
                {data.summary.rewardsGranted}
              </Text>
              <Text style={styles.metricLabel}>
                Recebidas
              </Text>
            </View>
          </View>

          <View style={styles.divider} />

          <Text style={styles.serverHint}>
            {
              "O progresso e as recompensas s\u00e3o atualizados pelo Radar."
            }
          </Text>

          <View style={styles.missionList}>
            {data.missions.map((mission) => (
              <MissionRow
                key={mission.code}
                mission={mission}
              />
            ))}
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: 10,
  },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  sectionTitleGroup: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  sectionIcon: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.accentSoft,
  },
  eyebrow: {
    color: appTheme.colors.accent,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.3,
  },
  title: {
    marginTop: 2,
    color: appTheme.colors.text,
    fontSize: 19,
    fontWeight: "900",
  },
  refreshButton: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  stateCard: {
    minHeight: 86,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  stateText: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
  },
  errorCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.dangerSurface,
    padding: 14,
  },
  errorCopy: {
    flex: 1,
    gap: 10,
  },
  errorText: {
    color: appTheme.colors.danger,
    fontSize: 12,
    lineHeight: 18,
  },
  retryButton: {
    alignSelf: "flex-start",
    minHeight: 36,
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.dangerBorder,
    borderRadius: appTheme.radius.md,
    paddingHorizontal: 12,
  },
  retryButtonText: {
    color: appTheme.colors.danger,
    fontSize: 11,
    fontWeight: "900",
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
    gap: 14,
  },
  metricsRow: {
    flexDirection: "row",
    alignItems: "stretch",
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    paddingVertical: 10,
  },
  metric: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 2,
  },
  metricDivider: {
    width: StyleSheet.hairlineWidth,
    backgroundColor: appTheme.colors.borderStrong,
  },
  metricValue: {
    color: appTheme.colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  metricLabel: {
    color: appTheme.colors.textMuted,
    fontSize: 9,
    fontWeight: "700",
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: appTheme.colors.border,
  },
  serverHint: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 15,
  },
  missionList: {
    gap: 9,
  },
  missionCard: {
    gap: 11,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    padding: 11,
  },
  missionHeading: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  missionIcon: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.accentSoft,
  },
  missionIconCompleted: {
    backgroundColor: appTheme.colors.successSurface,
  },
  missionCopy: {
    flex: 1,
    gap: 3,
  },
  missionTitle: {
    color: appTheme.colors.text,
    fontSize: 12,
    fontWeight: "900",
  },
  missionDescription: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 15,
  },
  progressBlock: {
    gap: 6,
  },
  progressTrack: {
    height: 7,
    overflow: "hidden",
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.background,
  },
  progressFill: {
    height: "100%",
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.accentStrong,
  },
  progressFillCompleted: {
    backgroundColor: appTheme.colors.success,
  },
  progressMeta: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  progressText: {
    color: appTheme.colors.textMuted,
    fontSize: 9,
    fontWeight: "800",
  },
  percentText: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "800",
  },
  rewardRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  rewardText: {
    color: appTheme.colors.textMuted,
    fontSize: 9,
    fontWeight: "800",
  },
  rewardTextGranted: {
    color: appTheme.colors.success,
  },
});
