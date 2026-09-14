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
          />
          <StatusBar style="auto" />
        </AuthSessionBootstrap>
      </AuthSessionProvider>
    </QueryClientProvider>
  );
}
