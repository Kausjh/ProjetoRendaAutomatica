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

import { useAuthSession } from "@/src/auth";
import { formatPrice } from "@/src/offers";
import { appTheme } from "@/src/ui";
import {
  WatchlistItem,
  useWatchlist,
} from "@/src/watchlist";

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

export default function WatchlistScreen() {
  const { snapshot } = useAuthSession();
  const authenticated = snapshot.status === "authenticated";
  const watchlist = useWatchlist(authenticated);

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

  if (watchlist.isPending) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator
          size="large"
          color={appTheme.colors.accent}
        />
        <Text style={styles.body}>Carregando sua lista...</Text>
      </View>
    );
  }

  if (watchlist.isError) {
    return (
      <View style={styles.loading}>
        <View style={styles.stateIcon}>
          <Ionicons
            name="heart-dislike-outline"
            size={28}
            color={appTheme.colors.warning}
          />
        </View>

        <Text style={styles.stateTitle}>
          Não foi possível carregar sua lista
        </Text>

        <Text style={styles.body}>
          {watchlist.error instanceof Error
            ? watchlist.error.message
            : "Tente novamente em alguns instantes."}
        </Text>

        <Pressable
          accessibilityRole="button"
          style={styles.primaryButton}
          onPress={() => {
            void watchlist.refetch();
          }}
        >
          <Text style={styles.primaryButtonText}>Tentar novamente</Text>
        </Pressable>
      </View>
    );
  }

  const items = [...(watchlist.data?.items ?? [])];

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.canonicalKey}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[
          styles.listContent,
          items.length === 0 && styles.emptyListContent,
        ]}
        refreshControl={
          <RefreshControl
            tintColor={appTheme.colors.accent}
            colors={[appTheme.colors.accent]}
            refreshing={watchlist.isRefetching}
            onRefresh={() => {
              void watchlist.refetch();
            }}
          />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.headerTop}>
              <View style={styles.headerIcon}>
                <Ionicons
                  name="heart"
                  size={20}
                  color={appTheme.colors.accent}
                />
              </View>

              <View style={styles.headerCopy}>
                <Text style={styles.eyebrow}>ACOMPANHAMENTO</Text>
                <Text style={styles.title}>Sua lista</Text>
              </View>

              <View style={styles.countBadge}>
                <Text style={styles.countValue}>{items.length}</Text>
              </View>
            </View>

            <Text style={styles.bodyLeft}>
              Produtos que você quer acompanhar por queda de preço ou
              preço-alvo.
            </Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <View style={styles.stateIcon}>
              <Ionicons
                name="heart-outline"
                size={30}
                color={appTheme.colors.textMuted}
              />
            </View>

            <Text style={styles.stateTitle}>
              Sua lista está vazia
            </Text>

            <Text style={styles.body}>
              Abra um produto e escolha acompanhar para receber
              atualizações de preço.
            </Text>

            <Pressable
              accessibilityRole="button"
              style={styles.primaryButton}
              onPress={() => router.replace("/home")}
            >
              <Text style={styles.primaryButtonText}>Explorar ofertas</Text>
            </Pressable>
          </View>
        }
        renderItem={({ item }) => (
          <WatchlistCard
            item={item}
            onPress={() =>
              router.push({
                pathname: "/product/[canonicalKey]",
                params: {
                  canonicalKey: item.canonicalKey,
                },
              })
            }
          />
        )}
      />
    </SafeAreaView>
  );
}

function WatchlistCard({
  item,
  onPress,
}: Readonly<{
  item: WatchlistItem;
  onPress: () => void;
}>) {
  const productLabel = humanizeCanonicalKey(item.canonicalKey);

  return (
    <Pressable
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.card,
        pressed && styles.cardPressed,
      ]}
      onPress={onPress}
    >
      <View style={styles.cardHeader}>
        <View style={styles.productIcon}>
          <Ionicons
            name="hardware-chip-outline"
            size={24}
            color={appTheme.colors.textMuted}
          />
        </View>

        <View style={styles.cardCopy}>
          <Text style={styles.cardTitle} numberOfLines={2}>
            {productLabel}
          </Text>

          <View style={styles.activeRow}>
            <View
              style={[
                styles.statusDot,
                item.notifyPriceDrop
                  ? styles.statusDotActive
                  : styles.statusDotDisabled,
              ]}
            />
            <Text style={styles.activeText}>
              {item.notifyPriceDrop
                ? "Alertas de queda ativos"
                : "Alertas de queda desativados"}
            </Text>
          </View>
        </View>

        <Ionicons
          name="chevron-forward"
          size={18}
          color={appTheme.colors.textSubtle}
        />
      </View>

      <View style={styles.targetPanel}>
        <View>
          <Text style={styles.metaLabel}>PREÇO-ALVO</Text>
          <Text style={styles.targetPrice}>
            {item.targetPrice === null
              ? "Não definido"
              : formatPrice(item.targetPrice)}
          </Text>
        </View>

        <View style={styles.bellBadge}>
          <Ionicons
            name={
              item.notifyPriceDrop
                ? "notifications"
                : "notifications-off-outline"
            }
            size={17}
            color={
              item.notifyPriceDrop
                ? appTheme.colors.accent
                : appTheme.colors.textSubtle
            }
          />
        </View>
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
    gap: 13,
  },
  cardPressed: {
    opacity: 0.84,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
  },
  productIcon: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  cardCopy: {
    flex: 1,
    gap: 5,
  },
  cardTitle: {
    color: appTheme.colors.text,
    fontSize: 15,
    lineHeight: 20,
    fontWeight: "900",
  },
  activeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  statusDotActive: {
    backgroundColor: appTheme.colors.success,
  },
  statusDotDisabled: {
    backgroundColor: appTheme.colors.textSubtle,
  },
  activeText: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "700",
  },
  targetPanel: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    padding: 12,
  },
  metaLabel: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.9,
  },
  targetPrice: {
    marginTop: 4,
    color: appTheme.colors.price,
    fontSize: 16,
    fontWeight: "900",
  },
  bellBadge: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.surfaceSoft,
  },
});
