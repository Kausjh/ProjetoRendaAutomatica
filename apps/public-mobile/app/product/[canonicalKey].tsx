import { Ionicons } from "@expo/vector-icons";
import { Redirect, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";

import { useAuthSession } from "@/src/auth";
import {
  formatHistoryTimestamp,
  formatPrice,
  useProductDetail,
  useProductHistory,
} from "@/src/offers";
import { appTheme } from "@/src/ui";
import {
  useDeleteWatchlist,
  useUpsertWatchlist,
  useWatchlist,
} from "@/src/watchlist";

function firstParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function parseTargetPrice(value: string): number | null {
  const compact = value.trim().replace(/\s/g, "").replace(/^R\$/i, "");

  if (!compact) {
    return null;
  }

  const normalized = compact.includes(",")
    ? compact.replace(/\./g, "").replace(",", ".")
    : compact;

  const parsed = Number(normalized);

  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error("Informe um preço-alvo válido.");
  }

  return parsed;
}

function timestampValue(value: string | null): number {
  if (!value) {
    return 0;
  }

  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

export default function ProductDetailScreen() {
  const { snapshot } = useAuthSession();
  const params = useLocalSearchParams<{
    canonicalKey?: string | string[];
  }>();

  const canonicalKey = firstParam(params.canonicalKey);
  const authenticated = snapshot.status === "authenticated";
  const product = useProductDetail(canonicalKey);
  const history = useProductHistory(canonicalKey, 50);
  const watchlist = useWatchlist(authenticated);
  const upsertWatchlist = useUpsertWatchlist();
  const deleteWatchlist = useDeleteWatchlist();

  const currentWatchlistItem = useMemo(
    () =>
      watchlist.data?.items.find(
        (item) => item.canonicalKey === canonicalKey,
      ) ?? null,
    [canonicalKey, watchlist.data?.items],
  );

  const historyPoints = useMemo(
    () =>
      [...(history.data ?? [])].sort(
        (a, b) => timestampValue(b.timestamp) - timestampValue(a.timestamp),
      ),
    [history.data],
  );

  const historyLow = useMemo(() => {
    const prices = historyPoints
      .map((point) => point.price)
      .filter((price): price is number => price !== null);

    return prices.length > 0 ? Math.min(...prices) : null;
  }, [historyPoints]);

  const visibleHistory = historyPoints.slice(0, 12);

  const [targetPriceText, setTargetPriceText] = useState("");
  const [notifyPriceDrop, setNotifyPriceDrop] = useState(true);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);

  useEffect(() => {
    setTargetPriceText(
      currentWatchlistItem?.targetPrice === null ||
        currentWatchlistItem?.targetPrice === undefined
        ? ""
        : String(currentWatchlistItem.targetPrice),
    );

    setNotifyPriceDrop(currentWatchlistItem?.notifyPriceDrop ?? true);
  }, [
    canonicalKey,
    currentWatchlistItem?.notifyPriceDrop,
    currentWatchlistItem?.targetPrice,
  ]);

  if (snapshot.status !== "authenticated") {
    return <Redirect href="/" />;
  }

  if (!canonicalKey) {
    return (
      <View style={styles.centerState}>
        <Ionicons
          color={appTheme.colors.danger}
          name="alert-circle-outline"
          size={36}
        />
        <Text style={styles.stateTitle}>Produto inválido</Text>
        <Text style={styles.stateBody}>
          Não recebemos uma identificação válida para abrir este produto.
        </Text>
      </View>
    );
  }

  if (product.isPending) {
    return (
      <View style={styles.centerState}>
        <ActivityIndicator color={appTheme.colors.accent} size="large" />
        <Text style={styles.stateTitle}>Carregando produto</Text>
        <Text style={styles.stateBody}>
          Buscando preço, marketplace e histórico no Radar.
        </Text>
      </View>
    );
  }

  if (product.isError) {
    return (
      <View style={styles.centerState}>
        <Ionicons
          color={appTheme.colors.danger}
          name="cloud-offline-outline"
          size={38}
        />
        <Text style={styles.stateTitle}>Não foi possível carregar</Text>
        <Text style={styles.stateBody}>
          {product.error instanceof Error
            ? product.error.message
            : "Falha desconhecida."}
        </Text>
        <Pressable
          accessibilityRole="button"
          style={styles.retryButton}
          onPress={() => {
            void product.refetch();
          }}
        >
          <Ionicons
            color={appTheme.colors.accent}
            name="refresh"
            size={18}
          />
          <Text style={styles.retryButtonText}>Tentar novamente</Text>
        </Pressable>
      </View>
    );
  }

  const marketplace = product.data.marketplace?.trim() || "Marketplace";
  const currentPrice = product.data.currentPrice;
  const originalPrice = product.data.originalPrice;
  const discountPercent = product.data.discountPercent;
  const productUrl = product.data.productUrl;

  const hasOriginalPrice =
    currentPrice !== null &&
    originalPrice !== null &&
    originalPrice > currentPrice;

  const hasDiscount =
    discountPercent !== null && Number.isFinite(discountPercent) && discountPercent > 0;

  const isHistoricalLow =
    currentPrice !== null &&
    historyLow !== null &&
    currentPrice <= historyLow;

  const saveWatchlist = async (): Promise<void> => {
    setWatchlistError(null);

    try {
      const targetPrice = parseTargetPrice(targetPriceText);

      await upsertWatchlist.mutateAsync({
        canonicalKey,
        targetPrice,
        notifyPriceDrop,
      });

      Alert.alert(
        currentWatchlistItem ? "Acompanhamento atualizado" : "Produto acompanhado",
        targetPrice === null
          ? "O Radar vai acompanhar as próximas quedas de preço."
          : `Avisaremos quando o preço chegar a ${formatPrice(targetPrice)} ou menos.`,
      );
    } catch (caught) {
      setWatchlistError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível salvar o acompanhamento.",
      );
    }
  };

  const removeWatchlist = async (): Promise<void> => {
    setWatchlistError(null);

    try {
      await deleteWatchlist.mutateAsync(canonicalKey);
      setTargetPriceText("");
      setNotifyPriceDrop(true);

      Alert.alert(
        "Produto removido",
        "O Radar deixou de acompanhar este produto na sua Lista.",
      );
    } catch (caught) {
      setWatchlistError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível remover o produto.",
      );
    }
  };

  const openOffer = async (): Promise<void> => {
    if (!productUrl) {
      Alert.alert(
        "Link indisponível",
        "Ainda não há um link de compra disponível para esta oferta.",
      );
      return;
    }

    try {
      await Linking.openURL(productUrl);
    } catch {
      Alert.alert(
        "Não foi possível abrir",
        "O link da oferta não pôde ser aberto neste dispositivo.",
      );
    }
  };

  return (
    <ScrollView
      keyboardShouldPersistTaps="handled"
      style={styles.screen}
      contentContainerStyle={styles.container}
    >
      <View style={styles.hero}>
        <View style={styles.heroTopRow}>
          <View style={styles.marketplaceBadge}>
            <Ionicons
              color={appTheme.colors.accent}
              name="storefront-outline"
              size={15}
            />
            <Text style={styles.marketplaceText} numberOfLines={1}>
              {marketplace}
            </Text>
          </View>

          <View style={styles.verticalBadge}>
            <Text style={styles.verticalBadgeText}>
              {appTheme.vertical.label.toUpperCase()}
            </Text>
          </View>
        </View>

        <View style={styles.productVisual}>
          <View style={styles.productVisualRing}>
            <View style={styles.productVisualCore}>
              <Ionicons
                color={appTheme.colors.accent}
                name="pricetag-outline"
                size={42}
              />
            </View>
          </View>

          <Text style={styles.monitoringLabel}>
            PRODUTO MONITORADO PELO RADAR
          </Text>
        </View>

        <Text style={styles.title}>{product.data.title}</Text>

        <View style={styles.priceBlock}>
          <Text style={styles.priceLabel}>Melhor preço agora</Text>
          <Text style={styles.price}>{formatPrice(currentPrice)}</Text>

          <View style={styles.priceMetaRow}>
            {hasOriginalPrice ? (
              <Text style={styles.originalPrice}>
                De {formatPrice(originalPrice)}
              </Text>
            ) : null}

            {hasDiscount ? (
              <View style={styles.discountBadge}>
                <Text style={styles.discountBadgeText}>
                  -{Math.round(discountPercent)}%
                </Text>
              </View>
            ) : null}
          </View>
        </View>

        {isHistoricalLow ? (
          <View style={styles.priceSignal}>
            <Ionicons
              color={appTheme.colors.price}
              name="trophy-outline"
              size={18}
            />
            <View style={styles.priceSignalCopy}>
              <Text style={styles.priceSignalTitle}>
                Menor preço registrado
              </Text>
              <Text style={styles.priceSignalBody}>
                Este valor está no menor nível encontrado pelo Radar.
              </Text>
            </View>
          </View>
        ) : historyLow !== null ? (
          <View style={styles.priceSignalNeutral}>
            <Ionicons
              color={appTheme.colors.accent}
              name="stats-chart-outline"
              size={18}
            />
            <View style={styles.priceSignalCopy}>
              <Text style={styles.priceSignalNeutralTitle}>
                Histórico a partir de {formatPrice(historyLow)}
              </Text>
              <Text style={styles.priceSignalBody}>
                Compare o preço atual com os registros recentes abaixo.
              </Text>
            </View>
          </View>
        ) : null}

        <Pressable
          accessibilityRole="button"
          disabled={!productUrl}
          style={[
            styles.offerButton,
            !productUrl && styles.disabledButton,
          ]}
          onPress={() => {
            void openOffer();
          }}
        >
          <Ionicons
            color={appTheme.colors.background}
            name="open-outline"
            size={20}
          />
          <Text style={styles.offerButtonText}>
            {productUrl ? "Ver oferta" : "Link indisponível"}
          </Text>
        </Pressable>
      </View>

      <View style={styles.sectionCard}>
        <View style={styles.sectionHeadingRow}>
          <View style={styles.sectionIcon}>
            <Ionicons
              color={appTheme.colors.accent}
              name={currentWatchlistItem ? "heart" : "heart-outline"}
              size={20}
            />
          </View>

          <View style={styles.sectionHeadingCopy}>
            <Text style={styles.sectionTitle}>Acompanhar preço</Text>
            <Text style={styles.sectionSubtitle}>
              {currentWatchlistItem
                ? "Este produto já está na sua Lista."
                : "Coloque na Lista e deixe o Radar acompanhar por você."}
            </Text>
          </View>

          {currentWatchlistItem ? (
            <View style={styles.activeBadge}>
              <Text style={styles.activeBadgeText}>ATIVO</Text>
            </View>
          ) : null}
        </View>

        {watchlist.isPending ? (
          <View style={styles.inlineLoading}>
            <ActivityIndicator color={appTheme.colors.accent} />
            <Text style={styles.mutedText}>Carregando acompanhamento...</Text>
          </View>
        ) : (
          <>
            {watchlist.isError ? (
              <View style={styles.inlineError}>
                <Ionicons
                  color={appTheme.colors.danger}
                  name="alert-circle-outline"
                  size={18}
                />
                <Text style={styles.errorText}>
                  Não foi possível carregar sua Lista. Você ainda pode tentar
                  salvar novamente.
                </Text>
              </View>
            ) : null}

            <View style={styles.targetCard}>
              <View style={styles.targetCopy}>
                <Text style={styles.fieldLabel}>Preço-alvo</Text>
                <Text style={styles.fieldHint}>
                  Opcional. Ex.: 2499,90
                </Text>
              </View>

              <View style={styles.inputShell}>
                <Text style={styles.currencyPrefix}>R$</Text>
                <TextInput
                  keyboardType="decimal-pad"
                  placeholder="0,00"
                  placeholderTextColor={appTheme.colors.textSubtle}
                  style={styles.input}
                  value={targetPriceText}
                  onChangeText={setTargetPriceText}
                />
              </View>
            </View>

            <View style={styles.switchRow}>
              <View style={styles.switchIcon}>
                <Ionicons
                  color={appTheme.colors.accent}
                  name="notifications-outline"
                  size={20}
                />
              </View>

              <View style={styles.switchCopy}>
                <Text style={styles.fieldLabel}>Avisar quando cair</Text>
                <Text style={styles.fieldHint}>
                  Mantém este produto elegível para alertas de preço.
                </Text>
              </View>

              <Switch
                trackColor={{
                  false: appTheme.colors.border,
                  true: appTheme.colors.accentSoft,
                }}
                thumbColor={
                  notifyPriceDrop
                    ? appTheme.colors.accent
                    : appTheme.colors.textSubtle
                }
                value={notifyPriceDrop}
                onValueChange={setNotifyPriceDrop}
              />
            </View>

            {watchlistError ? (
              <View style={styles.inlineError}>
                <Ionicons
                  color={appTheme.colors.danger}
                  name="alert-circle-outline"
                  size={18}
                />
                <Text style={styles.errorText}>{watchlistError}</Text>
              </View>
            ) : null}

            <Pressable
              accessibilityRole="button"
              disabled={
                upsertWatchlist.isPending || deleteWatchlist.isPending
              }
              style={[
                styles.saveButton,
                (upsertWatchlist.isPending ||
                  deleteWatchlist.isPending) &&
                  styles.disabledButton,
              ]}
              onPress={() => {
                void saveWatchlist();
              }}
            >
              <Ionicons
                color={appTheme.colors.text}
                name={
                  currentWatchlistItem
                    ? "checkmark-circle-outline"
                    : "add-circle-outline"
                }
                size={20}
              />
              <Text style={styles.saveButtonText}>
                {upsertWatchlist.isPending
                  ? "Salvando..."
                  : currentWatchlistItem
                    ? "Atualizar acompanhamento"
                    : "Adicionar à Lista"}
              </Text>
            </Pressable>

            {currentWatchlistItem ? (
              <Pressable
                accessibilityRole="button"
                disabled={
                  deleteWatchlist.isPending || upsertWatchlist.isPending
                }
                style={styles.removeButton}
                onPress={() => {
                  void removeWatchlist();
                }}
              >
                <Ionicons
                  color={appTheme.colors.danger}
                  name="trash-outline"
                  size={17}
                />
                <Text style={styles.removeButtonText}>
                  {deleteWatchlist.isPending
                    ? "Removendo..."
                    : "Parar de acompanhar"}
                </Text>
              </Pressable>
            ) : null}
          </>
        )}
      </View>

      <View style={styles.sectionCard}>
        <View style={styles.sectionHeadingRow}>
          <View style={styles.sectionIcon}>
            <Ionicons
              color={appTheme.colors.accent}
              name="pulse-outline"
              size={20}
            />
          </View>

          <View style={styles.sectionHeadingCopy}>
            <Text style={styles.sectionTitle}>Histórico de preço</Text>
            <Text style={styles.sectionSubtitle}>
              Registros que o Radar encontrou para este produto.
            </Text>
          </View>
        </View>

        <View style={styles.metricsRow}>
          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>MENOR REGISTRADO</Text>
            <Text style={styles.metricValue}>
              {historyLow === null ? "—" : formatPrice(historyLow)}
            </Text>
          </View>

          <View style={styles.metricCard}>
            <Text style={styles.metricLabel}>REGISTROS</Text>
            <Text style={styles.metricValue}>
              {history.isPending ? "—" : String(historyPoints.length)}
            </Text>
          </View>
        </View>

        {history.isPending ? (
          <View style={styles.historyState}>
            <ActivityIndicator color={appTheme.colors.accent} />
            <Text style={styles.mutedText}>Carregando histórico...</Text>
          </View>
        ) : null}

        {history.isError ? (
          <View style={styles.historyState}>
            <Ionicons
              color={appTheme.colors.danger}
              name="alert-circle-outline"
              size={20}
            />
            <Text style={styles.errorText}>
              Não foi possível carregar o histórico agora.
            </Text>
          </View>
        ) : null}

        {!history.isPending &&
        !history.isError &&
        historyPoints.length === 0 ? (
          <View style={styles.emptyHistory}>
            <Ionicons
              color={appTheme.colors.textSubtle}
              name="time-outline"
              size={28}
            />
            <Text style={styles.emptyHistoryTitle}>Histórico começando</Text>
            <Text style={styles.mutedText}>
              Ainda não há registros suficientes para comparar preços.
            </Text>
          </View>
        ) : null}

        {visibleHistory.length > 0 ? (
          <View style={styles.historyList}>
            {visibleHistory.map((point, index) => (
              <View
                key={`${point.timestamp ?? "sem-data"}-${index}`}
                style={[
                  styles.historyRow,
                  index === visibleHistory.length - 1 &&
                    styles.historyRowLast,
                ]}
              >
                <View style={styles.historyMarkerColumn}>
                  <View
                    style={[
                      styles.historyDot,
                      index === 0 && styles.historyDotLatest,
                    ]}
                  />
                  {index !== visibleHistory.length - 1 ? (
                    <View style={styles.historyLine} />
                  ) : null}
                </View>

                <View style={styles.historyMain}>
                  <Text style={styles.historyPrice}>
                    {formatPrice(point.price)}
                  </Text>
                  <Text style={styles.historyMarketplace}>
                    {point.marketplace ?? "Marketplace não informado"}
                  </Text>
                </View>

                <View style={styles.historyDateWrap}>
                  {index === 0 ? (
                    <Text style={styles.latestLabel}>MAIS RECENTE</Text>
                  ) : null}
                  <Text style={styles.historyDate}>
                    {formatHistoryTimestamp(point.timestamp)}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        ) : null}

        {historyPoints.length > visibleHistory.length ? (
          <Text style={styles.historyFooter}>
            Mostrando os {visibleHistory.length} registros mais recentes de{" "}
            {historyPoints.length}.
          </Text>
        ) : null}
      </View>

      <View style={styles.radarNote}>
        <Ionicons
          color={appTheme.colors.textMuted}
          name="information-circle-outline"
          size={19}
        />
        <Text style={styles.radarNoteText}>
          Preços e disponibilidade podem mudar no marketplace. Confirme os
          dados na página da oferta antes da compra.
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: appTheme.colors.background,
  },
  container: {
    padding: appTheme.spacing.lg,
    paddingBottom: appTheme.spacing.xxxl,
    gap: appTheme.spacing.lg,
  },
  centerState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: appTheme.spacing.md,
    padding: appTheme.spacing.xxl,
    backgroundColor: appTheme.colors.background,
  },
  stateTitle: {
    color: appTheme.colors.text,
    fontSize: 22,
    fontWeight: "900",
    textAlign: "center",
  },
  stateBody: {
    color: appTheme.colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
  retryButton: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: appTheme.spacing.sm,
    marginTop: appTheme.spacing.sm,
    paddingHorizontal: appTheme.spacing.lg,
    borderWidth: 1,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surface,
  },
  retryButtonText: {
    color: appTheme.colors.accent,
    fontSize: 14,
    fontWeight: "800",
  },
  hero: {
    gap: appTheme.spacing.lg,
    padding: appTheme.spacing.xl,
    borderWidth: 1,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.xl,
    backgroundColor: appTheme.colors.surface,
  },
  heroTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: appTheme.spacing.md,
  },
  marketplaceBadge: {
    maxWidth: "72%",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.accentSoft,
  },
  marketplaceText: {
    flexShrink: 1,
    color: appTheme.colors.accent,
    fontSize: 12,
    fontWeight: "800",
  },
  verticalBadge: {
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.pill,
  },
  verticalBadgeText: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1,
  },
  productVisual: {
    minHeight: 162,
    alignItems: "center",
    justifyContent: "center",
    gap: appTheme.spacing.md,
    overflow: "hidden",
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.accentSoft,
  },
  productVisualRing: {
    width: 102,
    height: 102,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: 51,
  },
  productVisualCore: {
    width: 72,
    height: 72,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 36,
    backgroundColor: appTheme.colors.surface,
  },
  monitoringLabel: {
    color: appTheme.colors.textSubtle,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.3,
  },
  title: {
    color: appTheme.colors.text,
    fontSize: 25,
    lineHeight: 32,
    fontWeight: "900",
  },
  priceBlock: {
    gap: 4,
  },
  priceLabel: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    fontWeight: "700",
  },
  price: {
    color: appTheme.colors.price,
    fontSize: 36,
    lineHeight: 42,
    fontWeight: "900",
    letterSpacing: -0.8,
  },
  priceMetaRow: {
    minHeight: 24,
    flexDirection: "row",
    alignItems: "center",
    gap: appTheme.spacing.sm,
  },
  originalPrice: {
    color: appTheme.colors.textSubtle,
    fontSize: 13,
    textDecorationLine: "line-through",
  },
  discountBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.successSurface,
  },
  discountBadgeText: {
    color: appTheme.colors.success,
    fontSize: 11,
    fontWeight: "900",
  },
  priceSignal: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: appTheme.spacing.sm,
    padding: appTheme.spacing.md,
    borderWidth: 1,
    borderColor: appTheme.colors.price,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.successSurface,
  },
  priceSignalNeutral: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: appTheme.spacing.sm,
    padding: appTheme.spacing.md,
    borderWidth: 1,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceSoft,
  },
  priceSignalCopy: {
    flex: 1,
    gap: 2,
  },
  priceSignalTitle: {
    color: appTheme.colors.price,
    fontSize: 13,
    fontWeight: "900",
  },
  priceSignalNeutralTitle: {
    color: appTheme.colors.accent,
    fontSize: 13,
    fontWeight: "900",
  },
  priceSignalBody: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
    lineHeight: 16,
  },
  offerButton: {
    minHeight: 54,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: appTheme.spacing.sm,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accent,
  },
  offerButtonText: {
    color: appTheme.colors.background,
    fontSize: 15,
    fontWeight: "900",
  },
  sectionCard: {
    gap: appTheme.spacing.lg,
    padding: appTheme.spacing.lg,
    borderWidth: 1,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
  },
  sectionHeadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: appTheme.spacing.md,
  },
  sectionIcon: {
    width: 42,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accentSoft,
  },
  sectionHeadingCopy: {
    flex: 1,
    gap: 2,
  },
  sectionTitle: {
    color: appTheme.colors.text,
    fontSize: 18,
    fontWeight: "900",
  },
  sectionSubtitle: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 17,
  },
  activeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.successSurface,
  },
  activeBadgeText: {
    color: appTheme.colors.success,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.8,
  },
  inlineLoading: {
    flexDirection: "row",
    alignItems: "center",
    gap: appTheme.spacing.sm,
  },
  mutedText: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
  },
  targetCard: {
    gap: appTheme.spacing.md,
    padding: appTheme.spacing.md,
    borderWidth: 1,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
  },
  targetCopy: {
    gap: 2,
  },
  fieldLabel: {
    color: appTheme.colors.text,
    fontSize: 13,
    fontWeight: "800",
  },
  fieldHint: {
    color: appTheme.colors.textSubtle,
    fontSize: 11,
    lineHeight: 16,
  },
  inputShell: {
    minHeight: 50,
    flexDirection: "row",
    alignItems: "center",
    overflow: "hidden",
    borderWidth: 1,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surface,
  },
  currencyPrefix: {
    paddingLeft: appTheme.spacing.md,
    color: appTheme.colors.textMuted,
    fontSize: 15,
    fontWeight: "800",
  },
  input: {
    flex: 1,
    minHeight: 48,
    paddingHorizontal: appTheme.spacing.sm,
    color: appTheme.colors.text,
    fontSize: 16,
    fontWeight: "800",
  },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: appTheme.spacing.md,
    padding: appTheme.spacing.md,
    borderWidth: 1,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
  },
  switchIcon: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 18,
    backgroundColor: appTheme.colors.accentSoft,
  },
  switchCopy: {
    flex: 1,
    gap: 2,
  },
  inlineError: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: appTheme.spacing.sm,
    padding: appTheme.spacing.md,
    borderWidth: 1,
    borderColor: appTheme.colors.dangerBorder,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.dangerSurface,
  },
  errorText: {
    flex: 1,
    color: appTheme.colors.danger,
    fontSize: 12,
    lineHeight: 18,
  },
  saveButton: {
    minHeight: 50,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: appTheme.spacing.sm,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  saveButtonText: {
    color: appTheme.colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  removeButton: {
    minHeight: 42,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
  },
  removeButtonText: {
    color: appTheme.colors.danger,
    fontSize: 12,
    fontWeight: "800",
  },
  metricsRow: {
    flexDirection: "row",
    gap: appTheme.spacing.sm,
  },
  metricCard: {
    flex: 1,
    minHeight: 78,
    justifyContent: "center",
    gap: 5,
    padding: appTheme.spacing.md,
    borderWidth: 1,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
  },
  metricLabel: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 0.8,
  },
  metricValue: {
    color: appTheme.colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  historyState: {
    flexDirection: "row",
    alignItems: "center",
    gap: appTheme.spacing.sm,
    paddingVertical: appTheme.spacing.sm,
  },
  emptyHistory: {
    alignItems: "center",
    gap: appTheme.spacing.sm,
    paddingVertical: appTheme.spacing.xl,
  },
  emptyHistoryTitle: {
    color: appTheme.colors.text,
    fontSize: 15,
    fontWeight: "800",
  },
  historyList: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.background,
  },
  historyRow: {
    minHeight: 70,
    flexDirection: "row",
    alignItems: "stretch",
    paddingHorizontal: appTheme.spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: appTheme.colors.border,
  },
  historyRowLast: {
    borderBottomWidth: 0,
  },
  historyMarkerColumn: {
    width: 18,
    alignItems: "center",
    paddingTop: 21,
  },
  historyDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: appTheme.colors.borderStrong,
  },
  historyDotLatest: {
    backgroundColor: appTheme.colors.price,
  },
  historyLine: {
    width: 1,
    flex: 1,
    marginTop: 3,
    backgroundColor: appTheme.colors.border,
  },
  historyMain: {
    flex: 1,
    justifyContent: "center",
    gap: 3,
    paddingVertical: appTheme.spacing.sm,
    paddingLeft: appTheme.spacing.sm,
  },
  historyPrice: {
    color: appTheme.colors.text,
    fontSize: 15,
    fontWeight: "900",
  },
  historyMarketplace: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
  },
  historyDateWrap: {
    maxWidth: 110,
    alignItems: "flex-end",
    justifyContent: "center",
    gap: 4,
    paddingVertical: appTheme.spacing.sm,
  },
  latestLabel: {
    color: appTheme.colors.price,
    fontSize: 8,
    fontWeight: "900",
    letterSpacing: 0.7,
  },
  historyDate: {
    color: appTheme.colors.textSubtle,
    fontSize: 10,
    lineHeight: 14,
    textAlign: "right",
  },
  historyFooter: {
    color: appTheme.colors.textSubtle,
    fontSize: 10,
    lineHeight: 15,
    textAlign: "center",
  },
  radarNote: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: appTheme.spacing.sm,
    paddingHorizontal: appTheme.spacing.sm,
  },
  radarNoteText: {
    flex: 1,
    color: appTheme.colors.textSubtle,
    fontSize: 10,
    lineHeight: 15,
  },
  disabledButton: {
    opacity: 0.45,
  },
});
