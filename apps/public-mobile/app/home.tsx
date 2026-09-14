import { Alert } from "react-native";
import { Redirect, router } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useAuthSession } from "@/src/auth";

function accountEmail(
  account: Readonly<Record<string, unknown>> | null,
): string {
  const email = account?.email;
  return typeof email === "string" ? email : "Conta autenticada";
}

export default function HomeScreen() {
  const { logout, snapshot } = useAuthSession();
  const [loggingOut, setLoggingOut] = useState(false);

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
      <Text style={styles.eyebrow}>ÁREA AUTENTICADA</Text>
      <Text style={styles.title}>Public App MVP</Text>
      <Text style={styles.body}>
        A autenticação está funcionando. O próximo bloco começa a
        conectar as telas de ofertas e dados do produto.
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardLabel}>Conta</Text>
        <Text style={styles.cardValue}>
          {accountEmail(snapshot.account)}
        </Text>
      </View>

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
          styles.primaryButton,
          loggingOut && styles.disabledButton,
        ]}
        onPress={() => {
          void performLogout();
        }}
      >
        <Text style={styles.primaryButtonText}>
          {loggingOut ? "Saindo..." : "Sair"}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    gap: 16,
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
  },
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: 16,
    padding: 18,
    gap: 6,
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: "700",
    opacity: 0.55,
    textTransform: "uppercase",
  },
  cardValue: {
    fontSize: 17,
    fontWeight: "700",
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
});
