import { HttpApiTransport } from "@/src/api/http-transport";
import { PublicApiClient } from "@/src/api/public-api-client";
import {
  loadRuntimeConfig,
  loadUserSession,
} from "@/src/storage/secure-runtime-config";

export function createPublicApiClient(): PublicApiClient {
  const transport = new HttpApiTransport(
    loadRuntimeConfig,
    loadUserSession,
  );

  return new PublicApiClient(transport);
}
