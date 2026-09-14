import { useQuery } from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import {
  presentPriceHistory,
  presentProductDetail,
  presentProductList,
} from "@/src/offers/offer-presenter";

const api = createPublicApiClient();

export const offerQueryKeys = {
  all: ["offers"] as const,
  list: (limite: number, offset: number) =>
    ["offers", "list", limite, offset] as const,
  detail: (canonicalKey: string) =>
    ["offers", "detail", canonicalKey] as const,
  history: (canonicalKey: string, limite: number) =>
    ["offers", "history", canonicalKey, limite] as const,
};

export function useProductList(
  limite = 50,
  offset = 0,
) {
  return useQuery({
    queryKey: offerQueryKeys.list(limite, offset),
    queryFn: async () =>
      presentProductList(
        await api.listProducts({
          limite,
          offset,
        }),
      ),
  });
}

export function useProductDetail(canonicalKey: string) {
  return useQuery({
    queryKey: offerQueryKeys.detail(canonicalKey),
    queryFn: async () =>
      presentProductDetail(
        await api.getProduct(canonicalKey),
        canonicalKey,
      ),
    enabled: Boolean(canonicalKey),
  });
}

export function useProductHistory(
  canonicalKey: string,
  limite = 50,
) {
  return useQuery({
    queryKey: offerQueryKeys.history(canonicalKey, limite),
    queryFn: async () =>
      presentPriceHistory(
        await api.getProductHistory(canonicalKey, {
          limite,
          offset: 0,
        }),
      ),
    enabled: Boolean(canonicalKey),
  });
}
