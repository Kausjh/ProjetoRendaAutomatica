export class ApiClientConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiClientConfigurationError";
  }
}

export class ApiSessionRequiredError extends Error {
  constructor() {
    super("Esta operação exige uma sessão de usuário válida.");
    this.name = "ApiSessionRequiredError";
  }
}

export class ApiHttpError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(options: {
    status: number;
    message: string;
    code?: string | null;
    retryAfterSeconds?: number | null;
  }) {
    super(options.message);
    this.name = "ApiHttpError";
    this.status = options.status;
    this.code = options.code ?? null;
    this.retryAfterSeconds = options.retryAfterSeconds ?? null;
  }
}
