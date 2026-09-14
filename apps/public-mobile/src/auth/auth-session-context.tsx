import {
  PropsWithChildren,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

import { ApiHttpError } from "@/src/api/api-error";
import {
  LoginInput,
  RegisterInput,
} from "@/src/api/public-api-client";
import { createPublicApiClient } from "@/src/api/create-public-api-client";
import { revokeCurrentDeviceRegistration } from "@/src/device/device-registration-service";
import {
  AuthSessionSnapshot,
  LoginResult,
  MeResult,
  PublicAccount,
  RegisterResult,
} from "@/src/auth/auth-session-types";
import {
  clearUserSession,
  loadUserSession,
  saveUserSession,
} from "@/src/storage/secure-runtime-config";

type AuthSessionContextValue = Readonly<{
  snapshot: AuthSessionSnapshot;
  restore: () => Promise<void>;
  register: (input: RegisterInput) => Promise<PublicAccount>;
  login: (input: LoginInput) => Promise<PublicAccount>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<PublicAccount | null>;
}>;

const AuthSessionContext = createContext<AuthSessionContextValue | null>(
  null,
);

const api = createPublicApiClient();

function asError(error: unknown): Error {
  return error instanceof Error
    ? error
    : new Error("Falha inesperada de autenticação.");
}

function isInvalidSession(error: unknown): boolean {
  return error instanceof ApiHttpError && error.status === 401;
}

function anonymousSnapshot(): AuthSessionSnapshot {
  return {
    status: "anonymous",
    account: null,
    error: null,
  };
}

export function AuthSessionProvider({
  children,
}: PropsWithChildren) {
  const [snapshot, setSnapshot] = useState<AuthSessionSnapshot>({
    status: "restoring",
    account: null,
    error: null,
  });

  const restore = useCallback(async (): Promise<void> => {
    setSnapshot({
      status: "restoring",
      account: null,
      error: null,
    });

    const token = await loadUserSession();

    if (!token?.trim()) {
      setSnapshot(anonymousSnapshot());
      return;
    }

    try {
      const result = await api.me<MeResult>();

      setSnapshot({
        status: "authenticated",
        account: result.conta,
        error: null,
      });
    } catch (error) {
      if (isInvalidSession(error)) {
        await clearUserSession();
        setSnapshot(anonymousSnapshot());
        return;
      }

      setSnapshot({
        status: "error",
        account: null,
        error: asError(error),
      });
    }
  }, []);

  const register = useCallback(
    async (input: RegisterInput): Promise<PublicAccount> => {
      const result = await api.register<RegisterResult>(input);
      return result.conta;
    },
    [],
  );

  const login = useCallback(
    async (input: LoginInput): Promise<PublicAccount> => {
      const result = await api.login<LoginResult>(input);
      const token = result.sessao?.token;

      if (!token?.trim()) {
        throw new Error(
          "A API não retornou uma sessão válida após o login.",
        );
      }

      await saveUserSession(token);

      setSnapshot({
        status: "authenticated",
        account: result.conta,
        error: null,
      });

      return result.conta;
    },
    [],
  );

  const logout = useCallback(async (): Promise<void> => {
    let serverError: unknown = null;

    try {
      try {
        await revokeCurrentDeviceRegistration();
      } catch {
        // Logout local nunca fica bloqueado por falha de revogacao do device.
      }

      await api.logout();
    } catch (error) {
      serverError = error;
    } finally {
      await clearUserSession();
      setSnapshot(anonymousSnapshot());
    }

    if (serverError) {
      throw serverError;
    }
  }, []);

  const refreshMe = useCallback(
    async (): Promise<PublicAccount | null> => {
      const token = await loadUserSession();

      if (!token?.trim()) {
        setSnapshot(anonymousSnapshot());
        return null;
      }

      try {
        const result = await api.me<MeResult>();

        setSnapshot({
          status: "authenticated",
          account: result.conta,
          error: null,
        });

        return result.conta;
      } catch (error) {
        if (isInvalidSession(error)) {
          await clearUserSession();
          setSnapshot(anonymousSnapshot());
          return null;
        }

        setSnapshot((current) => ({
          ...current,
          status: "error",
          error: asError(error),
        }));

        throw error;
      }
    },
    [],
  );

  const value = useMemo<AuthSessionContextValue>(
    () => ({
      snapshot,
      restore,
      register,
      login,
      logout,
      refreshMe,
    }),
    [
      snapshot,
      restore,
      register,
      login,
      logout,
      refreshMe,
    ],
  );

  return (
    <AuthSessionContext.Provider value={value}>
      {children}
    </AuthSessionContext.Provider>
  );
}

export function useAuthSession(): AuthSessionContextValue {
  const value = useContext(AuthSessionContext);

  if (!value) {
    throw new Error(
      "useAuthSession deve ser usado dentro de AuthSessionProvider.",
    );
  }

  return value;
}
