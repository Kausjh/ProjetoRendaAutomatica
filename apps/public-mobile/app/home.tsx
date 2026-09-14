import { Redirect, router } from "expo-router";
import { useState } from "react";
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

import { useAuthSession } from "@/src/auth";
import {
  ProductCard,
  formatPrice,
  useProductList,
} from "@/src/offers";

export default function HomeScreen() {
  const { logout, snapshot } = useAuthSession();
  const [loggingOut, setLoggingOut] = useState(false);
  const products = useProductList(50, 0);

  if (snapshot.status === "restoring") {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (snapshot.status !== "authenticated") {
    return <Redirect href="/" />;
  }

  const performLogout = async (): Promise<void> => {
    setLoggingOut(true);

    try {
      await logout();
    } catch {
      Alert.alert(
        "Sessão local encerrada",
        "O servidor não confirmou a revogação, mas este aparelho já foi desconectado.",
      );
    } finally {
      setLoggingOut(false);
      router.replace("/");
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerCopy}>
          <Text style={styles.eyebrow}>OFERTAS</Text>
          <Text style={styles.title}>Produtos monitorados</Text>
        </View>

        <View style={styles.headerActions}>
          <Pressable
            accessibilityRole="button"
            style={styles.compactButton}
            onPress={() => router.push("/watchlist")}
          >
            <Text style={styles.compactButtonText}>Watchlist</Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            style={styles.compactButton}
            onPress={() => router.push("/connection")}
          >
            <Text style={styles.compactButtonText}>Conexão</Text>
          </Pressable>
        </View>
      </View>

      {products.isPending ? (
        <View style={styles.centerState}>
          <ActivityIndicator size="large" />
          <Text style={styles.body}>Carregando produtos...</Text>
        </View>
      ) : null}

      {products.isError ? (
        <View style={styles.centerState}>
          <Text style={styles.stateTitle}>
            Não foi possível carregar os produtos
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
          contentContainerStyle={[
            styles.listContent,
            products.data.items.length === 0 &&
              styles.emptyListContent,
          ]}
          refreshControl={
            <RefreshControl
              refreshing={products.isRefetching}
              onRefresh={() => {
                void products.refetch();
              }}
            />
          }
          ListEmptyComponent={
            <View style={styles.centerState}>
              <Text style={styles.stateTitle}>
                Nenhum produto encontrado
              </Text>
              <Text style={styles.body}>
                A API respondeu normalmente, mas não retornou produtos.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <ProductCardView
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
          ListFooterComponent={
            <Pressable
              accessibilityRole="button"
              disabled={loggingOut}
              style={[
                styles.logoutButton,
                loggingOut && styles.disabledButton,
              ]}
              onPress={() => {
                void performLogout();
              }}
            >
              <Text style={styles.logoutButtonText}>
                {loggingOut ? "Saindo..." : "Sair da conta"}
              </Text>
            </Pressable>
          }
        />
      ) : null}
    </View>
  );
}

function ProductCardView({
  item,
  onPress,
}: Readonly<{
  item: ProductCard;
  onPress: () => void;
}>) {
  return (
    <Pressable
      accessibilityRole="button"
      style={styles.card}
      onPress={onPress}
    >
      <View style={styles.cardTopRow}>
        <Text style={styles.cardTitle} numberOfLines={2}>
          {item.title}
        </Text>

        {item.discountPercent !== null ? (
          <Text style={styles.discount}>
            -{Math.round(item.discountPercent)}%
          </Text>
        ) : null}
      </View>

      <Text style={styles.price}>
        {formatPrice(item.currentPrice)}
      </Text>

      {item.originalPrice !== null ? (
        <Text style={styles.originalPrice}>
          De {formatPrice(item.originalPrice)}
        </Text>
      ) : null}

      <View style={styles.metaRow}>
        <Text style={styles.meta}>
          {item.marketplace ?? "Marketplace não informado"}
        </Text>
        <Text style={styles.openLabel}>Ver detalhes →</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 18,
    paddingBottom: 12,
    gap: 12,
  },
  headerCopy: {
    gap: 4,
  },
  headerActions: {
    flexDirection: "row",
    gap: 8,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    opacity: 0.55,
  },
  title: {
    fontSize: 27,
    fontWeight: "800",
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    opacity: 0.7,
    textAlign: "center",
  },
  compactButton: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  compactButtonText: {
    fontSize: 13,
    fontWeight: "700",
  },
  centerState: {
    flex: 1,
    minHeight: 250,
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
  listContent: {
    padding: 16,
    gap: 12,
    paddingBottom: 32,
  },
  emptyListContent: {
    flexGrow: 1,
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 18,
    padding: 16,
    gap: 8,
  },
  cardTopRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
  },
  cardTitle: {
    flex: 1,
    fontSize: 17,
    lineHeight: 22,
    fontWeight: "700",
  },
  discount: {
    fontSize: 13,
    fontWeight: "800",
  },
  price: {
    fontSize: 24,
    fontWeight: "900",
  },
  originalPrice: {
    fontSize: 13,
    textDecorationLine: "line-through",
    opacity: 0.5,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
    marginTop: 4,
  },
  meta: {
    flex: 1,
    fontSize: 12,
    opacity: 0.6,
  },
  openLabel: {
    fontSize: 12,
    fontWeight: "700",
  },
  logoutButton: {
    minHeight: 50,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    marginTop: 12,
  },
  logoutButtonText: {
    fontSize: 15,
    fontWeight: "700",
  },
  disabledButton: {
    opacity: 0.5,
  },
});
