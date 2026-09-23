import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useState } from "react";

import {
  AuthSessionBootstrap,
  AuthSessionProvider,
} from "@/src/auth";
import { DeviceRegistrationBootstrap } from "@/src/device";
import { AppBottomNav, appTheme } from "@/src/ui";

export default function RootLayout() {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AuthSessionProvider>
        <AuthSessionBootstrap>
          <DeviceRegistrationBootstrap>
            <Stack
            screenOptions={{
              headerTitleAlign: "center",
              headerStyle: {
                backgroundColor: appTheme.colors.surface,
              },
              headerTintColor: appTheme.colors.text,
              headerShadowVisible: false,
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
                headerShown: false,
                gestureEnabled: false,
              }}
            />
            <Stack.Screen
              name="watchlist"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="alerts"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="account"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="search"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="discover"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="report"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="reports"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="report-status"
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="product/[canonicalKey]"
              options={{
                title: "Produto",
                headerBackTitle: "Voltar",
              }}
            />
          </Stack>

            <AppBottomNav />
            <StatusBar style="light" />
          </DeviceRegistrationBootstrap>
        </AuthSessionBootstrap>
      </AuthSessionProvider>
    </QueryClientProvider>
  );
}
