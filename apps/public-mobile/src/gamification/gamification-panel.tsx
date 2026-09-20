import { Ionicons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import {
  useGamification,
} from "@/src/gamification/gamification-queries";
import {
  GamificationAchievement,
} from "@/src/gamification/gamification-types";
import { appTheme } from "@/src/ui";

function AchievementRow({
  achievement,
}: Readonly<{
  achievement: GamificationAchievement;
}>) {
  return (
    <View style={styles.achievementRow}>
      <View
        style={[
          styles.achievementIcon,
          achievement.unlocked
            ? styles.achievementIconUnlocked
            : null,
        ]}
      >
        <Ionicons
          name={
            achievement.unlocked
              ? "checkmark-circle"
              : "lock-closed-outline"
          }
          size={18}
          color={
            achievement.unlocked
              ? appTheme.colors.success
              : appTheme.colors.textMuted
          }
        />
      </View>

      <View style={styles.achievementCopy}>
        <View style={styles.achievementHeading}>
          <Text style={styles.achievementName}>
            {achievement.name}
          </Text>

          {achievement.unlocked &&
          achievement.badge ? (
            <View style={styles.badgeChip}>
              <Text style={styles.badgeChipText}>
                BADGE
              </Text>
            </View>
          ) : null}
        </View>

        {achievement.description ? (
          <Text style={styles.achievementDescription}>
            {achievement.description}
          </Text>
        ) : null}
      </View>

      <Text style={styles.achievementProgress}>
        {achievement.currentProgress}/
        {achievement.targetProgress}
      </Text>
    </View>
  );
}

export function GamificationPanel({
  enabled,
}: Readonly<{
  enabled: boolean;
}>) {
  const gamification = useGamification(
    enabled
  );

  if (!enabled) {
    return null;
  }

  const data = gamification.data;

  const progressWidth = data
    ? `${Math.max(
        0,
        Math.min(
          100,
          data.levelProgress.percent
        )
      )}%` as `${number}%`
    : "0%";

  return (
    <View style={styles.section}>
      <View style={styles.sectionHeading}>
        <View style={styles.sectionTitleGroup}>
          <View style={styles.sectionIcon}>
            <Ionicons
              name="trophy-outline"
              size={18}
              color={appTheme.colors.accent}
            />
          </View>

          <View>
            <Text style={styles.eyebrow}>
              {"PROGRESS\u00c3O"}
            </Text>
            <Text style={styles.title}>
              {"N\u00edvel e conquistas"}
            </Text>
          </View>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={
            "Atualizar progress\u00e3o"
          }
          disabled={
            gamification.isFetching
          }
          style={styles.refreshButton}
          onPress={() => {
            void gamification.refetch();
          }}
        >
          {gamification.isFetching ? (
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

      {gamification.isPending ? (
        <View style={styles.stateCard}>
          <ActivityIndicator
            color={appTheme.colors.accent}
          />
          <Text style={styles.stateText}>
            {"Carregando sua progress\u00e3o..."}
          </Text>
        </View>
      ) : null}

      {gamification.isError ? (
        <View style={styles.errorCard}>
          <Ionicons
            name="alert-circle-outline"
            size={20}
            color={appTheme.colors.danger}
          />

          <View style={styles.errorCopy}>
            <Text style={styles.errorText}>
              {gamification.error instanceof Error
                ? gamification.error.message
                : "N\u00e3o foi poss\u00edvel carregar sua progress\u00e3o."}
            </Text>

            <Pressable
              accessibilityRole="button"
              style={styles.retryButton}
              onPress={() => {
                void gamification.refetch();
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
          <View style={styles.heroRow}>
            <View style={styles.levelBadge}>
              <Text style={styles.levelLabel}>
                {"N\u00cdVEL"}
              </Text>
              <Text style={styles.levelValue}>
                {data.profile.level}
              </Text>
            </View>

            <View style={styles.heroCopy}>
              <Text style={styles.heroTitle}>
                {data.profile.xpTotal} XP
              </Text>

              <Text style={styles.heroHint}>
                {data.levelProgress.maxLevel
                  ? "N\u00edvel m\u00e1ximo alcan\u00e7ado"
                  : `${data.levelProgress.xpRemaining} XP para o pr\u00f3ximo n\u00edvel`}
              </Text>
            </View>

            <View style={styles.percentBadge}>
              <Text style={styles.percentText}>
                {data.levelProgress.percent.toFixed(
                  0
                )}
                %
              </Text>
            </View>
          </View>

          <View style={styles.progressBlock}>
            <View style={styles.progressTrack}>
              <View
                style={[
                  styles.progressFill,
                  {
                    width: progressWidth,
                  },
                ]}
              />
            </View>

            <View style={styles.progressLabels}>
              <Text style={styles.progressText}>
                {data.levelProgress.xpInLevel}
                {data.levelProgress
                  .xpNeededInLevel !== null
                  ? ` / ${data.levelProgress.xpNeededInLevel} XP`
                  : " XP"}
              </Text>

              <Text style={styles.progressText}>
                {data.levelProgress.maxLevel
                  ? "MAX"
                  : `N\u00edvel ${data.levelProgress.currentLevel + 1}`}
              </Text>
            </View>
          </View>

          <View style={styles.metricsRow}>
            <View style={styles.metric}>
              <Text style={styles.metricValue}>
                {data.profile.reputationTotal}
              </Text>
              <Text style={styles.metricLabel}>
                {"Reputa\u00e7\u00e3o"}
              </Text>
            </View>

            <View style={styles.metricDivider} />

            <View style={styles.metric}>
              <Text style={styles.metricValue}>
                {data.unlockedBadges.length}
              </Text>
              <Text style={styles.metricLabel}>
                Badges
              </Text>
            </View>

            <View style={styles.metricDivider} />

            <View style={styles.metric}>
              <Text style={styles.metricValue}>
                {
                  data.achievements.filter(
                    (item) => item.unlocked
                  ).length
                }
                /{data.achievements.length}
              </Text>
              <Text style={styles.metricLabel}>
                Conquistas
              </Text>
            </View>
          </View>

          <View style={styles.divider} />

          <View style={styles.achievementsHeader}>
            <Text style={styles.achievementsTitle}>
              Conquistas
            </Text>
            <Text style={styles.achievementsHint}>
              {
                "Seu progresso \u00e9 atualizado pelo Radar."
              }
            </Text>
          </View>

          <View style={styles.achievementList}>
            {data.achievements.map(
              (achievement) => (
                <AchievementRow
                  key={achievement.code}
                  achievement={achievement}
                />
              )
            )}
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
  heroRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  levelBadge: {
    width: 62,
    height: 62,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 19,
    backgroundColor: appTheme.colors.accentSoft,
  },
  levelLabel: {
    color: appTheme.colors.accent,
    fontSize: 8,
    fontWeight: "900",
    letterSpacing: 1,
  },
  levelValue: {
    marginTop: -1,
    color: appTheme.colors.text,
    fontSize: 27,
    fontWeight: "900",
  },
  heroCopy: {
    flex: 1,
    gap: 3,
  },
  heroTitle: {
    color: appTheme.colors.text,
    fontSize: 20,
    fontWeight: "900",
  },
  heroHint: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
    lineHeight: 16,
  },
  percentBadge: {
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surfaceElevated,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  percentText: {
    color: appTheme.colors.accent,
    fontSize: 11,
    fontWeight: "900",
  },
  progressBlock: {
    gap: 7,
  },
  progressTrack: {
    height: 8,
    overflow: "hidden",
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  progressFill: {
    height: "100%",
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.accentStrong,
  },
  progressLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  progressText: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "700",
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
  achievementsHeader: {
    gap: 3,
  },
  achievementsTitle: {
    color: appTheme.colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  achievementsHint: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
  },
  achievementList: {
    gap: 8,
  },
  achievementRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    padding: 10,
  },
  achievementIcon: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 11,
    backgroundColor: appTheme.colors.background,
  },
  achievementIconUnlocked: {
    backgroundColor: appTheme.colors.successSurface,
  },
  achievementCopy: {
    flex: 1,
    gap: 2,
  },
  achievementHeading: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 6,
  },
  achievementName: {
    color: appTheme.colors.text,
    fontSize: 11,
    fontWeight: "900",
  },
  achievementDescription: {
    color: appTheme.colors.textMuted,
    fontSize: 9,
    lineHeight: 14,
  },
  badgeChip: {
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.accentSoft,
    paddingHorizontal: 6,
    paddingVertical: 3,
  },
  badgeChipText: {
    color: appTheme.colors.accent,
    fontSize: 7,
    fontWeight: "900",
    letterSpacing: 0.6,
  },
  achievementProgress: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "800",
  },
});
