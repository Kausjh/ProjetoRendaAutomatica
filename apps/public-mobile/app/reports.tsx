import { Ionicons } from "@expo/vector-icons";
import { Redirect, router } from "expo-router";
import { useMemo } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuthSession } from "@/src/auth";
import {
  type CommunityReportReason,
  type CommunityReportStatus,
  type CommunityReportSummary,
  useCommunityReports,
} from "@/src/reporting";
import { appTheme } from "@/src/ui";

const STATUS_LABELS: Readonly<
  Record<CommunityReportStatus, string>
> = {
  received: "Recebida",
  under_review: "Em análise",
  resolved: "Concluída",
};

const REASON_LABELS: Readonly<
  Record<CommunityReportReason, string>
> = {
  spam: "Spam",
  fraud: "Fraude",
  malicious_link: "Link malicioso",
  abuse: "Abuso",
  off_topic: "Fora do tema",
  duplicate: "Duplicado",
  other: "Outro problema",
};

function dateLabel(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return parsed.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusIcon(
  status: CommunityReportStatus,
): keyof typeof Ionicons.glyphMap {
  if (status === "resolved") {
    return "checkmark-circle-outline";
  }

  if (status === "under_review") {
    return "search-outline";
  }

  return "time-outline";
}

function statusColor(
  status: CommunityReportStatus,
): string {
  if (status === "resolved") {
    return appTheme.colors.success;
  }

  if (status === "under_review") {
    return appTheme.colors.warning;
  }

  return appTheme.colors.accent;
}

export default function ReportsScreen() {
  const { snapshot } = useAuthSession();

  const authenticated =
    snapshot.status === "authenticated";

  const reports = useCommunityReports(
    100,
    0,
    authenticated,
  );

  const items = useMemo(
    () => [...(reports.data?.items ?? [])],
    [reports.data],
  );

  if (snapshot.status === "restoring") {
    return (
      <View style={styles.loading}>
        <ActivityIndicator
          size="large"
          color={appTheme.colors.accent}
        />
      </View>
    );
  }

  if (!authenticated) {
    return <Redirect href="/" />;
  }

  return (
    <SafeAreaView
      style={styles.screen}
      edges={["top"]}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            tintColor={appTheme.colors.accent}
            colors={[appTheme.colors.accent]}
            refreshing={reports.isRefetching}
            onRefresh={() => {
              void reports.refetch();
            }}
          />
        }
      >
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <Ionicons
              name="chevron-back"
              size={22}
              color={appTheme.colors.text}
            />
          </Pressable>

          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>
              MODERAÇÃO DA COMUNIDADE
            </Text>

            <Text style={styles.title}>
              Minhas denúncias
            </Text>
          </View>
        </View>

        <View style={styles.hero}>
          <View style={styles.heroIcon}>
            <Ionicons
              name="flag-outline"
              size={24}
              color={appTheme.colors.danger}
            />
          </View>

          <Text style={styles.heroTitle}>
            Acompanhe o andamento
          </Text>

          <Text style={styles.body}>
            Aqui aparecem somente as denúncias vinculadas à sua conta.
            O status informa a etapa de revisão, não o resultado de uma
            decisão administrativa.
          </Text>
        </View>

        <View style={styles.sectionHeading}>
          <View style={styles.sectionHeadingCopy}>
            <Text style={styles.sectionEyebrow}>
              HISTÓRICO
            </Text>

            <Text style={styles.sectionTitle}>
              Enviadas recentemente
            </Text>
          </View>

          <View style={styles.countBadge}>
            <Text style={styles.countText}>
              {reports.data?.count ?? items.length}
            </Text>
          </View>
        </View>

        {reports.isPending ? (
          <View style={styles.inlineState}>
            <ActivityIndicator
              color={appTheme.colors.accent}
            />

            <Text style={styles.body}>
              Carregando suas denúncias...
            </Text>
          </View>
        ) : null}

        {reports.isError ? (
          <View style={styles.errorCard}>
            <Ionicons
              name="alert-circle-outline"
              size={20}
              color={appTheme.colors.danger}
            />

            <Text style={styles.errorText}>
              {reports.error instanceof Error
                ? reports.error.message
                : "Não foi possível carregar suas denúncias."}
            </Text>

            <Pressable
              accessibilityRole="button"
              style={styles.secondaryButton}
              onPress={() => {
                void reports.refetch();
              }}
            >
              <Text style={styles.secondaryButtonText}>
                Tentar novamente
              </Text>
            </Pressable>
          </View>
        ) : null}

        {!reports.isPending &&
        !reports.isError &&
        items.length === 0 ? (
          <View style={styles.emptyState}>
            <View style={styles.emptyIcon}>
              <Ionicons
                name="shield-checkmark-outline"
                size={28}
                color={appTheme.colors.textMuted}
              />
            </View>

            <Text style={styles.emptyTitle}>
              Nenhuma denúncia enviada
            </Text>

            <Text style={styles.bodyCentered}>
              Quando você reportar um problema em uma contribuição,
              poderá acompanhar o andamento por aqui.
            </Text>

            <Pressable
              accessibilityRole="button"
              style={styles.secondaryButton}
              onPress={() =>
                router.push(
                  "/discover" as never,
                )
              }
            >
              <Text style={styles.secondaryButtonText}>
                Ver contribuições
              </Text>
            </Pressable>
          </View>
        ) : null}

        <View style={styles.list}>
          {items.map((item) => (
            <ReportHistoryCard
              key={item.id}
              item={item}
              onPress={() =>
                router.push(
                  {
                    pathname: "/report-status",
                    params: {
                      reportId: item.id,
                    },
                  } as never,
                )
              }
            />
          ))}
        </View>

        {items.length > 0 ? (
          <View style={styles.limitNotice}>
            <Ionicons
              name="information-circle-outline"
              size={17}
              color={appTheme.colors.textMuted}
            />

            <Text style={styles.limitNoticeText}>
              Esta tela mostra até as 100 denúncias mais recentes
              retornadas pela API.
            </Text>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function ReportHistoryCard({
  item,
  onPress,
}: Readonly<{
  item: CommunityReportSummary;
  onPress: () => void;
}>) {
  const color = statusColor(
    item.status,
  );

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Abrir denúncia ${item.id}`}
      style={({ pressed }) => [
        styles.reportCard,
        pressed &&
          styles.reportCardPressed,
      ]}
      onPress={onPress}
    >
      <View style={styles.reportTop}>
        <View
          style={[
            styles.statusIcon,
            {
              borderColor: color,
            },
          ]}
        >
          <Ionicons
            name={statusIcon(item.status)}
            size={19}
            color={color}
          />
        </View>

        <View style={styles.reportCopy}>
          <Text style={styles.reasonLabel}>
            {REASON_LABELS[item.reason]}
          </Text>

          <Text
            style={styles.targetId}
            numberOfLines={1}
          >
            {item.targetId}
          </Text>
        </View>

        <View
          style={[
            styles.statusBadge,
            {
              borderColor: color,
            },
          ]}
        >
          <Text
            style={[
              styles.statusText,
              {
                color,
              },
            ]}
          >
            {STATUS_LABELS[item.status]}
          </Text>
        </View>
      </View>

      <View style={styles.reportFooter}>
        <Text style={styles.dateText}>
          Enviada em {dateLabel(item.createdAt)}
        </Text>

        <Ionicons
          name="chevron-forward"
          size={18}
          color={appTheme.colors.textSubtle}
        />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: appTheme.colors.background,
  },
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: appTheme.colors.background,
  },
  container: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 108,
    gap: 16,
  },
  header: {
    minHeight: 54,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  backButton: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 13,
    backgroundColor: appTheme.colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
  },
  headerCopy: {
    flex: 1,
  },
  eyebrow: {
    color: appTheme.colors.danger,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.3,
  },
  title: {
    marginTop: 2,
    color: appTheme.colors.text,
    fontSize: 24,
    fontWeight: "900",
    letterSpacing: -0.5,
  },
  hero: {
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.xl,
    backgroundColor: appTheme.colors.surface,
    padding: 18,
  },
  heroIcon: {
    width: 46,
    height: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 15,
    backgroundColor: appTheme.colors.dangerSurface,
  },
  heroTitle: {
    color: appTheme.colors.text,
    fontSize: 20,
    fontWeight: "900",
    letterSpacing: -0.3,
  },
  body: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 19,
  },
  bodyCentered: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 19,
    textAlign: "center",
  },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionHeadingCopy: {
    flex: 1,
  },
  sectionEyebrow: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  sectionTitle: {
    marginTop: 3,
    color: appTheme.colors.text,
    fontSize: 18,
    fontWeight: "900",
  },
  countBadge: {
    minWidth: 34,
    height: 30,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    paddingHorizontal: 9,
  },
  countText: {
    color: appTheme.colors.text,
    fontSize: 11,
    fontWeight: "900",
  },
  inlineState: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 15,
  },
  errorCard: {
    gap: 10,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.dangerSurface,
    padding: 15,
  },
  errorText: {
    color: appTheme.colors.danger,
    fontSize: 12,
    lineHeight: 18,
  },
  secondaryButton: {
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surface,
    paddingHorizontal: 16,
  },
  secondaryButtonText: {
    color: appTheme.colors.text,
    fontSize: 12,
    fontWeight: "900",
  },
  emptyState: {
    alignItems: "center",
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.xl,
    backgroundColor: appTheme.colors.surface,
    padding: 22,
  },
  emptyIcon: {
    width: 52,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 17,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  emptyTitle: {
    color: appTheme.colors.text,
    fontSize: 17,
    fontWeight: "900",
  },
  list: {
    gap: 10,
  },
  reportCard: {
    gap: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  reportCardPressed: {
    opacity: 0.78,
  },
  reportTop: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  statusIcon: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 13,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  reportCopy: {
    flex: 1,
    gap: 3,
  },
  reasonLabel: {
    color: appTheme.colors.text,
    fontSize: 13,
    fontWeight: "900",
  },
  targetId: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
  },
  statusBadge: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: appTheme.radius.pill,
    paddingHorizontal: 9,
    paddingVertical: 5,
  },
  statusText: {
    fontSize: 9,
    fontWeight: "900",
  },
  reportFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  dateText: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 10,
  },
  limitNotice: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surface,
    padding: 12,
  },
  limitNoticeText: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 16,
  },
});
