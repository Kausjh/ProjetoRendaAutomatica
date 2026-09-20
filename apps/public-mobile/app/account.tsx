import { Ionicons } from "@expo/vector-icons";
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
import { SafeAreaView } from "react-native-safe-area-context";

import {
  normalizeMarketplaceInput,
  useAccountPreferences,
  useSaveAccountPreferences,
} from "@/src/account";
import { useAuthSession } from "@/src/auth";
import { GamificationPanel } from "@/src/gamification";
import { MissionsPanel } from "@/src/missions";
import { appTheme } from "@/src/ui";

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

  const email =
    accountField(snapshot.account, ["email", "e_mail"]) ??
    "E-mail não informado";

  const initial = email.trim().charAt(0).toUpperCase() || "R";

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
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.container}
      >
        <View style={styles.header}>
          <View style={styles.headerIcon}>
            <Ionicons
              name="person-circle"
              size={20}
              color={appTheme.colors.accent}
            />
          </View>

          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>CONTA E PREFERÊNCIAS</Text>
            <Text style={styles.title}>Perfil</Text>
          </View>
        </View>

        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{initial}</Text>
          </View>

          <View style={styles.profileCopy}>
            <Text style={styles.profileLabel}>Sua conta</Text>
            <Text style={styles.email} numberOfLines={1}>
              {email}
            </Text>
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Atualizar conta"
            disabled={refreshingAccount}
            style={styles.iconButton}
            onPress={() => {
              void refreshAccount();
            }}
          >
            {refreshingAccount ? (
              <ActivityIndicator
                size="small"
                color={appTheme.colors.accent}
              />
            ) : (
              <Ionicons
                name="refresh"
                size={18}
                color={appTheme.colors.text}
              />
            )}
          </Pressable>
        </View>

        <GamificationPanel enabled={authenticated} />

        <MissionsPanel enabled={authenticated} />

        <View style={styles.section}>
          <Text style={styles.sectionEyebrow}>PREFERÊNCIAS</Text>
          <Text style={styles.sectionTitle}>Como o Radar deve te avisar</Text>

          <View style={styles.card}>
            {preferences.isPending ? (
              <View style={styles.inlineLoading}>
                <ActivityIndicator
                  color={appTheme.colors.accent}
                />
                <Text style={styles.hint}>
                  Carregando preferências...
                </Text>
              </View>
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
                  <View style={styles.switchIcon}>
                    <Ionicons
                      name="notifications-outline"
                      size={19}
                      color={appTheme.colors.accent}
                    />
                  </View>

                  <View style={styles.switchCopy}>
                    <Text style={styles.fieldLabel}>
                      Alertas de preço
                    </Text>
                    <Text style={styles.hint}>
                      Receba alertas quando o Radar encontrar mudanças
                      relevantes.
                    </Text>
                  </View>

                  <Switch
                    value={priceNotificationsEnabled}
                    trackColor={{
                      false: appTheme.colors.borderStrong,
                      true: appTheme.colors.accentStrong,
                    }}
                    thumbColor={appTheme.colors.white}
                    onValueChange={setPriceNotificationsEnabled}
                  />
                </View>

                <View style={styles.divider} />

                <View style={styles.field}>
                  <View style={styles.fieldHeading}>
                    <Ionicons
                      name="storefront-outline"
                      size={18}
                      color={appTheme.colors.accent}
                    />
                    <Text style={styles.fieldLabel}>
                      Marketplaces preferidos
                    </Text>
                  </View>

                  <TextInput
                    autoCapitalize="none"
                    autoCorrect={false}
                    multiline
                    placeholder="Ex.: Mercado Livre, Amazon, Shopee"
                    placeholderTextColor={appTheme.colors.textSubtle}
                    selectionColor={appTheme.colors.accent}
                    style={[styles.input, styles.multilineInput]}
                    value={marketplacesText}
                    onChangeText={setMarketplacesText}
                  />

                  <Text style={styles.hint}>
                    Separe os nomes por vírgulas. Deixe vazio para não
                    restringir por marketplace.
                  </Text>

                  {normalizedMarketplaces.length > 0 ? (
                    <View style={styles.chipRow}>
                      {normalizedMarketplaces.map((marketplace) => (
                        <View style={styles.chip} key={marketplace}>
                          <Text style={styles.chipText}>
                            {marketplace}
                          </Text>
                        </View>
                      ))}
                    </View>
                  ) : null}
                </View>

                <Pressable
                  accessibilityRole="button"
                  disabled={savePreferences.isPending}
                  style={[
                    styles.primaryButton,
                    savePreferences.isPending && styles.disabledButton,
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
        </View>

        {localError ? (
          <View style={styles.localError}>
            <Ionicons
              name="alert-circle-outline"
              size={18}
              color={appTheme.colors.danger}
            />
            <Text style={styles.error}>{localError}</Text>
          </View>
        ) : null}

        <View style={styles.section}>
          <Text style={styles.sectionEyebrow}>APLICATIVO</Text>
          <Text style={styles.sectionTitle}>Configurações</Text>

          <Pressable
            accessibilityRole="button"
            style={styles.settingRow}
            onPress={() => router.push("/connection")}
          >
            <View style={styles.settingIcon}>
              <Ionicons
                name="wifi-outline"
                size={19}
                color={appTheme.colors.textMuted}
              />
            </View>

            <View style={styles.settingCopy}>
              <Text style={styles.settingTitle}>Conexão</Text>
              <Text style={styles.hint}>
                Ajustes técnicos de acesso ao Radar.
              </Text>
            </View>

            <Ionicons
              name="chevron-forward"
              size={18}
              color={appTheme.colors.textSubtle}
            />
          </Pressable>
        </View>

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
          <Ionicons
            name="log-out-outline"
            size={19}
            color={appTheme.colors.danger}
          />
          <Text style={styles.logoutButtonText}>
            {loggingOut ? "Saindo..." : "Sair da conta"}
          </Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
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
  container: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 108,
    gap: 18,
  },
  header: {
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
  profileCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  avatar: {
    width: 50,
    height: 50,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 17,
    backgroundColor: appTheme.colors.accentSoft,
  },
  avatarText: {
    color: appTheme.colors.accent,
    fontSize: 21,
    fontWeight: "900",
  },
  profileCopy: {
    flex: 1,
    gap: 3,
  },
  profileLabel: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "700",
  },
  email: {
    color: appTheme.colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  iconButton: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  section: {
    gap: 10,
  },
  sectionEyebrow: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.3,
  },
  sectionTitle: {
    color: appTheme.colors.text,
    fontSize: 19,
    fontWeight: "900",
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
    gap: 14,
  },
  inlineLoading: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  errorCard: {
    gap: 10,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.dangerSurface,
    padding: 12,
  },
  error: {
    flex: 1,
    color: appTheme.colors.danger,
    fontSize: 12,
    lineHeight: 18,
  },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
  },
  switchIcon: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.accentSoft,
  },
  switchCopy: {
    flex: 1,
    gap: 3,
  },
  field: {
    gap: 8,
  },
  fieldHeading: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  fieldLabel: {
    color: appTheme.colors.text,
    fontSize: 13,
    fontWeight: "900",
  },
  hint: {
    color: appTheme.colors.textMuted,
    fontSize: 11,
    lineHeight: 17,
  },
  divider: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: appTheme.colors.border,
  },
  input: {
    minHeight: 48,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    color: appTheme.colors.text,
    paddingHorizontal: 13,
    fontSize: 14,
  },
  multilineInput: {
    minHeight: 78,
    paddingTop: 12,
    textAlignVertical: "top",
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 7,
  },
  chip: {
    borderRadius: appTheme.radius.pill,
    backgroundColor: appTheme.colors.accentSoft,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  chipText: {
    color: appTheme.colors.accent,
    fontSize: 10,
    fontWeight: "800",
  },
  primaryButton: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accentStrong,
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: appTheme.colors.white,
    fontSize: 13,
    fontWeight: "900",
  },
  secondaryButton: {
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    paddingHorizontal: 16,
  },
  secondaryButtonText: {
    color: appTheme.colors.text,
    fontSize: 12,
    fontWeight: "900",
  },
  localError: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.dangerSurface,
    padding: 12,
  },
  settingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 11,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  settingIcon: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  settingCopy: {
    flex: 1,
    gap: 3,
  },
  settingTitle: {
    color: appTheme.colors.text,
    fontSize: 13,
    fontWeight: "900",
  },
  logoutButton: {
    minHeight: 50,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.dangerBorder,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.dangerSurface,
    paddingHorizontal: 18,
  },
  logoutButtonText: {
    color: appTheme.colors.danger,
    fontSize: 13,
    fontWeight: "900",
  },
  disabledButton: {
    opacity: 0.55,
  },
});
