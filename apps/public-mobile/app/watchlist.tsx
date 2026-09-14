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

import { useAuthSession } from "@/src/auth";
import { formatPrice } from "@/src/offers";
import {
  WatchlistItem,
  useWatchlist,
} from "@/src/watchlist";

export default function WatchlistScreen() {
  const { snapshot } = useAuthSession();
  const authenticated = snapshot.status === "authenticated";
  const watchlist = useWatchlist(authenticated);

  if (snapshot.status === "restoring") {
    return (
      <View style={styles.centerState}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!authenticated) {
    return <Redirect href="/" />;
  }

  if (watchlist.isPending) {
    return (
      <View style={styles.centerState}>
        <ActivityIndicator size="large" />
        <Text style={styles.body}>Carregando watchlist...</Text>
      </View>
    );
  }

  if (watchlist.isError) {
    return (
      <View style={styles.centerState}>
        <Text style={styles.stateTitle}>
          Não foi possível carregar sua watchlist
        </Text>
        <Text style={styles.body}>
          {watchlist.error instanceof Error
            ? watchlist.error.message
            : "Falha desconhecida."}
        </Text>

        <Pressable
          accessibilityRole="button"
          style={styles.primaryButton}
          onPress={() => {
            void watchlist.refetch();
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
      data={[...(watchlist.data?.items ?? [])]}
      keyExtractor={(item) => item.canonicalKey}
      contentContainerStyle={[
        styles.listContent,
        (watchlist.data?.items.length ?? 0) === 0 &&
          styles.emptyListContent,
      ]}
      refreshControl={
        <RefreshControl
          refreshing={watchlist.isRefetching}
          onRefresh={() => {
            void watchlist.refetch();
          }}
        />
      }
      ListHeaderComponent={
        <View style={styles.header}>
          <Text style={styles.eyebrow}>ACOMPANHAMENTO</Text>
          <Text style={styles.title}>Minha watchlist</Text>
          <Text style={styles.bodyLeft}>
            Produtos que você quer acompanhar por queda de preço
            ou preço-alvo.
          </Text>
        </View>
      }
      ListEmptyComponent={
        <View style={styles.centerState}>
          <Text style={styles.stateTitle}>
            Sua watchlist está vazia
          </Text>
          <Text style={styles.body}>
            Abra um produto e escolha “Acompanhar produto”.
          </Text>

          <Pressable
            accessibilityRole="button"
            style={styles.primaryButton}
            onPress={() => router.replace("/home")}
          >
            <Text style={styles.primaryButtonText}>
              Ver produtos
            </Text>
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
  );
}

function WatchlistCard({
  item,
  onPress,
}: Readonly<{
  item: WatchlistItem;
  onPress: () => void;
}>) {
  return (
    <Pressable
      accessibilityRole="button"
      style={styles.card}
      onPress={onPress}
    >
      <Text style={styles.cardTitle} numberOfLines={2}>
        {item.canonicalKey}
      </Text>

      <View style={styles.cardRow}>
        <View>
          <Text style={styles.metaLabel}>PREÇO-ALVO</Text>
          <Text style={styles.cardValue}>
            {item.targetPrice === null
              ? "Sem preço-alvo"
              : formatPrice(item.targetPrice)}
          </Text>
        </View>

        <View style={styles.rightMeta}>
          <Text style={styles.metaLabel}>QUEDA DE PREÇO</Text>
          <Text style={styles.cardValue}>
            {item.notifyPriceDrop ? "Ativa" : "Desativada"}
          </Text>
        </View>
      </View>

      <Text style={styles.openLabel}>Abrir produto →</Text>
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
    gap: 14,
  },
  cardTitle: {
    fontSize: 15,
    lineHeight: 21,
    fontWeight: "700",
  },
  cardRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 16,
  },
  rightMeta: {
    alignItems: "flex-end",
  },
  metaLabel: {
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 0.8,
    opacity: 0.5,
  },
  cardValue: {
    marginTop: 3,
    fontSize: 14,
    fontWeight: "700",
  },
  openLabel: {
    fontSize: 12,
    fontWeight: "700",
    alignSelf: "flex-end",
  },
});
