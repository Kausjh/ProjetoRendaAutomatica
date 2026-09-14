import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import { presentWatchlist } from "@/src/watchlist/watchlist-presenter";
import {
  WatchlistUpsertInput,
} from "@/src/watchlist/watchlist-types";

const api = createPublicApiClient();

export const watchlistQueryKeys = {
  all: ["watchlist"] as const,
};

export function useWatchlist(enabled = true) {
  return useQuery({
    queryKey: watchlistQueryKeys.all,
    queryFn: async () =>
      presentWatchlist(await api.getWatchlist()),
    enabled,
  });
}

export function useUpsertWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: WatchlistUpsertInput) =>
      api.putWatchlist(input.canonicalKey, {
        preco_alvo: input.targetPrice,
        notificar_queda_preco: input.notifyPriceDrop,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: watchlistQueryKeys.all,
      });
    },
  });
}

export function useDeleteWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (canonicalKey: string) =>
      api.deleteWatchlist(canonicalKey),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: watchlistQueryKeys.all,
      });
    },
  });
}
