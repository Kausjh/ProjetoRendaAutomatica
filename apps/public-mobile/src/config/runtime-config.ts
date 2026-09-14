import { ApiClientConfigurationError } from "@/src/api/api-error";

export type PublicAppRuntimeConfig = Readonly<{
  apiBaseUrl: string;
  infrastructureToken: string;
}>;

export const PUBLIC_APP_TRANSPORT_PROFILE =
  "tailscale-http-trusted-tunnel" as const;

export function normalizeApiBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, "");
}

export function isRuntimeConfigComplete(
  config: Partial<PublicAppRuntimeConfig>,
): config is PublicAppRuntimeConfig {
  return Boolean(
    config.apiBaseUrl?.trim() && config.infrastructureToken?.trim(),
  );
}

export function requireRuntimeConfig(
  config: Partial<PublicAppRuntimeConfig>,
): PublicAppRuntimeConfig {
  if (!isRuntimeConfigComplete(config)) {
    throw new ApiClientConfigurationError(
      "A configuração local da API está incompleta.",
    );
  }

  const apiBaseUrl = normalizeApiBaseUrl(config.apiBaseUrl);

  let parsed: URL;

  try {
    parsed = new URL(apiBaseUrl);
  } catch {
    throw new ApiClientConfigurationError(
      "A URL local da API é inválida.",
    );
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new ApiClientConfigurationError(
      "A API deve usar HTTP ou HTTPS.",
    );
  }

  if (parsed.port === "8765") {
    throw new ApiClientConfigurationError(
      "A porta administrativa não pode ser usada pelo app público.",
    );
  }

  if (!parsed.pathname.endsWith("/api/v1")) {
    throw new ApiClientConfigurationError(
      "A URL da API deve terminar em /api/v1.",
    );
  }

  return {
    apiBaseUrl,
    infrastructureToken: config.infrastructureToken.trim(),
  };
}
