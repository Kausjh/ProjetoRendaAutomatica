import { Redirect, useLocalSearchParams } from "expo-router";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useAuthSession } from "@/src/auth";
import {
  formatHistoryTimestamp,
  formatPrice,
  useProductDetail,
  useProductHistory,
} from "@/src/offers";

function firstParam(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

export default function ProductDetailScreen() {
  const { snapshot } = useAuthSession();
  const params = useLocalSearchParams<{
    canonicalKey?: string | string[];
  }>();

  const canonicalKey = firstParam(params.canonicalKey);
  const product = useProductDetail(canonicalKey);
  const history = useProductHistory(canonicalKey, 50);

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
    gap: 10,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "800",
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
