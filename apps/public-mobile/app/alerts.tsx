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

import {
  AlertCard,
  formatAlertTimestamp,
  useAlertList,
} from "@/src/alerts";
import { useAuthSession } from "@/src/auth";
import { formatPrice } from "@/src/offers";

export default function AlertsScreen() {
  const { snapshot } = useAuthSession();
  const alerts = useAlertList(100, 0);

  if (snapshot.status === "restoring") {
    return (
      <View style={styles.centerState}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (snapshot.status !== "authenticated") {
    return <Redirect href="/" />;
  }

  if (alerts.isPending) {
    return (
      <View style={styles.centerState}>
        <ActivityIndicator size="large" />
        <Text style={styles.body}>Carregando alertas...</Text>
      </View>
    );
  }

  if (alerts.isError) {
    return (
      <View style={styles.centerState}>
        <Text style={styles.stateTitle}>
          Não foi possível carregar os alertas
        </Text>

        <Text style={styles.body}>
          {alerts.error instanceof Error
            ? alerts.error.message
            : "Falha desconhecida."}
        </Text>

        <Pressable
          accessibilityRole="button"
          style={styles.primaryButton}
          onPress={() => {
            void alerts.refetch();
          }}
        >
          <Text style={styles.primaryButtonText}>
            Tentar novamente
          </Text>
        </Pressable>
      </View>
    );
  }

  return (
    <FlatList
      data={[...(alerts.data?.items ?? [])]}
      keyExtractor={(item) => item.id}
      contentContainerStyle={[
        styles.listContent,
        (alerts.data?.items.length ?? 0) === 0 &&
          styles.emptyListContent,
      ]}
      refreshControl={
        <RefreshControl
          refreshing={alerts.isRefetching}
          onRefresh={() => {
            void alerts.refetch();
          }}
        />
      }
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.eyebrow}>ALERT ENGINE</Text>
          <Text style={styles.title}>Alertas recentes</Text>
          <Text style={styles.bodyLeft}>
            Eventos detectados pelo backend. Esta tela ainda não é o
            Personalized Feed nem o Push Dispatcher.
          </Text>
        </View>
      }
      ListEmptyComponent={
        <View style={styles.centerState}>
          <Text style={styles.stateTitle}>
            Nenhum alerta encontrado
          </Text>
          <Text style={styles.body}>
            O backend respondeu normalmente, mas ainda não há alertas.
          </Text>
        </View>
      }
      renderItem={({ item }) => (
        <AlertCardView item={item} />
      )}
    />
  );
}

function AlertCardView({
  item,
}: Readonly<{
  item: AlertCard;
}>) {
  const canOpenProduct = Boolean(item.canonicalKey);

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

  return (
    <Pressable
      accessibilityRole={canOpenProduct ? "button" : undefined}
      disabled={!canOpenProduct}
      style={styles.card}
      onPress={openProduct}
    >
      <View style={styles.cardTopRow}>
        <View style={styles.cardCopy}>
          <Text style={styles.cardTitle}>{item.title}</Text>

          {item.marketplace ? (
            <Text style={styles.meta}>{item.marketplace}</Text>
          ) : null}
        </View>

        <Text style={styles.date}>
          {formatAlertTimestamp(item.occurredAt)}
        </Text>
      </View>

      {item.message ? (
        <Text style={styles.message}>{item.message}</Text>
      ) : null}

      {item.currentPrice !== null ||
      item.previousPrice !== null ? (
        <View style={styles.priceRow}>
          {item.previousPrice !== null ? (
            <View style={styles.priceBlock}>
              <Text style={styles.priceLabel}>ANTES</Text>
              <Text style={styles.previousPrice}>
                {formatPrice(item.previousPrice)}
              </Text>
            </View>
          ) : null}

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

      {item.canonicalKey ? (
        <View style={styles.productRow}>
          <Text style={styles.productKey} numberOfLines={1}>
            {item.canonicalKey}
          </Text>
          <Text style={styles.openLabel}>Abrir produto →</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  listContent: {
    padding: 16,
    paddingBottom: 32,
    gap: 12,
  },
  emptyListContent: {
    flexGrow: 1,
  },
  header: {
    gap: 6,
    marginBottom: 10,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    opacity: 0.55,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    opacity: 0.7,
    textAlign: "center",
  },
  bodyLeft: {
    fontSize: 15,
    lineHeight: 22,
    opacity: 0.7,
  },
  centerState: {
    flex: 1,
    minHeight: 280,
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
    padding: 24,
  },
  stateTitle: {
    fontSize: 20,
    fontWeight: "800",
    textAlign: "center",
  },
  primaryButton: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: "#111111",
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 18,
    padding: 16,
    gap: 12,
  },
  cardTopRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
  },
  cardCopy: {
    flex: 1,
    gap: 3,
  },
  cardTitle: {
    fontSize: 17,
    lineHeight: 22,
    fontWeight: "800",
  },
  meta: {
    fontSize: 12,
    opacity: 0.55,
  },
  date: {
    maxWidth: 120,
    fontSize: 11,
    lineHeight: 16,
    opacity: 0.55,
    textAlign: "right",
  },
  message: {
    fontSize: 14,
    lineHeight: 21,
    opacity: 0.78,
  },
  priceRow: {
    flexDirection: "row",
    gap: 28,
  },
  priceBlock: {
    gap: 3,
  },
  priceLabel: {
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.8,
    opacity: 0.5,
  },
  previousPrice: {
    fontSize: 15,
    textDecorationLine: "line-through",
    opacity: 0.55,
  },
  currentPrice: {
    fontSize: 19,
    fontWeight: "900",
  },
  productRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    paddingTop: 10,
  },
  productKey: {
    flex: 1,
    fontSize: 11,
    opacity: 0.55,
  },
  openLabel: {
    fontSize: 12,
    fontWeight: "700",
  },
});
