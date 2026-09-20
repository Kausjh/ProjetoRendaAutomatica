import { HttpApiTransport } from "@/src/api/http-transport";

export type PaginationParams = Readonly<{
  limite?: number;
  offset?: number;
}>;

export type RegisterInput = Readonly<{
  email: string;
  senha: string;
}>;

export type LoginInput = RegisterInput;

export type PreferencesPatch = Readonly<{
  notificacoes_preco_habilitadas?: boolean;
  marketplaces_preferidos?: readonly string[];
}>;

export type WatchlistPutInput = Readonly<{
  preco_alvo?: number | string | null;
  notificar_queda_preco?: boolean;
}>;

export type DeviceRegistrationPutInput = Readonly<{
  plataforma: "android" | "ios";
  push_token: string;
}>;

export type CommunityDiscoveryCreateInput = Readonly<{
  url: string;
}>;

export class PublicApiClient {
  constructor(private readonly transport: HttpApiTransport) {}

  health<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      path: "/health",
      responseMode: "raw-json",
    });
  }

  listProducts<T = unknown>(
    pagination: PaginationParams = {},
  ): Promise<T> {
    return this.transport.request<T>({
      path: "/produtos",
      query: pagination,
      responseMode: "raw-json",
    });
  }

  getProduct<T = unknown>(canonicalKey: string): Promise<T> {
    return this.transport.request<T>({
      path: `/produtos/${encodeURIComponent(canonicalKey)}`,
      responseMode: "raw-json",
    });
  }

  getProductHistory<T = unknown>(
    canonicalKey: string,
    pagination: PaginationParams = {},
  ): Promise<T> {
    return this.transport.request<T>({
      path: `/produtos/${encodeURIComponent(canonicalKey)}/historico`,
      query: pagination,
      responseMode: "raw-json",
    });
  }

  listAlerts<T = unknown>(
    pagination: PaginationParams = {},
  ): Promise<T> {
    return this.transport.request<T>({
      path: "/alertas",
      query: pagination,
      responseMode: "raw-json",
    });
  }

  register<T = unknown>(input: RegisterInput): Promise<T> {
    return this.transport.request<T>({
      method: "POST",
      path: "/auth/register",
      body: input,
      responseMode: "user-facing-envelope",
    });
  }

  login<T = unknown>(input: LoginInput): Promise<T> {
    return this.transport.request<T>({
      method: "POST",
      path: "/auth/login",
      body: input,
      responseMode: "user-facing-envelope",
    });
  }

  logout<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      method: "POST",
      path: "/auth/logout",
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  me<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      path: "/me",
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  getGamification<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      path: "/me/gamification",
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  getPreferences<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      path: "/me/preferences",
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  patchPreferences<T = unknown>(
    patch: PreferencesPatch,
  ): Promise<T> {
    return this.transport.request<T>({
      method: "PATCH",
      path: "/me/preferences",
      body: patch,
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  listCommunityDiscoveries<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      path: "/me/discoveries",
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  createCommunityDiscovery<T = unknown>(
    input: CommunityDiscoveryCreateInput,
  ): Promise<T> {
    return this.transport.request<T>({
      method: "POST",
      path: "/me/discoveries",
      body: input,
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  getPersonalizedFeed<T = unknown>(
    pagination: PaginationParams = {},
  ): Promise<T> {
    return this.transport.request<T>({
      path: "/me/feed",
      query: pagination,
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  getWatchlist<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      path: "/me/watchlist",
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  putWatchlist<T = unknown>(
    canonicalKey: string,
    input: WatchlistPutInput,
  ): Promise<T> {
    return this.transport.request<T>({
      method: "PUT",
      path: `/me/watchlist/${encodeURIComponent(canonicalKey)}`,
      body: input,
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  deleteWatchlist<T = unknown>(
    canonicalKey: string,
  ): Promise<T> {
    return this.transport.request<T>({
      method: "DELETE",
      path: `/me/watchlist/${encodeURIComponent(canonicalKey)}`,
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  listDevices<T = unknown>(): Promise<T> {
    return this.transport.request<T>({
      path: "/me/devices",
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  putDevice<T = unknown>(
    installationId: string,
    input: DeviceRegistrationPutInput,
  ): Promise<T> {
    return this.transport.request<T>({
      method: "PUT",
      path: `/me/devices/${encodeURIComponent(installationId)}`,
      body: input,
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }

  deleteDevice<T = unknown>(installationId: string): Promise<T> {
    return this.transport.request<T>({
      method: "DELETE",
      path: `/me/devices/${encodeURIComponent(installationId)}`,
      requiresUserSession: true,
      responseMode: "user-facing-envelope",
    });
  }
}
