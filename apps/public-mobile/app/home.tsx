import { Ionicons } from "@expo/vector-icons";
import { Redirect, router } from "expo-router";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuthSession } from "@/src/auth";
import {
  ProductCard,
  formatPrice,
  useProductList,
} from "@/src/offers";
import { appTheme } from "@/src/ui";
import {
  useDeleteWatchlist,
  useUpsertWatchlist,
  useWatchlist,
} from "@/src/watchlist";

export default function HomeScreen() {
  const { snapshot } = useAuthSession();
  const authenticated = snapshot.status === "authenticated";
  const products = useProductList(50, 0);
  const watchlist = useWatchlist(authenticated);
  const upsertWatchlist = useUpsertWatchlist();
  const deleteWatchlist = useDeleteWatchlist();

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

  const totalProducts =
    products.data?.total ?? products.data?.items.length ?? 0;

  const watchedKeys = new Set(
    (watchlist.data?.items ?? []).map((item) => item.canonicalKey),
  );
  const watchlistBusy =
    watchlist.isPending ||
    upsertWatchlist.isPending ||
    deleteWatchlist.isPending;

  const toggleWatchlist = async (
    canonicalKey: string,
    watched: boolean,
  ): Promise<void> => {
    try {
      if (watched) {
        await deleteWatchlist.mutateAsync(canonicalKey);
        return;
      }

      await upsertWatchlist.mutateAsync({
        canonicalKey,
        targetPrice: null,
        notifyPriceDrop: true,
      });
    } catch (caught) {
      Alert.alert(
        "Não foi possível atualizar a Lista",
        caught instanceof Error
          ? caught.message
          : "Tente novamente em alguns instantes.",
      );
    }
  };

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <View style={styles.brandIcon}>
            <Ionicons
              name="game-controller"
              size={20}
              color={appTheme.colors.accent}
            />
          </View>

          <View style={styles.headerCopy}>
            <Text style={styles.brand}>Radar de Ofertas</Text>
            <Text style={styles.vertical}>GAMER</Text>
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Buscar produtos"
            style={styles.profileButton}
            onPress={() => router.push("/search")}
          >
            <Ionicons
              name="search"
              size={21}
              color={appTheme.colors.text}
            />
          </Pressable>
        </View>

        <View style={styles.hero}>
          <Text style={styles.heroEyebrow}>OFERTAS MONITORADAS</Text>
          <Text style={styles.heroTitle}>
            Preço bom sem perder tempo procurando.
          </Text>
          <Text style={styles.heroBody}>
            O Radar acompanha marketplaces e organiza os melhores
            preços encontrados para o seu setup.
          </Text>

          <View style={styles.heroStats}>
            <View style={styles.stat}>
              <Text style={styles.statValue}>{totalProducts}</Text>
              <Text style={styles.statLabel}>produtos</Text>
            </View>

            <View style={styles.statDivider} />

            <View style={styles.stat}>
              <Text style={styles.statValue}>Gamer</Text>
              <Text style={styles.statLabel}>radar ativo</Text>
            </View>
          </View>
        </View>
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Enviar uma oferta encontrada"
        style={({ pressed }) => [
          styles.communityCard,
          pressed && styles.communityCardPressed,
        ]}
        onPress={() => router.push("/discover" as never)}
      >
        <View style={styles.communityIcon}>
          <Ionicons
            name="radio-outline"
            size={20}
            color={appTheme.colors.accent}
          />
        </View>

        <View style={styles.communityCopy}>
          <Text style={styles.communityEyebrow}>COMUNIDADE</Text>
          <Text style={styles.communityTitle}>
            Encontrou uma oferta?
          </Text>
          <Text style={styles.communityBody}>
            Envie o link para o Radar validar.
          </Text>
        </View>

        <Ionicons
          name="chevron-forward"
          size={18}
          color={appTheme.colors.textMuted}
        />
      </Pressable>

      {products.isPending ? (
        <View style={styles.centerState}>
          <ActivityIndicator
            size="large"
            color={appTheme.colors.accent}
          />
          <Text style={styles.body}>Carregando ofertas...</Text>
        </View>
      ) : null}

      {products.isError ? (
        <View style={styles.centerState}>
          <View style={styles.stateIcon}>
            <Ionicons
              name="cloud-offline-outline"
              size={28}
              color={appTheme.colors.warning}
            />
          </View>
          <Text style={styles.stateTitle}>
            Não foi possível carregar as ofertas
          </Text>
          <Text style={styles.body}>
            {products.error instanceof Error
              ? products.error.message
              : "Falha desconhecida."}
          </Text>

          <Pressable
            accessibilityRole="button"
            style={styles.primaryButton}
            onPress={() => {
              void products.refetch();
            }}
          >
            <Text style={styles.primaryButtonText}>
              Tentar novamente
            </Text>
          </Pressable>
        </View>
      ) : null}

      {products.data ? (
        <FlatList
          data={[...products.data.items]}
          keyExtractor={(item) => item.canonicalKey}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={[
            styles.listContent,
            products.data.items.length === 0 &&
              styles.emptyListContent,
          ]}
          refreshControl={
            <RefreshControl
              tintColor={appTheme.colors.accent}
              colors={[appTheme.colors.accent]}
              refreshing={
                products.isRefetching || watchlist.isRefetching
              }
              onRefresh={() => {
                void Promise.all([
                  products.refetch(),
                  watchlist.refetch(),
                ]);
              }}
            />
          }
          ListHeaderComponent={
            <View style={styles.feedHeader}>
              <View>
                <Text style={styles.feedEyebrow}>AGORA</Text>
                <Text style={styles.feedTitle}>Melhores preços</Text>
              </View>

              <View style={styles.liveBadge}>
                <View style={styles.liveDot} />
                <Text style={styles.liveText}>Radar ativo</Text>
              </View>
            </View>
          }
          ListEmptyComponent={
            <View style={styles.centerState}>
              <View style={styles.stateIcon}>
                <Ionicons
                  name="search-outline"
                  size={28}
                  color={appTheme.colors.textMuted}
                />
              </View>
              <Text style={styles.stateTitle}>
                Nenhuma oferta encontrada
              </Text>
              <Text style={styles.body}>
                O Radar respondeu normalmente, mas não há produtos
                disponíveis agora.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <ProductCardView
              item={item}
              watched={watchedKeys.has(item.canonicalKey)}
              watchlistBusy={watchlistBusy}
              onToggleWatchlist={(canonicalKey, watched) =>
                toggleWatchlist(canonicalKey, watched)
              }
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
      ) : null}
    </SafeAreaView>
  );
}

function ProductCardView({
  item,
  watched,
  watchlistBusy,
  onToggleWatchlist,
  onPress,
}: Readonly<{
  item: ProductCard;
  watched: boolean;
  watchlistBusy: boolean;
  onToggleWatchlist: (
    canonicalKey: string,
    watched: boolean,
  ) => Promise<void>;
  onPress: () => void;
}>) {
  const marketplace =
    item.marketplace?.trim() || "Marketplace";

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
        <View style={styles.marketplaceBadge}>
          <Ionicons
            name="storefront-outline"
            size={14}
            color={appTheme.colors.accent}
          />
          <Text style={styles.marketplace} numberOfLines={1}>
            {marketplace}
          </Text>
        </View>

        <View style={styles.cardHeaderActions}>
          {item.discountPercent !== null ? (
            <View style={styles.discountBadge}>
              <Ionicons
                name="pricetag"
                size={12}
                color={appTheme.colors.success}
              />
              <Text style={styles.discount}>
                -{Math.round(item.discountPercent)}%
              </Text>
            </View>
          ) : null}

          <Pressable
            accessibilityRole="button"
            accessibilityLabel={
              watched ? "Remover da Lista" : "Salvar na Lista"
            }
            accessibilityState={{ selected: watched }}
            disabled={watchlistBusy}
            hitSlop={8}
            style={[
              styles.watchButton,
              watched && styles.watchButtonActive,
              watchlistBusy && styles.watchButtonDisabled,
            ]}
            onPress={(event) => {
              event.stopPropagation();
              void onToggleWatchlist(item.canonicalKey, watched);
            }}
          >
            <Ionicons
              name={watched ? "heart" : "heart-outline"}
              size={18}
              color={
                watched
                  ? appTheme.colors.accent
                  : appTheme.colors.textMuted
              }
            />
          </Pressable>
        </View>
      </View>

      <View style={styles.cardMain}>
        <View style={styles.productGlyph}>
          <Ionicons
            name="hardware-chip-outline"
            size={30}
            color={appTheme.colors.textMuted}
          />
        </View>

        <View style={styles.cardCopy}>
          <Text style={styles.cardTitle} numberOfLines={3}>
            {item.title}
          </Text>

          <View style={styles.priceLine}>
            <Text style={styles.price}>
              {formatPrice(item.currentPrice)}
            </Text>

            {item.originalPrice !== null ? (
              <Text style={styles.originalPrice}>
                {formatPrice(item.originalPrice)}
              </Text>
            ) : null}
          </View>
        </View>
      </View>

      <View style={styles.cardFooter}>
        <View style={styles.intelligenceChip}>
          <Ionicons
            name="pulse-outline"
            size={13}
            color={appTheme.colors.textMuted}
          />
          <Text style={styles.intelligenceText}>
            Histórico disponível
          </Text>
        </View>

        <View style={styles.openButton}>
          <Text style={styles.openLabel}>Ver oferta</Text>
          <Ionicons
            name="chevron-forward"
            size={15}
            color={appTheme.colors.text}
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
    backgroundColor: appTheme.colors.background,
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 10,
    gap: 16,
  },
  communityCard: {
    marginHorizontal: 16,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 13,
  },
  communityCardPressed: {
    opacity: 0.84,
  },
  communityIcon: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 13,
    backgroundColor: appTheme.colors.accentSoft,
  },
  communityCopy: {
    flex: 1,
    gap: 2,
  },
  communityEyebrow: {
    color: appTheme.colors.accent,
    fontSize: 8,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  communityTitle: {
    color: appTheme.colors.text,
    fontSize: 13,
    fontWeight: "900",
  },
  communityBody: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
  },
  brandRow: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  brandIcon: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.accentSoft,
  },
  headerCopy: {
    flex: 1,
  },
  brand: {
    color: appTheme.colors.text,
    fontSize: 17,
    fontWeight: "900",
    letterSpacing: -0.2,
  },
  vertical: {
    marginTop: 2,
    color: appTheme.colors.accent,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.7,
  },
  profileButton: {
    width: 42,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surface,
  },
  hero: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.xl,
    backgroundColor: appTheme.colors.surface,
    padding: 18,
  },
  heroEyebrow: {
    color: appTheme.colors.accent,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.5,
  },
  heroTitle: {
    marginTop: 8,
    color: appTheme.colors.text,
    fontSize: 24,
    lineHeight: 29,
    fontWeight: "900",
    letterSpacing: -0.6,
  },
  heroBody: {
    marginTop: 8,
    color: appTheme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },
  heroStats: {
    marginTop: 16,
    flexDirection: "row",
    alignItems: "center",
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: appTheme.colors.border,
    paddingTop: 14,
  },
  stat: {
    flex: 1,
  },
  statValue: {
    color: appTheme.colors.text,
    fontSize: 17,
    fontWeight: "900",
  },
  statLabel: {
    marginTop: 2,
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "600",
  },
  statDivider: {
    width: StyleSheet.hairlineWidth,
    height: 30,
    backgroundColor: appTheme.colors.border,
    marginHorizontal: 14,
  },
  feedHeader: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 2,
  },
  feedEyebrow: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.3,
  },
  feedTitle: {
    marginTop: 2,
    color: appTheme.colors.text,
    fontSize: 20,
    fontWeight: "900",
  },
  liveBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surface,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  liveDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: appTheme.colors.success,
  },
  liveText: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "800",
  },
  body: {
    color: appTheme.colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
  centerState: {
    flex: 1,
    minHeight: 250,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 24,
    backgroundColor: appTheme.colors.background,
  },
  stateIcon: {
    width: 52,
    height: 52,
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
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 2,
    paddingBottom: 108,
    gap: 12,
  },
  emptyListContent: {
    flexGrow: 1,
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
    opacity: 0.82,
    transform: [{ scale: 0.995 }],
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  marketplaceBadge: {
    minWidth: 0,
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  marketplace: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 11,
    fontWeight: "800",
    textTransform: "capitalize",
  },
  cardHeaderActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  watchButton: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  watchButtonActive: {
    borderColor: appTheme.colors.accent,
    backgroundColor: appTheme.colors.accentSoft,
  },
  watchButtonDisabled: {
    opacity: 0.55,
  },
  discountBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.successSurface,
    paddingHorizontal: 8,
    paddingVertical: 5,
  },
  discount: {
    color: appTheme.colors.success,
    fontSize: 11,
    fontWeight: "900",
  },
  cardMain: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  productGlyph: {
    width: 72,
    height: 72,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 16,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  cardCopy: {
    flex: 1,
    gap: 8,
  },
  cardTitle: {
    color: appTheme.colors.text,
    fontSize: 15,
    lineHeight: 20,
    fontWeight: "800",
  },
  priceLine: {
    flexDirection: "row",
    alignItems: "baseline",
    flexWrap: "wrap",
    gap: 8,
  },
  price: {
    color: appTheme.colors.price,
    fontSize: 20,
    fontWeight: "900",
  },
  originalPrice: {
    color: appTheme.colors.textSubtle,
    fontSize: 11,
    textDecorationLine: "line-through",
  },
  cardFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: appTheme.colors.border,
    paddingTop: 11,
  },
  intelligenceChip: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
  },
  intelligenceText: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "700",
  },
  openButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surfaceElevated,
    paddingHorizontal: 11,
    paddingVertical: 7,
  },
  openLabel: {
    color: appTheme.colors.text,
    fontSize: 11,
    fontWeight: "900",
  },
});
