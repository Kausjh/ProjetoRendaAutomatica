export type AuthSessionStatus =
  | "restoring"
  | "anonymous"
  | "authenticated"
  | "error";

export type PublicAccount = Readonly<Record<string, unknown>>;

export type PublicUserSession = Readonly<{
  token: string;
  expira_em: string;
}>;

export type RegisterResult = Readonly<{
  conta: PublicAccount;
}>;

export type LoginResult = Readonly<{
  conta: PublicAccount;
  sessao: PublicUserSession;
}>;

export type MeResult = Readonly<{
  conta: PublicAccount;
}>;

export type AuthSessionSnapshot = Readonly<{
  status: AuthSessionStatus;
  account: PublicAccount | null;
  error: Error | null;
}>;
