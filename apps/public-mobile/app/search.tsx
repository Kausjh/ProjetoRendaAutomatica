import { Ionicons } from "@expo/vector-icons";
import { Redirect, router } from "expo-router";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
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

function normalizeSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export default function SearchScreen() {
  const { snapshot } = useAuthSession();
  const [query, setQuery] = useState("");
  const products = useProductList(100, 0);

  const normalizedQuery = normalizeSearch(query);

  const filteredProducts = useMemo(() => {
    if (!products.data) {
      return [];
    }

    if (!normalizedQuery) {
      return [...products.data.items];
    }

    return products.data.items.filter((item) => {
      const haystack = normalizeSearch(
        [
          item.title,
          item.canonicalKey,
          item.marketplace ?? "",
        ].join(" "),
      );

      return haystack.includes(normalizedQuery);
    });
  }, [normalizedQuery, products.data]);

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

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <View style={styles.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Voltar"
          style={styles.iconButton}
          onPress={() => router.back()}
        >
          <Ionicons
            name="arrow-back"
            size={22}
            color={appTheme.colors.text}
          />
        </Pressable>

        <View style={styles.headerCopy}>
          <Text style={styles.eyebrow}>RADAR DE OFERTAS</Text>
          <Text style={styles.title}>Buscar</Text>
        </View>
      </View>

      <View style={styles.searchBox}>
        <Ionicons
          name="search"
          size={20}
          color={appTheme.colors.textMuted}
        />

        <TextInput
          autoFocus
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="Produto, modelo ou marketplace"
          placeholderTextColor={appTheme.colors.textSubtle}
          selectionColor={appTheme.colors.accent}
          style={styles.input}
          value={query}
          onChangeText={setQuery}
        />

        {query ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Limpar busca"
            style={styles.clearButton}
            onPress={() => setQuery("")}
          >
            <Ionicons
              name="close-circle"
              size={20}
              color={appTheme.colors.textMuted}
            />
          </Pressable>
        ) : null}
      </View>

      {products.isPending ? (
        <View style={styles.state}>
          <ActivityIndicator
            size="large"
            color={appTheme.colors.accent}
          />
          <Text style={styles.stateBody}>Carregando produtos...</Text>
        </View>
      ) : null}

      {products.isError ? (
        <View style={styles.state}>
          <Ionicons
            name="cloud-offline-outline"
            size={30}
            color={appTheme.colors.warning}
          />
          <Text style={styles.stateTitle}>
            Não foi possível carregar os produtos
          </Text>
          <Text style={styles.stateBody}>
            {products.error instanceof Error
              ? products.error.message
              : "Tente novamente em alguns instantes."}
          </Text>
        </View>
      ) : null}

      {products.data ? (
        <FlatList
          data={filteredProducts}
          keyExtractor={(item) => item.canonicalKey}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.listContent}
          ListHeaderComponent={
            <View style={styles.resultHeader}>
              <Text style={styles.resultLabel}>
                {normalizedQuery
                  ? `${filteredProducts.length} resultado${
                      filteredProducts.length === 1 ? "" : "s"
                    }`
                  : "Todos os produtos"}
              </Text>
            </View>
          }
          ListEmptyComponent={
            <View style={styles.state}>
              <View style={styles.emptyIcon}>
                <Ionicons
                  name="search-outline"
                  size={28}
                  color={appTheme.colors.textMuted}
                />
              </View>

              <Text style={styles.stateTitle}>Nada encontrado</Text>
              <Text style={styles.stateBody}>
                Tente outro nome, modelo ou marketplace.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <SearchResultCard
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
      ) : null}
    </SafeAreaView>
  );
}

function SearchResultCard({
  item,
  onPress,
}: Readonly<{
  item: ProductCard;
  onPress: () => void;
}>) {
  return (
    <Pressable
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.card,
        pressed && styles.cardPressed,
      ]}
      onPress={onPress}
    >
      <View style={styles.productIcon}>
        <Ionicons
          name="hardware-chip-outline"
          size={24}
          color={appTheme.colors.textMuted}
        />
      </View>

      <View style={styles.cardCopy}>
        <Text style={styles.cardTitle} numberOfLines={2}>
          {item.title}
        </Text>

        <View style={styles.metaRow}>
          <Text style={styles.marketplace} numberOfLines={1}>
            {item.marketplace?.trim() || "Marketplace"}
          </Text>

          <Text style={styles.price}>
            {formatPrice(item.currentPrice)}
          </Text>
        </View>
      </View>

      <Ionicons
        name="chevron-forward"
        size={18}
        color={appTheme.colors.textSubtle}
      />
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
    minHeight: 62,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 16,
  },
  iconButton: {
    width: 42,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.surface,
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
    letterSpacing: -0.4,
  },
  searchBox: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    marginHorizontal: 16,
    marginTop: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    paddingHorizontal: 14,
  },
  input: {
    flex: 1,
    color: appTheme.colors.text,
    fontSize: 14,
    paddingVertical: 12,
  },
  clearButton: {
    width: 32,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 32,
    gap: 10,
  },
  resultHeader: {
    paddingBottom: 2,
  },
  resultLabel: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
    fontWeight: "800",
  },
  card: {
    minHeight: 78,
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 12,
  },
  cardPressed: {
    opacity: 0.84,
  },
  productIcon: {
    width: 50,
    height: 50,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  cardCopy: {
    flex: 1,
    gap: 7,
  },
  cardTitle: {
    color: appTheme.colors.text,
    fontSize: 14,
    lineHeight: 19,
    fontWeight: "900",
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  marketplace: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "700",
    textTransform: "capitalize",
  },
  price: {
    color: appTheme.colors.price,
    fontSize: 14,
    fontWeight: "900",
  },
  state: {
    flex: 1,
    minHeight: 260,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    padding: 28,
  },
  emptyIcon: {
    width: 54,
    height: 54,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 18,
    backgroundColor: appTheme.colors.surface,
  },
  stateTitle: {
    color: appTheme.colors.text,
    fontSize: 18,
    fontWeight: "900",
    textAlign: "center",
  },
  stateBody: {
    color: appTheme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
    textAlign: "center",
  },
});
