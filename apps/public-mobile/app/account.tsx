import { Redirect, router } from "expo-router";
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

import {
  normalizeMarketplaceInput,
  useAccountPreferences,
  useSaveAccountPreferences,
} from "@/src/account";
import { useAuthSession } from "@/src/auth";

function accountField(
  account: Readonly<Record<string, unknown>> | null,
  keys: readonly string[],
): string | null {
  if (!account) {
    return null;
  }

  for (const key of keys) {
    const value = account[key];

    if (
      (typeof value === "string" && value.trim()) ||
      typeof value === "number"
    ) {
      return String(value);
    }
  }

  return null;
}

export default function AccountScreen() {
  const {
    logout,
    refreshMe,
    snapshot,
  } = useAuthSession();

  const authenticated = snapshot.status === "authenticated";
  const preferences = useAccountPreferences(authenticated);
  const savePreferences = useSaveAccountPreferences();

  const [priceNotificationsEnabled, setPriceNotificationsEnabled] =
    useState(true);
  const [marketplacesText, setMarketplacesText] = useState("");
  const [refreshingAccount, setRefreshingAccount] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!preferences.data) {
      return;
    }

    setPriceNotificationsEnabled(
      preferences.data.priceNotificationsEnabled,
    );

    setMarketplacesText(
      preferences.data.preferredMarketplaces.join(", "),
    );
  }, [preferences.data]);

  const normalizedMarketplaces = useMemo(
    () => normalizeMarketplaceInput(marketplacesText),
    [marketplacesText],
  );

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

  const email =
    accountField(snapshot.account, ["email", "e_mail"]) ??
    "E-mail não informado";

  const accountId = accountField(snapshot.account, [
    "id",
    "conta_id",
    "account_id",
  ]);

  const refreshAccount = async (): Promise<void> => {
    setLocalError(null);
    setRefreshingAccount(true);

    try {
      await refreshMe();
      await preferences.refetch();
    } catch (caught) {
      setLocalError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível atualizar a conta.",
      );
    } finally {
      setRefreshingAccount(false);
    }
  };

  const save = async (): Promise<void> => {
    setLocalError(null);

    try {
      await savePreferences.mutateAsync({
        priceNotificationsEnabled,
        preferredMarketplaces: normalizedMarketplaces,
      });

      Alert.alert(
        "Preferências salvas",
        "Suas preferências foram atualizadas.",
      );
    } catch (caught) {
      setLocalError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível salvar as preferências.",
      );
    }
  };

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
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.eyebrow}>CONTA</Text>
      <Text style={styles.title}>Minha conta</Text>

      <View style={styles.card}>
        <Text style={styles.label}>E-mail</Text>
        <Text style={styles.value}>{email}</Text>

        {accountId ? (
          <>
            <Text style={styles.label}>Identificador</Text>
            <Text selectable style={styles.value}>
              {accountId}
            </Text>
          </>
        ) : null}
      </View>

      <Pressable
        accessibilityRole="button"
        disabled={refreshingAccount}
        style={styles.secondaryButton}
        onPress={() => {
          void refreshAccount();
        }}
      >
        <Text style={styles.secondaryButtonText}>
          {refreshingAccount
            ? "Atualizando..."
            : "Atualizar dados da conta"}
        </Text>
      </Pressable>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Preferências</Text>

        {preferences.isPending ? (
          <ActivityIndicator />
        ) : null}

        {preferences.isError ? (
          <View style={styles.errorCard}>
            <Text style={styles.error}>
              {preferences.error instanceof Error
                ? preferences.error.message
                : "Não foi possível carregar as preferências."}
            </Text>

            <Pressable
              accessibilityRole="button"
              style={styles.secondaryButton}
              onPress={() => {
                void preferences.refetch();
              }}
            >
              <Text style={styles.secondaryButtonText}>
                Tentar novamente
              </Text>
            </Pressable>
          </View>
        ) : null}

        {preferences.data ? (
          <>
            <View style={styles.switchRow}>
              <View style={styles.switchCopy}>
                <Text style={styles.fieldLabel}>
                  Notificações de preço
                </Text>
                <Text style={styles.hint}>
                  Controla o matching futuro de alertas personalizados.
                </Text>
              </View>

              <Switch
                value={priceNotificationsEnabled}
                onValueChange={setPriceNotificationsEnabled}
              />
            </View>

            <View style={styles.field}>
              <Text style={styles.fieldLabel}>
                Marketplaces preferidos
              </Text>

              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                multiline
                placeholder="Ex.: Mercado Livre, Amazon"
                style={[styles.input, styles.multilineInput]}
                value={marketplacesText}
                onChangeText={setMarketplacesText}
              />

              <Text style={styles.hint}>
                Separe por vírgulas. Deixe vazio para não restringir
                por marketplace.
              </Text>

              {normalizedMarketplaces.length > 0 ? (
                <Text style={styles.preview}>
                  {normalizedMarketplaces.join(" • ")}
                </Text>
              ) : null}
            </View>

            <Pressable
              accessibilityRole="button"
              disabled={savePreferences.isPending}
              style={[
                styles.primaryButton,
                savePreferences.isPending &&
                  styles.disabledButton,
              ]}
              onPress={() => {
                void save();
              }}
            >
              <Text style={styles.primaryButtonText}>
                {savePreferences.isPending
                  ? "Salvando..."
                  : "Salvar preferências"}
              </Text>
            </Pressable>
          </>
        ) : null}
      </View>

      {localError ? (
        <Text style={styles.error}>{localError}</Text>
      ) : null}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Aplicativo</Text>

        <Pressable
          accessibilityRole="button"
          style={styles.secondaryButton}
          onPress={() => router.push("/connection")}
        >
          <Text style={styles.secondaryButtonText}>
            Configuração da conexão
          </Text>
        </Pressable>

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
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingBottom: 40,
    gap: 16,
  },
  centerState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    opacity: 0.55,
  },
  title: {
    fontSize: 30,
    fontWeight: "800",
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 18,
    padding: 16,
    gap: 6,
  },
  label: {
    marginTop: 6,
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.7,
    opacity: 0.55,
    textTransform: "uppercase",
  },
  value: {
    fontSize: 16,
    lineHeight: 22,
    fontWeight: "700",
  },
  section: {
    gap: 12,
    marginTop: 8,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "800",
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
  field: {
    gap: 7,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: "700",
  },
  hint: {
    fontSize: 12,
    lineHeight: 18,
    opacity: 0.6,
  },
  input: {
    minHeight: 50,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 14,
    paddingHorizontal: 14,
    fontSize: 16,
  },
  multilineInput: {
    minHeight: 88,
    paddingTop: 12,
    textAlignVertical: "top",
  },
  preview: {
    fontSize: 13,
    lineHeight: 19,
    fontWeight: "600",
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
  logoutButton: {
    minHeight: 50,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 18,
  },
  logoutButtonText: {
    fontSize: 15,
    fontWeight: "700",
  },
  disabledButton: {
    opacity: 0.5,
  },
  errorCard: {
    gap: 10,
  },
  error: {
    fontSize: 14,
    lineHeight: 20,
  },
});
