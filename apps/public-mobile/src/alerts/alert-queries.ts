import { useQuery } from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import { presentAlertList } from "@/src/alerts/alert-presenter";

const api = createPublicApiClient();

export const alertQueryKeys = {
  all: ["alerts"] as const,
  list: (limite: number, offset: number) =>
    ["alerts", "list", limite, offset] as const,
};

export function useAlertList(
  limite = 100,
  offset = 0,
) {
  return useQuery({
    queryKey: alertQueryKeys.list(limite, offset),
    queryFn: async () =>
      presentAlertList(
        await api.listAlerts({
          limite,
          offset,
        }),
      ),
  });
}
