import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import {
  AccountPreferencesPatch,
} from "@/src/account/account-types";
import {
  presentAccountPreferences,
} from "@/src/account/account-presenter";

const api = createPublicApiClient();

export const accountQueryKeys = {
  preferences: ["account", "preferences"] as const,
};

export function useAccountPreferences(enabled = true) {
  return useQuery({
    queryKey: accountQueryKeys.preferences,
    queryFn: async () =>
      presentAccountPreferences(await api.getPreferences()),
    enabled,
  });
}

export function useSaveAccountPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (patch: AccountPreferencesPatch) =>
      api.patchPreferences({
        notificacoes_preco_habilitadas:
          patch.priceNotificationsEnabled,
        marketplaces_preferidos: [
          ...patch.preferredMarketplaces,
        ],
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: accountQueryKeys.preferences,
      });
    },
  });
}
