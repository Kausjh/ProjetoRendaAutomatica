import { Redirect, useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
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
import {
  useDeleteWatchlist,
  useUpsertWatchlist,
  useWatchlist,
} from "@/src/watchlist";

function firstParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function parseTargetPrice(value: string): number | null {
  const normalized = value.trim();

  if (!normalized) {
    return null;
  }

  const parsed = Number(
    normalized
      .replace(/\s/g, "")
      .replace(/^R\$/i, "")
      .replace(",", "."),
  );

  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error("Informe um preço-alvo válido.");
  }

  return parsed;
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

  const [targetPriceText, setTargetPriceText] = useState("");
  const [notifyPriceDrop, setNotifyPriceDrop] = useState(true);
  const [watchlistError, setWatchlistError] =
    useState<string | null>(null);

  useEffect(() => {
    setTargetPriceText(
      currentWatchlistItem?.targetPrice === null ||
        currentWatchlistItem?.targetPrice === undefined
        ? ""
        : String(currentWatchlistItem.targetPrice),
    );

    setNotifyPriceDrop(
      currentWatchlistItem?.notifyPriceDrop ?? true,
    );
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
        <Text style={styles.stateTitle}>Produto inválido</Text>
      </View>
    );
  }

  if (product.isPending) {
    return (
      <View style={styles.centerState}>
        <ActivityIndicator size="large" />
        <Text style={styles.body}>Carregando produto...</Text>
      </View>
    );
  }

  if (product.isError) {
    return (
      <View style={styles.centerState}>
        <Text style={styles.stateTitle}>
          Não foi possível carregar o produto
        </Text>
        <Text style={styles.body}>
          {product.error instanceof Error
            ? product.error.message
            : "Falha desconhecida."}
        </Text>
      </View>
    );
  }

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
        currentWatchlistItem ? "Watchlist atualizada" : "Produto acompanhado",
        "As configurações de acompanhamento foram salvas.",
      );
    } catch (caught) {
      setWatchlistError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível salvar a watchlist.",
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
        "O produto saiu da sua watchlist.",
      );
    } catch (caught) {
      setWatchlistError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível remover o produto.",
      );
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.eyebrow}>
        {product.data.marketplace ?? "PRODUTO"}
      </Text>

      <Text style={styles.title}>{product.data.title}</Text>

      <Text style={styles.price}>
        {formatPrice(product.data.currentPrice)}
      </Text>

      {product.data.originalPrice !== null ? (
        <Text style={styles.originalPrice}>
          De {formatPrice(product.data.originalPrice)}
        </Text>
      ) : null}

      {product.data.discountPercent !== null ? (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>
            {Math.round(product.data.discountPercent)}% de desconto
          </Text>
        </View>
      ) : null}

      <View style={styles.keyCard}>
        <Text style={styles.keyLabel}>CHAVE CANÔNICA</Text>
        <Text selectable style={styles.keyValue}>
          {product.data.canonicalKey}
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Acompanhar produto</Text>
        <Text style={styles.body}>
          Defina um preço-alvo opcional e escolha se quer acompanhar
          quedas de preço.
        </Text>

        {watchlist.isPending ? (
          <ActivityIndicator />
        ) : (
          <>
            <View style={styles.field}>
              <Text style={styles.fieldLabel}>Preço-alvo</Text>
              <TextInput
                keyboardType="decimal-pad"
                placeholder="Ex.: 999,90"
                style={styles.input}
                value={targetPriceText}
                onChangeText={setTargetPriceText}
              />
            </View>

            <View style={styles.switchRow}>
              <View style={styles.switchCopy}>
                <Text style={styles.fieldLabel}>
                  Notificar queda de preço
                </Text>
                <Text style={styles.bodySmall}>
                  Mantém o produto elegível para alertas de queda.
                </Text>
              </View>

              <Switch
                value={notifyPriceDrop}
                onValueChange={setNotifyPriceDrop}
              />
            </View>

            {watchlistError ? (
              <Text style={styles.error}>{watchlistError}</Text>
            ) : null}

            <Pressable
              accessibilityRole="button"
              disabled={
                upsertWatchlist.isPending ||
                deleteWatchlist.isPending
              }
              style={[
                styles.primaryButton,
                (upsertWatchlist.isPending ||
                  deleteWatchlist.isPending) &&
                  styles.disabledButton,
              ]}
              onPress={() => {
                void saveWatchlist();
              }}
            >
              <Text style={styles.primaryButtonText}>
                {upsertWatchlist.isPending
                  ? "Salvando..."
                  : currentWatchlistItem
                    ? "Atualizar acompanhamento"
                    : "Acompanhar produto"}
              </Text>
            </Pressable>

            {currentWatchlistItem ? (
              <Pressable
                accessibilityRole="button"
                disabled={
                  deleteWatchlist.isPending ||
                  upsertWatchlist.isPending
                }
                style={styles.secondaryButton}
                onPress={() => {
                  void removeWatchlist();
                }}
              >
                <Text style={styles.secondaryButtonText}>
                  {deleteWatchlist.isPending
                    ? "Removendo..."
                    : "Remover da watchlist"}
                </Text>
              </Pressable>
            ) : null}
          </>
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Histórico de preço</Text>

        {history.isPending ? (
          <ActivityIndicator />
        ) : null}

        {history.isError ? (
          <Text style={styles.body}>
            Não foi possível carregar o histórico.
          </Text>
        ) : null}

        {history.data?.length === 0 ? (
          <Text style={styles.body}>
            Nenhum registro histórico disponível.
          </Text>
        ) : null}

        {history.data?.map((point, index) => (
          <View
            key={`${point.timestamp ?? "sem-data"}-${index}`}
            style={styles.historyRow}
          >
            <View style={styles.historyCopy}>
              <Text style={styles.historyPrice}>
                {formatPrice(point.price)}
              </Text>
              <Text style={styles.historyMeta}>
                {point.marketplace ?? "Marketplace não informado"}
              </Text>
            </View>

            <Text style={styles.historyDate}>
              {formatHistoryTimestamp(point.timestamp)}
            </Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingBottom: 40,
    gap: 14,
  },
  centerState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
    padding: 24,
  },
  stateTitle: {
    fontSize: 21,
    fontWeight: "800",
    textAlign: "center",
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    opacity: 0.55,
  },
  title: {
    fontSize: 27,
    lineHeight: 34,
    fontWeight: "800",
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    opacity: 0.7,
  },
  bodySmall: {
    fontSize: 12,
    lineHeight: 18,
    opacity: 0.6,
  },
  price: {
    fontSize: 32,
    fontWeight: "900",
  },
  originalPrice: {
    fontSize: 14,
    textDecorationLine: "line-through",
    opacity: 0.5,
  },
  badge: {
    alignSelf: "flex-start",
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  badgeText: {
    fontSize: 13,
    fontWeight: "800",
  },
  keyCard: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 16,
    padding: 14,
    gap: 6,
  },
  keyLabel: {
    fontSize: 11,
    fontWeight: "700",
    opacity: 0.55,
  },
  keyValue: {
    fontSize: 13,
    lineHeight: 19,
  },
  section: {
    marginTop: 10,
    gap: 12,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "800",
  },
  field: {
    gap: 7,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: "700",
  },
  input: {
    minHeight: 50,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 14,
    paddingHorizontal: 14,
    fontSize: 16,
  },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
  },
  switchCopy: {
    flex: 1,
    gap: 3,
  },
  error: {
    fontSize: 14,
    lineHeight: 20,
  },
  primaryButton: {
    minHeight: 50,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: "#111111",
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
  },
  secondaryButton: {
    minHeight: 50,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 18,
  },
  secondaryButtonText: {
    fontSize: 15,
    fontWeight: "700",
  },
  disabledButton: {
    opacity: 0.5,
  },
  historyRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    paddingVertical: 12,
  },
  historyCopy: {
    flex: 1,
    gap: 3,
  },
  historyPrice: {
    fontSize: 16,
    fontWeight: "800",
  },
  historyMeta: {
    fontSize: 12,
    opacity: 0.55,
  },
  historyDate: {
    fontSize: 12,
    opacity: 0.6,
    textAlign: "right",
  },
});
