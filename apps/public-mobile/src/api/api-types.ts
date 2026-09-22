export type ApiHttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type ApiResponseMode = "raw-json" | "user-facing-envelope";

export type ApiQueryValue = string | number | boolean | null | undefined;

export type ApiRequestOptions = Readonly<{
  method?: ApiHttpMethod;
  path: string;
  query?: Readonly<Record<string, ApiQueryValue>>;
  body?: unknown;
  requiresUserSession?: boolean;
  idempotencyKey?: string;
  responseMode?: ApiResponseMode;
  timeoutMs?: number;
}>;

export type UserFacingSuccessEnvelope<T> = Readonly<{
  api_version: string;
  dados: T;
}>;

export type UserFacingErrorEnvelope = Readonly<{
  api_version?: string;
  erro: Readonly<{
    codigo?: string;
    mensagem?: string;
  }>;
}>;
