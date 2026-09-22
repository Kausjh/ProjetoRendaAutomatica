import { Ionicons } from "@expo/vector-icons";
import { Redirect, router } from "expo-router";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuthSession } from "@/src/auth";
import {
  CommunityDiscoveryItem,
  CommunityDiscoveryStatus,
  useCommunityDiscoveries,
  useCreateCommunityDiscovery,
} from "@/src/discoveries";
import { appTheme } from "@/src/ui";

const STATUS_LABELS: Readonly<
  Record<CommunityDiscoveryStatus, string>
> = {
  received: "Recebida",
  processing: "Em validação",
  retry: "Nova tentativa",
  approved: "Aprovada",
  rejected: "Rejeitada",
};

function marketplaceLabel(value: string | null): string {
  if (!value) {
    return "Loja ainda não identificada";
  }

  const labels: Record<string, string> = {
    mercado_livre: "Mercado Livre",
    kabum: "KaBuM!",
    shopee: "Shopee",
    aliexpress: "AliExpress",
    amazon: "Amazon",
  };

  return labels[value] ?? value.replace(/_/g, " ");
}

function hostLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function dateLabel(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }

  return parsed.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DiscoverScreen() {
  const { snapshot } = useAuthSession();
  const authenticated = snapshot.status === "authenticated";
  const discoveries = useCommunityDiscoveries(authenticated);
  const createDiscovery = useCreateCommunityDiscovery();

  const [url, setUrl] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const recent = useMemo(
    () => [...(discoveries.data?.items ?? [])],
    [discoveries.data],
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

  const submit = async (): Promise<void> => {
    const normalized = url.trim();
    setFeedback(null);

    if (!normalized) {
      setFeedback("Cole o link da oferta antes de enviar.");
      return;
    }

    try {
      const result = await createDiscovery.mutateAsync(normalized);

      setFeedback(
        result.duplicate
          ? "Esse link já estava na sua fila de contribuições."
          : "Oferta recebida. O Radar vai validar o link antes de aproveitá-lo.",
      );
      setUrl("");
    } catch (caught) {
      setFeedback(
        caught instanceof Error
          ? caught.message
          : "Não foi possível enviar a oferta.",
      );
    }
  };

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl
            tintColor={appTheme.colors.accent}
            colors={[appTheme.colors.accent]}
            refreshing={discoveries.isRefetching}
            onRefresh={() => {
              void discoveries.refetch();
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
            <Text style={styles.eyebrow}>COMUNIDADE</Text>
            <Text style={styles.title}>Encontrou uma oferta?</Text>
          </View>
        </View>

        <View style={styles.hero}>
          <View style={styles.heroIcon}>
            <Ionicons
              name="radio-outline"
              size={24}
              color={appTheme.colors.accent}
            />
          </View>

          <Text style={styles.heroTitle}>
            Ajude o Radar a descobrir antes.
          </Text>
          <Text style={styles.body}>
            Cole o link da promoção. A contribuição fica ligada à sua
            conta e passa por validação antes de poder entrar no Radar.
          </Text>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.sectionEyebrow}>ENVIAR LINK</Text>
          <Text style={styles.fieldLabel}>Link da oferta</Text>

          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            placeholder="https://loja.com/produto..."
            placeholderTextColor={appTheme.colors.textSubtle}
            selectionColor={appTheme.colors.accent}
            style={styles.input}
            value={url}
            onChangeText={setUrl}
          />

          <Text style={styles.hint}>
            O envio não publica nada automaticamente. O Radar recebe,
            identifica e valida a descoberta primeiro.
          </Text>

          {feedback ? (
            <View style={styles.feedback}>
              <Ionicons
                name="information-circle-outline"
                size={18}
                color={appTheme.colors.accent}
              />
              <Text style={styles.feedbackText}>{feedback}</Text>
            </View>
          ) : null}

          <Pressable
            accessibilityRole="button"
            disabled={createDiscovery.isPending}
            style={[
              styles.primaryButton,
              createDiscovery.isPending && styles.disabledButton,
            ]}
            onPress={() => {
              void submit();
            }}
          >
            {createDiscovery.isPending ? (
              <ActivityIndicator
                size="small"
                color={appTheme.colors.white}
              />
            ) : (
              <Ionicons
                name="send"
                size={17}
                color={appTheme.colors.white}
              />
            )}
            <Text style={styles.primaryButtonText}>
              {createDiscovery.isPending
                ? "Enviando..."
                : "Enviar para análise"}
            </Text>
          </Pressable>
        </View>

        <View style={styles.section}>
          <View style={styles.sectionHeading}>
            <View>
              <Text style={styles.sectionEyebrow}>SUAS CONTRIBUIÇÕES</Text>
              <Text style={styles.sectionTitle}>Enviadas recentemente</Text>
            </View>

            <View style={styles.countBadge}>
              <Text style={styles.countText}>
                {discoveries.data?.total ?? recent.length}
              </Text>
            </View>
          </View>

          {discoveries.isPending ? (
            <View style={styles.inlineState}>
              <ActivityIndicator color={appTheme.colors.accent} />
              <Text style={styles.body}>Carregando contribuições...</Text>
            </View>
          ) : null}

          {discoveries.isError ? (
            <View style={styles.errorCard}>
              <Text style={styles.errorText}>
                {discoveries.error instanceof Error
                  ? discoveries.error.message
                  : "Não foi possível carregar suas contribuições."}
              </Text>
              <Pressable
                accessibilityRole="button"
                style={styles.secondaryButton}
                onPress={() => {
                  void discoveries.refetch();
                }}
              >
                <Text style={styles.secondaryButtonText}>
                  Tentar novamente
                </Text>
              </Pressable>
            </View>
          ) : null}

          {!discoveries.isPending &&
          !discoveries.isError &&
          recent.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons
                name="link-outline"
                size={28}
                color={appTheme.colors.textMuted}
              />
              <Text style={styles.emptyTitle}>
                Nenhum link enviado ainda
              </Text>
              <Text style={styles.bodyCentered}>
                Quando você encontrar uma promoção, ela pode começar
                por aqui.
              </Text>
            </View>
          ) : null}

          {recent.map((item) => (
            <DiscoveryCard
              key={item.id}
              item={item}
              onReport={() =>
                router.push(
                  {
                    pathname: "/report",
                    params: {
                      targetId: item.id,
                      targetLabel: hostLabel(item.url),
                    },
                  } as never,
                )
              }
            />
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function DiscoveryCard({
  item,
  onReport,
}: Readonly<{
  item: CommunityDiscoveryItem;
  onReport: () => void;
}>) {
  const approved = item.status === "approved";
  const rejected = item.status === "rejected";

  return (
    <View style={styles.discoveryCard}>
      <View style={styles.discoveryTop}>
        <View
          style={[
            styles.statusIcon,
            approved && styles.statusIconApproved,
            rejected && styles.statusIconRejected,
          ]}
        >
          <Ionicons
            name={
              approved
                ? "checkmark"
                : rejected
                  ? "close"
                  : "time-outline"
            }
            size={18}
            color={
              approved
                ? appTheme.colors.success
                : rejected
                  ? appTheme.colors.danger
                  : appTheme.colors.accent
            }
          />
        </View>

        <View style={styles.discoveryCopy}>
          <Text style={styles.discoveryHost} numberOfLines={1}>
            {hostLabel(item.url)}
          </Text>
          <Text style={styles.discoveryMarketplace}>
            {marketplaceLabel(item.marketplace)}
          </Text>
        </View>

        <View style={styles.statusBadge}>
          <Text style={styles.statusText}>
            {STATUS_LABELS[item.status]}
          </Text>
        </View>
      </View>

      <Text style={styles.discoveryUrl} numberOfLines={2}>
        {item.url}
      </Text>

      <View style={styles.discoveryFooter}>
        <Text style={styles.dateText}>
          {dateLabel(item.createdAt)}
        </Text>

        {item.canonicalKey ? (
          <Text style={styles.canonicalText} numberOfLines={1}>
            {item.canonicalKey}
          </Text>
        ) : null}
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Denunciar problema nesta contribuição"
        style={({ pressed }) => [
          styles.reportButton,
          pressed && styles.reportButtonPressed,
        ]}
        onPress={onReport}
      >
        <Ionicons
          name="flag-outline"
          size={15}
          color={appTheme.colors.danger}
        />
        <Text style={styles.reportButtonText}>
          Denunciar problema
        </Text>
      </Pressable>
    </View>
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
    paddingBottom: 38,
    gap: 18,
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
    letterSpacing: 1.4,
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
    backgroundColor: appTheme.colors.accentSoft,
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
  formCard: {
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 15,
  },
  sectionEyebrow: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  fieldLabel: {
    color: appTheme.colors.text,
    fontSize: 13,
    fontWeight: "900",
  },
  input: {
    minHeight: 50,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    color: appTheme.colors.text,
    paddingHorizontal: 13,
    fontSize: 14,
  },
  hint: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 16,
  },
  feedback: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accentSoft,
    padding: 11,
  },
  feedbackText: {
    flex: 1,
    color: appTheme.colors.text,
    fontSize: 11,
    lineHeight: 17,
  },
  primaryButton: {
    minHeight: 49,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accentStrong,
    paddingHorizontal: 16,
  },
  primaryButtonText: {
    color: appTheme.colors.white,
    fontSize: 13,
    fontWeight: "900",
  },
  disabledButton: {
    opacity: 0.55,
  },
  section: {
    gap: 10,
  },
  sectionHeading: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
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
  emptyState: {
    alignItems: "center",
    gap: 9,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 28,
  },
  emptyTitle: {
    color: appTheme.colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  errorCard: {
    gap: 10,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.dangerSurface,
    padding: 14,
  },
  errorText: {
    color: appTheme.colors.danger,
    fontSize: 12,
    lineHeight: 18,
  },
  secondaryButton: {
    minHeight: 42,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.dangerBorder,
    borderRadius: appTheme.radius.md,
  },
  secondaryButtonText: {
    color: appTheme.colors.text,
    fontSize: 11,
    fontWeight: "900",
  },
  discoveryCard: {
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  discoveryTop: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  statusIcon: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.accentSoft,
  },
  statusIconApproved: {
    backgroundColor: appTheme.colors.successSurface,
  },
  statusIconRejected: {
    backgroundColor: appTheme.colors.dangerSurface,
  },
  discoveryCopy: {
    flex: 1,
    gap: 2,
  },
  discoveryHost: {
    color: appTheme.colors.text,
    fontSize: 13,
    fontWeight: "900",
  },
  discoveryMarketplace: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
  },
  statusBadge: {
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surfaceElevated,
    paddingHorizontal: 9,
    paddingVertical: 6,
  },
  statusText: {
    color: appTheme.colors.accent,
    fontSize: 9,
    fontWeight: "900",
  },
  discoveryUrl: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 15,
  },
  discoveryFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: appTheme.colors.border,
    paddingTop: 9,
  },
  dateText: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
  },
  canonicalText: {
    flex: 1,
    color: appTheme.colors.success,
    fontSize: 9,
    fontWeight: "800",
    textAlign: "right",
  },
  reportButton: {
    minHeight: 40,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.dangerBorder,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.dangerSurface,
    paddingHorizontal: 12,
  },
  reportButtonPressed: {
    opacity: 0.78,
  },
  reportButtonText: {
    color: appTheme.colors.danger,
    fontSize: 11,
    fontWeight: "900",
  },
});
