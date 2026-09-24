import { Ionicons } from "@expo/vector-icons";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import {
  useCommunityTrustEvidenceHistory,
  useCommunityTrustProfile,
} from "@/src/trust/trust-queries";
import {
  CommunityTrustClassification,
  CommunityTrustEvidenceItem,
} from "@/src/trust/trust-types";
import { appTheme } from "@/src/ui";

function formatTimestamp(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function classificationLabel(
  value: CommunityTrustClassification,
): string {
  if (value === "positive") {
    return "Positiva";
  }

  if (value === "negative") {
    return "Negativa";
  }

  return "Neutra";
}

function classificationColor(
  value: CommunityTrustClassification,
): string {
  if (value === "positive") {
    return appTheme.colors.success;
  }

  if (value === "negative") {
    return appTheme.colors.danger;
  }

  return appTheme.colors.textMuted;
}

function EvidenceRow({
  item,
}: Readonly<{
  item: CommunityTrustEvidenceItem;
}>) {
  return (
    <View style={styles.evidenceRow}>
      <View style={styles.evidenceIcon}>
        <Ionicons
          name="shield-checkmark-outline"
          size={17}
          color={classificationColor(
            item.classification,
          )}
        />
      </View>

      <View style={styles.evidenceCopy}>
        <Text style={styles.evidenceType}>
          {item.type}
        </Text>

        <Text style={styles.evidenceTimestamp}>
          {formatTimestamp(item.occurredAt)}
        </Text>
      </View>

      <Text
        style={[
          styles.classification,
          {
            color: classificationColor(
              item.classification,
            ),
          },
        ]}
      >
        {classificationLabel(
          item.classification,
        )}
      </Text>
    </View>
  );
}

export function TrustPanel() {
  const profile =
    useCommunityTrustProfile();

  const history =
    useCommunityTrustEvidenceHistory(
      20,
      0,
    );

  const refreshing =
    profile.isFetching ||
    history.isFetching;

  const refresh = async (): Promise<void> => {
    await Promise.all([
      profile.refetch(),
      history.refetch(),
    ]);
  };

  if (
    profile.isPending ||
    history.isPending
  ) {
    return (
      <View style={styles.section}>
        <View style={styles.sectionHeading}>
          <View style={styles.sectionTitleGroup}>
            <View style={styles.sectionIcon}>
              <Ionicons
                name="shield-checkmark-outline"
                size={18}
                color={appTheme.colors.accent}
              />
            </View>

            <View>
              <Text style={styles.eyebrow}>
                CONFIANCA
              </Text>
              <Text style={styles.title}>
                Reputacao comunitaria
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.stateCard}>
          <ActivityIndicator
            color={appTheme.colors.accent}
          />
          <Text style={styles.stateText}>
            Carregando sinais de confianca...
          </Text>
        </View>
      </View>
    );
  }

  const profileData =
    profile.data;

  const historyData =
    history.data;

  if (
    profile.isError ||
    history.isError ||
    !profileData ||
    !historyData
  ) {
    return (
      <View style={styles.section}>
        <View style={styles.sectionHeading}>
          <View style={styles.sectionTitleGroup}>
            <View style={styles.sectionIcon}>
              <Ionicons
                name="shield-checkmark-outline"
                size={18}
                color={appTheme.colors.accent}
              />
            </View>

            <View>
              <Text style={styles.eyebrow}>
                CONFIANCA
              </Text>
              <Text style={styles.title}>
                Reputacao comunitaria
              </Text>
            </View>
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Tentar carregar reputacao novamente"
            style={styles.refreshButton}
            onPress={() => {
              void refresh();
            }}
          >
            <Ionicons
              name="refresh"
              size={17}
              color={appTheme.colors.accent}
            />
          </Pressable>
        </View>

        <View style={styles.errorCard}>
          <Ionicons
            name="alert-circle-outline"
            size={20}
            color={appTheme.colors.danger}
          />

          <Text style={styles.errorText}>
            Nao foi possivel carregar sua reputacao agora.
          </Text>

          <Pressable
            accessibilityRole="button"
            style={styles.retryButton}
            onPress={() => {
              void refresh();
            }}
          >
            <Text style={styles.retryText}>
              Tentar novamente
            </Text>
          </Pressable>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.section}>
      <View style={styles.sectionHeading}>
        <View style={styles.sectionTitleGroup}>
          <View style={styles.sectionIcon}>
            <Ionicons
              name="shield-checkmark-outline"
              size={18}
              color={appTheme.colors.accent}
            />
          </View>

          <View style={styles.headingCopy}>
            <Text style={styles.eyebrow}>
              CONFIANCA
            </Text>

            <Text style={styles.title}>
              Reputacao comunitaria
            </Text>
          </View>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Atualizar reputacao comunitaria"
          disabled={refreshing}
          style={styles.refreshButton}
          onPress={() => {
            void refresh();
          }}
        >
          {refreshing ? (
            <ActivityIndicator
              size="small"
              color={appTheme.colors.accent}
            />
          ) : (
            <Ionicons
              name="refresh"
              size={17}
              color={appTheme.colors.accent}
            />
          )}
        </Pressable>
      </View>

      <Text style={styles.explanation}>
        Sua reputacao e formada por evidencias registradas
        pelo sistema. Nao usamos uma nota numerica.
      </Text>

      <View style={styles.summaryGrid}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryValue}>
            {profileData.evidenceTotal}
          </Text>
          <Text style={styles.summaryLabel}>
            Evidencias
          </Text>
        </View>

        <View style={styles.summaryCard}>
          <Text
            style={[
              styles.summaryValue,
              styles.positiveValue,
            ]}
          >
            {profileData.positiveTotal}
          </Text>
          <Text style={styles.summaryLabel}>
            Positivas
          </Text>
        </View>

        <View style={styles.summaryCard}>
          <Text
            style={[
              styles.summaryValue,
              styles.neutralValue,
            ]}
          >
            {profileData.neutralTotal}
          </Text>
          <Text style={styles.summaryLabel}>
            Neutras
          </Text>
        </View>

        <View style={styles.summaryCard}>
          <Text
            style={[
              styles.summaryValue,
              styles.negativeValue,
            ]}
          >
            {profileData.negativeTotal}
          </Text>
          <Text style={styles.summaryLabel}>
            Negativas
          </Text>
        </View>
      </View>

      <View style={styles.modelNotice}>
        <Ionicons
          name="information-circle-outline"
          size={17}
          color={appTheme.colors.textMuted}
        />

        <Text style={styles.modelNoticeText}>
          Modelo publico v{profileData.modelVersion}
          {" \u2022 "}
          sem score numerico
        </Text>
      </View>

      <View style={styles.historyHeading}>
        <View>
          <Text style={styles.historyEyebrow}>
            HISTORICO
          </Text>
          <Text style={styles.historyTitle}>
            Evidencias recentes
          </Text>
        </View>

        <Text style={styles.historyCount}>
          {historyData.count}
        </Text>
      </View>

      {historyData.items.length === 0 ? (
        <View style={styles.emptyCard}>
          <Ionicons
            name="shield-outline"
            size={22}
            color={appTheme.colors.textMuted}
          />

          <Text style={styles.emptyTitle}>
            Nenhuma evidencia ainda
          </Text>

          <Text style={styles.emptyDescription}>
            Quando houver sinais de confianca registrados,
            eles aparecerao aqui.
          </Text>
        </View>
      ) : (
        <View style={styles.historyList}>
          {historyData.items.map(
            (item, index) => (
              <EvidenceRow
                key={`${item.type}-${item.occurredAt}-${index}`}
                item={item}
              />
            ),
          )}
        </View>
      )}

      {profileData.updatedAt ? (
        <Text style={styles.updatedAt}>
          Atualizado em{" "}
          {formatTimestamp(
            profileData.updatedAt,
          )}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.xl,
    backgroundColor: appTheme.colors.surface,
    padding: appTheme.spacing.lg,
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
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accentSoft,
  },
  headingCopy: {
    flex: 1,
  },
  eyebrow: {
    color: appTheme.colors.accent,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1,
  },
  title: {
    color: appTheme.colors.text,
    fontSize: 18,
    fontWeight: "900",
  },
  refreshButton: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
  },
  explanation: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
  },
  summaryGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  summaryCard: {
    minWidth: "47%",
    flexGrow: 1,
    gap: 2,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  summaryValue: {
    color: appTheme.colors.text,
    fontSize: 21,
    fontWeight: "900",
  },
  positiveValue: {
    color: appTheme.colors.success,
  },
  neutralValue: {
    color: appTheme.colors.textMuted,
  },
  negativeValue: {
    color: appTheme.colors.danger,
  },
  summaryLabel: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "800",
  },
  modelNotice: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  modelNoticeText: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "700",
  },
  historyHeading: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: 12,
  },
  historyEyebrow: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.8,
  },
  historyTitle: {
    color: appTheme.colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  historyCount: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
    fontWeight: "800",
  },
  historyList: {
    overflow: "hidden",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
  },
  evidenceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: appTheme.colors.border,
    backgroundColor: appTheme.colors.background,
    paddingHorizontal: 12,
    paddingVertical: 11,
  },
  evidenceIcon: {
    width: 30,
    height: 30,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surface,
  },
  evidenceCopy: {
    flex: 1,
    gap: 2,
  },
  evidenceType: {
    color: appTheme.colors.text,
    fontSize: 11,
    fontWeight: "800",
  },
  evidenceTimestamp: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
  },
  classification: {
    fontSize: 9,
    fontWeight: "900",
  },
  stateCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    minHeight: 72,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.background,
    padding: 14,
  },
  stateText: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 11,
    fontWeight: "700",
  },
  errorCard: {
    gap: 10,
    alignItems: "flex-start",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.dangerBorder,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.dangerSurface,
    padding: 14,
  },
  errorText: {
    color: appTheme.colors.text,
    fontSize: 11,
    lineHeight: 17,
  },
  retryButton: {
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  retryText: {
    color: appTheme.colors.accent,
    fontSize: 10,
    fontWeight: "900",
  },
  emptyCard: {
    alignItems: "center",
    gap: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.background,
    padding: 18,
  },
  emptyTitle: {
    color: appTheme.colors.text,
    fontSize: 12,
    fontWeight: "900",
  },
  emptyDescription: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 15,
    textAlign: "center",
  },
  updatedAt: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    textAlign: "right",
  },
});
