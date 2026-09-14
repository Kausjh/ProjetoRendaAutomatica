import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

export type PublicPushPlatform = "android" | "ios";

export type PushTokenUnavailableReason =
  | "unsupported-platform"
  | "expo-go-remote-push-unavailable"
  | "project-id-missing"
  | "permission-denied"
  | "token-unavailable";

export type PushTokenAcquisitionResult =
  | Readonly<{
      status: "ready";
      plataforma: PublicPushPlatform;
      token: string;
    }>
  | Readonly<{
      status: "unavailable";
      reason: PushTokenUnavailableReason;
    }>;

function resolveProjectId(): string | null {
  const expoConfigProjectId = Constants.expoConfig?.extra?.eas?.projectId;
  const easConfigProjectId = Constants.easConfig?.projectId;
  const projectId =
    typeof expoConfigProjectId === "string"
      ? expoConfigProjectId
      : easConfigProjectId;

  return typeof projectId === "string" && projectId.trim()
    ? projectId.trim()
    : null;
}

function isExpoGo(): boolean {
  return Constants.expoGoConfig !== null;
}

export async function acquireExpoPushToken(): Promise<PushTokenAcquisitionResult> {
  if (Platform.OS !== "android" && Platform.OS !== "ios") {
    return {
      status: "unavailable",
      reason: "unsupported-platform",
    };
  }

  if (isExpoGo()) {
    return {
      status: "unavailable",
      reason: "expo-go-remote-push-unavailable",
    };
  }

  const projectId = resolveProjectId();

  if (!projectId) {
    return {
      status: "unavailable",
      reason: "project-id-missing",
    };
  }

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("ofertas", {
      name: "Ofertas",
      importance: Notifications.AndroidImportance.HIGH,
    });
  }

  const existingPermission = await Notifications.getPermissionsAsync();
  let permissionStatus = existingPermission.status;

  if (permissionStatus !== "granted") {
    const requestedPermission =
      await Notifications.requestPermissionsAsync();
    permissionStatus = requestedPermission.status;
  }

  if (permissionStatus !== "granted") {
    return {
      status: "unavailable",
      reason: "permission-denied",
    };
  }

  try {
    const token = (
      await Notifications.getExpoPushTokenAsync({
        projectId,
      })
    ).data.trim();

    if (!token) {
      return {
        status: "unavailable",
        reason: "token-unavailable",
      };
    }

    return {
      status: "ready",
      plataforma: Platform.OS,
      token,
    };
  } catch {
    return {
      status: "unavailable",
      reason: "token-unavailable",
    };
  }
}
