import * as SecureStore from "expo-secure-store";

import {
  PublicAppRuntimeConfig,
  normalizeApiBaseUrl,
} from "@/src/config/runtime-config";

const API_BASE_URL_KEY = "pra_public_api_base_url_v1";
const INFRASTRUCTURE_TOKEN_KEY = "pra_public_infra_token_v1";
const USER_SESSION_KEY = "pra_public_user_session_v1";

export async function loadRuntimeConfig(): Promise<
  Partial<PublicAppRuntimeConfig>
> {
  const [apiBaseUrl, infrastructureToken] = await Promise.all([
    SecureStore.getItemAsync(API_BASE_URL_KEY),
    SecureStore.getItemAsync(INFRASTRUCTURE_TOKEN_KEY),
  ]);

  return {
    apiBaseUrl: apiBaseUrl ?? undefined,
    infrastructureToken: infrastructureToken ?? undefined,
  };
}

export async function saveRuntimeConfig(
  config: PublicAppRuntimeConfig,
): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(
      API_BASE_URL_KEY,
      normalizeApiBaseUrl(config.apiBaseUrl),
    ),
    SecureStore.setItemAsync(
      INFRASTRUCTURE_TOKEN_KEY,
      config.infrastructureToken.trim(),
    ),
  ]);
}

export async function saveUserSession(token: string): Promise<void> {
  await SecureStore.setItemAsync(USER_SESSION_KEY, token.trim());
}

export async function loadUserSession(): Promise<string | null> {
  return SecureStore.getItemAsync(USER_SESSION_KEY);
}

export async function clearUserSession(): Promise<void> {
  await SecureStore.deleteItemAsync(USER_SESSION_KEY);
}

export async function clearRuntimeConfig(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(API_BASE_URL_KEY),
    SecureStore.deleteItemAsync(INFRASTRUCTURE_TOKEN_KEY),
  ]);
}
