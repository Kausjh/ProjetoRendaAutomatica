import { Ionicons } from "@expo/vector-icons";
import { Redirect, router } from "expo-router";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  AlertCard,
  formatAlertTimestamp,
  useAlertList,
} from "@/src/alerts";
import { useAuthSession } from "@/src/auth";
import { formatPrice } from "@/src/offers";
import { appTheme } from "@/src/ui";

function humanizeCanonicalKey(value: string): string {
  const words = value
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .split(/\s+/)
    .filter(Boolean);

  return words
    .map((word) => {
      const lower = word.toLowerCase();

      if (
        ["rtx", "gtx", "rx", "ssd", "ram", "nvme", "gpu", "cpu"].includes(
          lower,
        )
      ) {
        return lower.toUpperCase();
      }

      if (/^i[3579]$/i.test(word)) {
        return lower;
      }

      const model = word.match(/^(\d+)(gt|x|xt|xtx|ti)$/i);
      if (model) {
        const numberPart = model[1] ?? "";
        const suffixPart = model[2] ?? "";

        return `${numberPart}${suffixPart.toUpperCase()}`;
      }

      if (/^\d/.test(word)) {
        return word;
      }

      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

export default function AlertsScreen() {
  const { snapshot } = useAuthSession();
  const alerts = useAlertList(100, 0);

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

  if (snapshot.status !== "authenticated") {
    return <Redirect href="/" />;
  }

  if (alerts.isPending) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator
          size="large"
          color={appTheme.colors.accent}
        />
        <Text style={styles.body}>Carregando seus alertas...</Text>
      </View>
    );
  }

  if (alerts.isError) {
    return (
      <View style={styles.loading}>
        <View style={styles.stateIcon}>
          <Ionicons
            name="notifications-off-outline"
            size={28}
            color={appTheme.colors.warning}
          />
        </View>

        <Text style={styles.stateTitle}>
          Não foi possível carregar os alertas
        </Text>

        <Text style={styles.body}>
          {alerts.error instanceof Error
            ? alerts.error.message
            : "Tente novamente em alguns instantes."}
        </Text>

        <Pressable
          accessibilityRole="button"
          style={styles.primaryButton}
          onPress={() => {
            void alerts.refetch();
          }}
        >
          <Text style={styles.primaryButtonText}>Tentar novamente</Text>
        </Pressable>
      </View>
    );
  }

  const items = [...(alerts.data?.items ?? [])];

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[
          styles.listContent,
          items.length === 0 && styles.emptyListContent,
        ]}
        refreshControl={
          <RefreshControl
            tintColor={appTheme.colors.accent}
            colors={[appTheme.colors.accent]}
            refreshing={alerts.isRefetching}
            onRefresh={() => {
              void alerts.refetch();
            }}
          />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.headerTop}>
              <View style={styles.headerIcon}>
                <Ionicons
                  name="notifications"
                  size={20}
                  color={appTheme.colors.accent}
                />
              </View>

              <View style={styles.headerCopy}>
                <Text style={styles.eyebrow}>ALERTAS DE PREÇO</Text>
                <Text style={styles.title}>Alertas</Text>
              </View>

              <View style={styles.countBadge}>
                <Text style={styles.countValue}>{items.length}</Text>
              </View>
            </View>

            <Text style={styles.bodyLeft}>
              Mudanças importantes de preço encontradas pelo Radar.
            </Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <View style={styles.stateIcon}>
              <Ionicons
                name="notifications-outline"
                size={30}
                color={appTheme.colors.textMuted}
              />
            </View>
            <Text style={styles.stateTitle}>Nenhum alerta por enquanto</Text>
            <Text style={styles.body}>
              Quando o Radar detectar uma mudança relevante, ela aparece
              aqui.
            </Text>
          </View>
        }
        renderItem={({ item }) => <AlertCardView item={item} />}
      />
    </SafeAreaView>
  );
}

function AlertCardView({
  item,
}: Readonly<{
  item: AlertCard;
}>) {
  const canOpenProduct = Boolean(item.canonicalKey);
  const productLabel = item.canonicalKey
    ? humanizeCanonicalKey(item.canonicalKey)
    : "Produto monitorado";

  const openProduct = (): void => {
    if (!item.canonicalKey) {
      return;
    }

    router.push({
      pathname: "/product/[canonicalKey]",
      params: {
        canonicalKey: item.canonicalKey,
      },
    });
  };

  const isBestPrice = item.title.toLowerCase().includes("menor");

  return (
    <Pressable
      accessibilityRole={canOpenProduct ? "button" : undefined}
      disabled={!canOpenProduct}
      style={({ pressed }) => [
        styles.card,
        pressed && canOpenProduct && styles.cardPressed,
      ]}
      onPress={openProduct}
    >
      <View style={styles.cardTopRow}>
        <View
          style={[
            styles.eventIcon,
            isBestPrice && styles.eventIconBest,
          ]}
        >
          <Ionicons
            name={isBestPrice ? "trending-down" : "pulse-outline"}
            size={18}
            color={
              isBestPrice
                ? appTheme.colors.success
                : appTheme.colors.accent
            }
          />
        </View>

        <View style={styles.cardCopy}>
          <Text style={styles.cardTitle}>{item.title}</Text>
          <Text style={styles.productName} numberOfLines={1}>
            {productLabel}
          </Text>
        </View>

        <Text style={styles.date}>
          {formatAlertTimestamp(item.occurredAt)}
        </Text>
      </View>

      {item.marketplace ? (
        <View style={styles.marketplaceRow}>
          <Ionicons
            name="storefront-outline"
            size={13}
            color={appTheme.colors.textMuted}
          />
          <Text style={styles.marketplace}>
            {item.marketplace}
          </Text>
        </View>
      ) : null}

      {item.currentPrice !== null ||
      item.previousPrice !== null ? (
        <View style={styles.pricePanel}>
          {item.previousPrice !== null ? (
            <View style={styles.priceBlock}>
              <Text style={styles.priceLabel}>ANTES</Text>
              <Text style={styles.previousPrice}>
                {formatPrice(item.previousPrice)}
              </Text>
            </View>
          ) : null}

          <Ionicons
            name="arrow-forward"
            size={16}
            color={appTheme.colors.textSubtle}
          />

          {item.currentPrice !== null ? (
            <View style={styles.priceBlock}>
              <Text style={styles.priceLabel}>AGORA</Text>
              <Text style={styles.currentPrice}>
                {formatPrice(item.currentPrice)}
              </Text>
            </View>
          ) : null}
        </View>
      ) : null}

      {item.message ? (
        <Text style={styles.message} numberOfLines={2}>
          {item.message}
        </Text>
      ) : null}

      {canOpenProduct ? (
        <View style={styles.cardFooter}>
          <Text style={styles.openLabel}>Ver produto</Text>
          <Ionicons
            name="chevron-forward"
            size={15}
            color={appTheme.colors.text}
          />
        </View>
      ) : null}
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
    gap: 12,
    padding: 24,
    backgroundColor: appTheme.colors.background,
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 108,
    gap: 12,
  },
  emptyListContent: {
    flexGrow: 1,
  },
  header: {
    gap: 12,
    marginBottom: 6,
  },
  headerTop: {
    minHeight: 54,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  headerIcon: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 13,
    backgroundColor: appTheme.colors.accentSoft,
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
    fontSize: 25,
    fontWeight: "900",
    letterSpacing: -0.5,
  },
  countBadge: {
    minWidth: 38,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    paddingHorizontal: 10,
  },
  countValue: {
    color: appTheme.colors.text,
    fontSize: 12,
    fontWeight: "900",
  },
  body: {
    color: appTheme.colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
  bodyLeft: {
    color: appTheme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },
  emptyState: {
    flex: 1,
    minHeight: 360,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 28,
  },
  stateIcon: {
    width: 56,
    height: 56,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 18,
    backgroundColor: appTheme.colors.surface,
  },
  stateTitle: {
    color: appTheme.colors.text,
    fontSize: 19,
    fontWeight: "900",
    textAlign: "center",
  },
  primaryButton: {
    minHeight: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accentStrong,
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: appTheme.colors.white,
    fontWeight: "900",
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
    gap: 12,
  },
  cardPressed: {
    opacity: 0.84,
  },
  cardTopRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  eventIcon: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.accentSoft,
  },
  eventIconBest: {
    backgroundColor: appTheme.colors.successSurface,
  },
  cardCopy: {
    flex: 1,
    gap: 2,
  },
  cardTitle: {
    color: appTheme.colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  productName: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
    fontWeight: "700",
  },
  date: {
    maxWidth: 92,
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    lineHeight: 13,
    textAlign: "right",
  },
  marketplaceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  marketplace: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "capitalize",
  },
  pricePanel: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    padding: 12,
  },
  priceBlock: {
    flex: 1,
    gap: 3,
  },
  priceLabel: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.9,
  },
  previousPrice: {
    color: appTheme.colors.textMuted,
    fontSize: 13,
    textDecorationLine: "line-through",
  },
  currentPrice: {
    color: appTheme.colors.price,
    fontSize: 18,
    fontWeight: "900",
  },
  message: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
  },
  cardFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    gap: 3,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: appTheme.colors.border,
    paddingTop: 10,
  },
  openLabel: {
    color: appTheme.colors.text,
    fontSize: 11,
    fontWeight: "900",
  },
});
