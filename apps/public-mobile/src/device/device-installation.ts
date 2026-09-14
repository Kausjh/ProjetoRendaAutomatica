import * as Crypto from "expo-crypto";
import * as SecureStore from "expo-secure-store";

const INSTALLATION_ID_KEY = "pra_public_installation_id_v1";

function normalizeInstallationId(value: string | null): string | null {
  const normalized = value?.trim();

  if (!normalized || normalized.length < 8 || normalized.length > 128) {
    return null;
  }

  return normalized;
}

export async function loadInstallationId(): Promise<string | null> {
  return normalizeInstallationId(
    await SecureStore.getItemAsync(INSTALLATION_ID_KEY),
  );
}

export async function ensureInstallationId(): Promise<string> {
  const current = await loadInstallationId();

  if (current) {
    return current;
  }

  const generated = `inst_${Crypto.randomUUID()}`;

  await SecureStore.setItemAsync(INSTALLATION_ID_KEY, generated);

  return generated;
}
