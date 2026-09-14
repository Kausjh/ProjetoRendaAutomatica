import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useState } from "react";

import {
  AuthSessionBootstrap,
  AuthSessionProvider,
} from "@/src/auth";

export default function RootLayout() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AuthSessionProvider>
        <AuthSessionBootstrap>
          <Stack
            screenOptions={{
              headerTitleAlign: "center",
            }}
          >
            <Stack.Screen
              name="index"
              options={{ headerShown: false }}
            />
            <Stack.Screen
              name="connection"
              options={{ title: "Conexão" }}
            />
            <Stack.Screen
              name="login"
              options={{ headerShown: false }}
            />
            <Stack.Screen
              name="register"
              options={{ title: "Criar conta" }}
            />
            <Stack.Screen
              name="home"
              options={{
                title: "Ofertas",
                headerBackVisible: false,
              }}
            />
            <Stack.Screen
              name="product/[canonicalKey]"
              options={{
                title: "Produto",
              }}
            />
          </Stack>
          <StatusBar style="auto" />
        </AuthSessionBootstrap>
      </AuthSessionProvider>
    </QueryClientProvider>
  );
}
