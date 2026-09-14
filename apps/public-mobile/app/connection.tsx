import { router } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { useAuthSession } from "@/src/auth";
import {
  normalizeApiBaseUrl,
  requireRuntimeConfig,
} from "@/src/config/runtime-config";
import {
  clearUserSession,
  loadRuntimeConfig,
  saveRuntimeConfig,
} from "@/src/storage/secure-runtime-config";

export default function ConnectionScreen() {
  const { restore } = useAuthSession();
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [hasStoredToken, setHasStoredToken] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [infrastructureToken, setInfrastructureToken] =
    useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void loadRuntimeConfig()
      .then((config) => {
        if (!active) {
          return;
        }

        setApiBaseUrl(config.apiBaseUrl ?? "");
        setHasStoredToken(Boolean(config.infrastructureToken?.trim()));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const save = async (): Promise<void> => {
    setError(null);
    setSaving(true);

    try {
      const existing = await loadRuntimeConfig();
      const normalizedInput = normalizeApiBaseUrl(apiBaseUrl);
      const normalizedExisting = existing.apiBaseUrl
        ? normalizeApiBaseUrl(existing.apiBaseUrl)
        : "";

      const typedToken = infrastructureToken.trim();

      if (
        normalizedInput !== normalizedExisting &&
        !typedToken
      ) {
        throw new Error(
          "Informe o token de infraestrutura ao trocar o endpoint.",
        );
      }

      const token =
        typedToken || existing.infrastructureToken?.trim() || "";

      const validated = requireRuntimeConfig({
        apiBaseUrl: normalizedInput,
        infrastructureToken: token,
      });

      const configChanged =
        normalizedInput !== normalizedExisting ||
        Boolean(
          typedToken &&
            typedToken !== existing.infrastructureToken?.trim(),
        );

      await saveRuntimeConfig(validated);

      if (configChanged) {
        await clearUserSession();
      }

      await restore();
      router.replace("/");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível salvar a configuração.",
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.eyebrow}>ALPHA INTERNO</Text>
        <Text style={styles.title}>Conexão com a API</Text>
        <Text style={styles.body}>
          Informe o endpoint confiável da Application API e o Bearer
          de infraestrutura. Esses dados ficam no Secure Store do
          aparelho e não fazem parte do bundle.
        </Text>

        <View style={styles.field}>
          <Text style={styles.label}>URL da API</Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            placeholder="http://endpoint-confiavel:18767/api/v1"
            style={styles.input}
            value={apiBaseUrl}
            onChangeText={setApiBaseUrl}
          />
          <Text style={styles.hint}>
            A URL precisa terminar em /api/v1. A porta 8765 é
            recusada pelo app.
          </Text>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Token de infraestrutura</Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            placeholder={
              hasStoredToken
                ? "Deixe em branco para manter o token salvo"
                : "Bearer usado pelo alpha"
            }
            secureTextEntry
            style={styles.input}
            value={infrastructureToken}
            onChangeText={setInfrastructureToken}
          />
          <Text style={styles.hint}>
            O valor salvo nunca é exibido novamente nesta tela.
          </Text>
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          accessibilityRole="button"
          disabled={saving}
          style={[
            styles.primaryButton,
            saving && styles.disabledButton,
          ]}
          onPress={() => {
            void save();
          }}
        >
          <Text style={styles.primaryButtonText}>
            {saving ? "Salvando..." : "Salvar e continuar"}
          </Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  container: {
    flexGrow: 1,
    justifyContent: "center",
    gap: 18,
    padding: 24,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    opacity: 0.6,
  },
  title: {
    fontSize: 30,
    fontWeight: "800",
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    opacity: 0.75,
  },
  field: {
    gap: 8,
  },
  label: {
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
  hint: {
    fontSize: 12,
    lineHeight: 18,
    opacity: 0.6,
  },
  error: {
    fontSize: 14,
    lineHeight: 20,
  },
  primaryButton: {
    minHeight: 52,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: "#111111",
    paddingHorizontal: 18,
  },
  disabledButton: {
    opacity: 0.5,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
});
