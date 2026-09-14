import { ApiHttpError } from "@/src/api/api-error";
import { createPublicApiClient } from "@/src/api/create-public-api-client";
import {
  ensureInstallationId,
  loadInstallationId,
} from "@/src/device/device-installation";
import {
  PushTokenUnavailableReason,
  acquireExpoPushToken,
} from "@/src/device/device-push-token";

const api = createPublicApiClient();

export type DeviceBindingResult =
  | Readonly<{
      status: "bound";
      installationId: string;
    }>
  | Readonly<{
      status: "deferred";
      installationId: string;
      reason: PushTokenUnavailableReason;
    }>;

export async function bindCurrentDeviceRegistration(): Promise<DeviceBindingResult> {
  const installationId = await ensureInstallationId();
  const tokenResult = await acquireExpoPushToken();

  if (tokenResult.status !== "ready") {
    return {
      status: "deferred",
      installationId,
      reason: tokenResult.reason,
    };
  }

  await api.putDevice(installationId, {
    plataforma: tokenResult.plataforma,
    push_token: tokenResult.token,
  });

  return {
    status: "bound",
    installationId,
  };
}

export async function revokeCurrentDeviceRegistration(): Promise<boolean> {
  const installationId = await loadInstallationId();

  if (!installationId) {
    return false;
  }

  try {
    await api.deleteDevice(installationId);
    return true;
  } catch (error) {
    if (error instanceof ApiHttpError && error.status === 404) {
      return true;
    }

    throw error;
  }
}
