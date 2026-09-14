import { Redirect, router } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { useAuthSession } from "@/src/auth";
import {
  isRuntimeConfigComplete,
} from "@/src/config/runtime-config";
import {
  loadRuntimeConfig,
} from "@/src/storage/secure-runtime-config";

type ConfigState = "loading" | "missing" | "ready";

export default function EntryGateScreen() {
  const { snapshot, restore } = useAuthSession();
  const [configState, setConfigState] =
    useState<ConfigState>("loading");

  useEffect(() => {
    let active = true;

    void loadRuntimeConfig().then((config) => {
      if (!active) {
        return;
      }

      setConfigState(
        isRuntimeConfigComplete(config) ? "ready" : "missing",
      );
    });

    return () => {
      active = false;
    };
  }, []);

  if (configState === "loading") {
    return <LoadingState label="Carregando configuração local..." />;
  }

  if (configState === "missing") {
    return <Redirect href="/connection" />;
  }

  if (snapshot.status === "restoring") {
    return <LoadingState label="Validando sua sessão..." />;
  }

  if (snapshot.status === "authenticated") {
    return <Redirect href="/home" />;
  }

  if (snapshot.status === "anonymous") {
    return <Redirect href="/login" />;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Não foi possível validar a sessão</Text>
      <Text style={styles.body}>
        Sua sessão local foi preservada. Isso pode ser apenas uma falha
        temporária de conexão.
      </Text>

      {snapshot.error ? (
        <Text style={styles.error}>{snapshot.error.message}</Text>
      ) : null}

      <Pressable
        accessibilityRole="button"
        style={styles.primaryButton}
        onPress={() => {
          void restore();
        }}
      >
        <Text style={styles.primaryButtonText}>Tentar novamente</Text>
      </Pressable>

      <Pressable
        accessibilityRole="button"
        style={styles.secondaryButton}
        onPress={() => router.push("/connection")}
      >
        <Text style={styles.secondaryButtonText}>
          Revisar configuração da API
        </Text>
      </Pressable>
    </View>
  );
}

function LoadingState({ label }: Readonly<{ label: string }>) {
  return (
    <View style={styles.loading}>
      <ActivityIndicator size="large" />
      <Text style={styles.body}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    padding: 24,
  },
  container: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    gap: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: "800",
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    opacity: 0.75,
  },
  error: {
    fontSize: 14,
    lineHeight: 20,
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
    fontSize: 16,
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
    fontSize: 16,
    fontWeight: "600",
  },
});
