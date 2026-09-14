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
