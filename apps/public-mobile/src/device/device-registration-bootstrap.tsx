import { PropsWithChildren, useEffect } from "react";

import { useAuthSession } from "@/src/auth/auth-session-context";
import { bindCurrentDeviceRegistration } from "@/src/device/device-registration-service";

export function DeviceRegistrationBootstrap({
  children,
}: PropsWithChildren) {
  const { snapshot } = useAuthSession();

  useEffect(() => {
    if (snapshot.status !== "authenticated") {
      return;
    }

    void bindCurrentDeviceRegistration().catch(() => undefined);
  }, [snapshot.status]);

  return children;
}
