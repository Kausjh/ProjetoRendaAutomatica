import {
  ApiClientConfigurationError,
  ApiHttpError,
  ApiSessionRequiredError,
} from "@/src/api/api-error";
import {
  ApiQueryValue,
  ApiRequestOptions,
  UserFacingErrorEnvelope,
  UserFacingSuccessEnvelope,
} from "@/src/api/api-types";
import {
  PublicAppRuntimeConfig,
  requireRuntimeConfig,
} from "@/src/config/runtime-config";

export type RuntimeConfigLoader = () => Promise<
  Partial<PublicAppRuntimeConfig>
>;

export type UserSessionLoader = () => Promise<string | null>;

const DEFAULT_TIMEOUT_MS = 15_000;

function buildQueryString(
  query: Readonly<Record<string, ApiQueryValue>> | undefined,
): string {
  if (!query) {
    return "";
  }

  const parts: string[] = [];

  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined) {
      continue;
    }

    parts.push(
      `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`,
    );
  }

  return parts.length > 0 ? `?${parts.join("&")}` : "";
}

function buildUrl(
  config: PublicAppRuntimeConfig,
  path: string,
  query: Readonly<Record<string, ApiQueryValue>> | undefined,
): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  return `${config.apiBaseUrl}${normalizedPath}${buildQueryString(query)}`;
}

function parseRetryAfter(value: string | null): number | null {
  if (!value) {
    return null;
  }

  const seconds = Number.parseInt(value, 10);

  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseJson(text: string): unknown {
  if (!text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new ApiHttpError({
      status: 502,
      code: "resposta_json_invalida",
      message: "A API retornou uma resposta inválida.",
    });
  }
}

function extractError(
  status: number,
  payload: unknown,
  retryAfterSeconds: number | null,
): ApiHttpError {
  let code: string | null = null;
  let message = `A API respondeu com status ${status}.`;

  if (isRecord(payload)) {
    const erro = payload.erro;

    if (typeof erro === "string" && erro.trim()) {
      message = erro;
    } else if (isRecord(erro)) {
      const envelope = payload as unknown as UserFacingErrorEnvelope;

      if (typeof envelope.erro.codigo === "string") {
        code = envelope.erro.codigo;
      }

      if (
        typeof envelope.erro.mensagem === "string" &&
        envelope.erro.mensagem.trim()
      ) {
        message = envelope.erro.mensagem;
      }
    }
  }

  return new ApiHttpError({
    status,
    code,
    message,
    retryAfterSeconds,
  });
}

export class HttpApiTransport {
  constructor(
    private readonly loadRuntimeConfig: RuntimeConfigLoader,
    private readonly loadUserSession: UserSessionLoader,
  ) {}

  async request<T>(options: ApiRequestOptions): Promise<T> {
    const config = requireRuntimeConfig(await this.loadRuntimeConfig());

    let userSession: string | null = null;

    if (options.requiresUserSession) {
      userSession = await this.loadUserSession();

      if (!userSession?.trim()) {
        throw new ApiSessionRequiredError();
      }
    }

    const controller = new AbortController();
    const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    const headers: Record<string, string> = {
      Accept: "application/json",
      Authorization: `Bearer ${config.infrastructureToken}`,
    };

    if (userSession) {
      headers["X-User-Session"] = userSession;
    }

    const idempotencyKey = options.idempotencyKey?.trim();

    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }

    let body: string | undefined;

    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }

    try {
      const response = await fetch(
        buildUrl(config, options.path, options.query),
        {
          method: options.method ?? "GET",
          headers,
          body,
          signal: controller.signal,
        },
      );

      const payload = parseJson(await response.text());

      if (!response.ok) {
        throw extractError(
          response.status,
          payload,
          parseRetryAfter(response.headers.get("Retry-After")),
        );
      }

      if (options.responseMode === "user-facing-envelope") {
        if (!isRecord(payload) || !("dados" in payload)) {
          throw new ApiHttpError({
            status: 502,
            code: "envelope_user_facing_invalido",
            message: "A API retornou um envelope inesperado.",
          });
        }

        return (payload as unknown as UserFacingSuccessEnvelope<T>).dados;
      }

      return payload as T;
    } catch (error) {
      if (error instanceof ApiHttpError) {
        throw error;
      }

      if (error instanceof ApiSessionRequiredError) {
        throw error;
      }

      if (error instanceof ApiClientConfigurationError) {
        throw error;
      }

      if (
        error instanceof Error &&
        error.name === "AbortError"
      ) {
        throw new ApiHttpError({
          status: 408,
          code: "timeout_cliente",
          message: "A API demorou demais para responder.",
        });
      }

      throw new ApiHttpError({
        status: 0,
        code: "falha_rede",
        message: "Não foi possível conectar à API.",
      });
    } finally {
      clearTimeout(timeout);
    }
  }
}
