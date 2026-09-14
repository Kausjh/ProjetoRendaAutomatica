import { PropsWithChildren, useEffect } from "react";

import { useAuthSession } from "@/src/auth/auth-session-context";

export function AuthSessionBootstrap({
  children,
}: PropsWithChildren) {
  const { restore } = useAuthSession();

  useEffect(() => {
    void restore();
  }, [restore]);

  return children;
}
