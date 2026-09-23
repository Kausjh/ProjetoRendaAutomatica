import { Ionicons } from "@expo/vector-icons";
import {
  Redirect,
  router,
  useLocalSearchParams,
} from "expo-router";
import {
  ActivityIndicator,
  Pressable,
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
  useCommunityReport,
} from "@/src/reporting";
import { appTheme } from "@/src/ui";

const STATUS_LABELS: Readonly<
  Record<CommunityReportStatus, string>
> = {
  received: "Recebida",
  under_review: "Em análise",
  resolved: "Concluída",
};

const STATUS_DESCRIPTIONS: Readonly<
  Record<CommunityReportStatus, string>
> = {
  received:
    "A denúncia foi recebida e está aguardando ou iniciando a revisão.",
  under_review:
    "A denúncia está em análise pela camada responsável de moderação.",
  resolved:
    "A revisão administrativa foi encerrada. Este status não informa, por si só, se houve confirmação de abuso.",
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

function firstParam(
  value: string | string[] | undefined,
): string {
  return Array.isArray(value)
    ? value[0] ?? ""
    : value ?? "";
}

function dateLabel(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
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

export default function ReportStatusScreen() {
  const { snapshot } = useAuthSession();

  const params = useLocalSearchParams<{
    reportId?: string | string[];
  }>();

  const reportId = firstParam(
    params.reportId,
  ).trim();

  const authenticated =
    snapshot.status === "authenticated";

  const report = useCommunityReport(
    reportId,
    authenticated && Boolean(reportId),
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

  if (!reportId) {
    return (
      <SafeAreaView
        style={styles.screen}
        edges={["top"]}
      >
        <View style={styles.invalidState}>
          <Ionicons
            name="alert-circle-outline"
            size={38}
            color={appTheme.colors.danger}
          />

          <Text style={styles.invalidTitle}>
            Denúncia inválida
          </Text>

          <Text style={styles.bodyCentered}>
            Não recebemos uma identificação válida para consultar
            esta denúncia.
          </Text>

          <Pressable
            accessibilityRole="button"
            style={styles.secondaryButton}
            onPress={() => router.back()}
          >
            <Text style={styles.secondaryButtonText}>
              Voltar
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const item = report.data;

  return (
    <SafeAreaView
      style={styles.screen}
      edges={["top"]}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.container}
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
              SUA DENÚNCIA
            </Text>

            <Text style={styles.title}>
              Acompanhamento
            </Text>
          </View>
        </View>

        {report.isPending ? (
          <View style={styles.inlineState}>
            <ActivityIndicator
              color={appTheme.colors.accent}
            />

            <Text style={styles.body}>
              Carregando denúncia...
            </Text>
          </View>
        ) : null}

        {report.isError ? (
          <View style={styles.errorCard}>
            <Ionicons
              name="alert-circle-outline"
              size={20}
              color={appTheme.colors.danger}
            />

            <Text style={styles.errorText}>
              {report.error instanceof Error
                ? report.error.message
                : "Não foi possível carregar esta denúncia."}
            </Text>

            <Pressable
              accessibilityRole="button"
              style={styles.secondaryButton}
              onPress={() => {
                void report.refetch();
              }}
            >
              <Text style={styles.secondaryButtonText}>
                Tentar novamente
              </Text>
            </Pressable>
          </View>
        ) : null}

        {item ? (
          <>
            <View style={styles.statusCard}>
              <View
                style={[
                  styles.statusIcon,
                  {
                    borderColor: statusColor(
                      item.status,
                    ),
                  },
                ]}
              >
                <Ionicons
                  name={statusIcon(item.status)}
                  size={26}
                  color={statusColor(
                    item.status,
                  )}
                />
              </View>

              <View style={styles.statusCopy}>
                <Text style={styles.sectionEyebrow}>
                  STATUS
                </Text>

                <Text
                  style={[
                    styles.statusTitle,
                    {
                      color: statusColor(
                        item.status,
                      ),
                    },
                  ]}
                >
                  {STATUS_LABELS[item.status]}
                </Text>

                <Text style={styles.body}>
                  {STATUS_DESCRIPTIONS[item.status]}
                </Text>
              </View>
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionEyebrow}>
                MOTIVO REPORTADO
              </Text>

              <Text style={styles.cardTitle}>
                {REASON_LABELS[item.reason]}
              </Text>

              <View style={styles.divider} />

              <Text style={styles.fieldLabel}>
                Contribuição
              </Text>

              <Text
                style={styles.monoValue}
                selectable
              >
                {item.targetId}
              </Text>

              <Text style={styles.fieldLabel}>
                ID da denúncia
              </Text>

              <Text
                style={styles.monoValue}
                selectable
              >
                {item.id}
              </Text>
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionEyebrow}>
                DETALHES ENVIADOS
              </Text>

              <Text style={styles.detailsText}>
                {item.details ??
                  "Nenhum detalhe adicional foi enviado."}
              </Text>
            </View>

            <View style={styles.card}>
              <Text style={styles.sectionEyebrow}>
                LINHA DO TEMPO
              </Text>

              <View style={styles.timelineRow}>
                <View style={styles.timelineIcon}>
                  <Ionicons
                    name="send-outline"
                    size={17}
                    color={appTheme.colors.accent}
                  />
                </View>

                <View style={styles.timelineCopy}>
                  <Text style={styles.timelineLabel}>
                    Enviada
                  </Text>

                  <Text style={styles.timelineValue}>
                    {dateLabel(item.createdAt)}
                  </Text>
                </View>
              </View>

              <View style={styles.divider} />

              <View style={styles.timelineRow}>
                <View style={styles.timelineIcon}>
                  <Ionicons
                    name="refresh-outline"
                    size={17}
                    color={appTheme.colors.textMuted}
                  />
                </View>

                <View style={styles.timelineCopy}>
                  <Text style={styles.timelineLabel}>
                    Última atualização
                  </Text>

                  <Text style={styles.timelineValue}>
                    {dateLabel(item.updatedAt)}
                  </Text>
                </View>
              </View>
            </View>

            <View style={styles.notice}>
              <Ionicons
                name="information-circle-outline"
                size={19}
                color={appTheme.colors.textMuted}
              />

              <Text style={styles.noticeText}>
                O aplicativo mostra somente o estado público da sua
                denúncia. Dados internos de moderação, justificativas,
                decisões administrativas e dados de Trust não são
                exibidos aqui.
              </Text>
            </View>
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
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
    color: appTheme.colors.accent,
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
  inlineState: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 15,
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
  statusCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 13,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.xl,
    backgroundColor: appTheme.colors.surface,
    padding: 17,
  },
  statusIcon: {
    width: 52,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 17,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  statusCopy: {
    flex: 1,
    gap: 4,
  },
  sectionEyebrow: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  statusTitle: {
    fontSize: 20,
    fontWeight: "900",
  },
  card: {
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 15,
  },
  cardTitle: {
    color: appTheme.colors.text,
    fontSize: 17,
    fontWeight: "900",
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: appTheme.colors.border,
  },
  fieldLabel: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "800",
  },
  monoValue: {
    color: appTheme.colors.text,
    fontSize: 11,
    lineHeight: 17,
  },
  detailsText: {
    color: appTheme.colors.text,
    fontSize: 12,
    lineHeight: 19,
  },
  timelineRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  timelineIcon: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  timelineCopy: {
    flex: 1,
    gap: 2,
  },
  timelineLabel: {
    color: appTheme.colors.text,
    fontSize: 11,
    fontWeight: "900",
  },
  timelineValue: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
  },
  notice: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 9,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  noticeText: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 16,
  },
  invalidState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 28,
  },
  invalidTitle: {
    color: appTheme.colors.text,
    fontSize: 20,
    fontWeight: "900",
  },
});
