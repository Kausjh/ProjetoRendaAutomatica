import { Redirect, router } from "expo-router";
import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from "react-native";

import { useAuthSession } from "@/src/auth";

export default function LoginScreen() {
  const { login, snapshot } = useAuthSession();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (snapshot.status === "authenticated") {
    return <Redirect href="/home" />;
  }

  const submit = async (): Promise<void> => {
    if (!email.trim() || !senha) {
      setError("Informe e-mail e senha.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await login({
        email: email.trim(),
        senha,
      });

      router.replace("/home");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Não foi possível entrar.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.eyebrow}>PROJETO RENDA AUTOMÁTICA</Text>
        <Text style={styles.title}>Entrar</Text>
        <Text style={styles.body}>
          Use sua conta da plataforma para acessar o aplicativo.
        </Text>

        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          autoCorrect={false}
          keyboardType="email-address"
          placeholder="E-mail"
          style={styles.input}
          value={email}
          onChangeText={setEmail}
        />

        <TextInput
          autoCapitalize="none"
          autoComplete="password"
          placeholder="Senha"
          secureTextEntry
          style={styles.input}
          value={senha}
          onChangeText={setSenha}
        />

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Pressable
          accessibilityRole="button"
          disabled={submitting}
          style={[
            styles.primaryButton,
            submitting && styles.disabledButton,
          ]}
          onPress={() => {
            void submit();
          }}
        >
          <Text style={styles.primaryButtonText}>
            {submitting ? "Entrando..." : "Entrar"}
          </Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          style={styles.secondaryButton}
          onPress={() => router.push("/register")}
        >
          <Text style={styles.secondaryButtonText}>
            Criar uma conta
          </Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          onPress={() => router.push("/connection")}
        >
          <Text style={styles.link}>
            Configuração da conexão
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
  container: {
    flexGrow: 1,
    justifyContent: "center",
    gap: 16,
    padding: 24,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    opacity: 0.6,
  },
  title: {
    fontSize: 34,
    fontWeight: "800",
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    opacity: 0.75,
    marginBottom: 4,
  },
  input: {
    minHeight: 52,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 14,
    paddingHorizontal: 14,
    fontSize: 16,
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
  },
  secondaryButton: {
    minHeight: 52,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
  },
  disabledButton: {
    opacity: 0.5,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
  secondaryButtonText: {
    fontSize: 16,
    fontWeight: "700",
  },
  link: {
    textAlign: "center",
    fontSize: 14,
    fontWeight: "600",
    textDecorationLine: "underline",
  },
});
