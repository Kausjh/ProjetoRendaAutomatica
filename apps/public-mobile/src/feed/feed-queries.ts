import { useQuery } from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import { presentPersonalizedFeed } from "@/src/feed/feed-presenter";

const api = createPublicApiClient();

export const personalizedFeedQueryKeys = {
  all: ["personalized-feed"] as const,
  list: (limit: number, offset: number) =>
    ["personalized-feed", "list", limit, offset] as const,
};

export function usePersonalizedFeed(
  limit = 20,
  offset = 0,
  enabled = true,
) {
  return useQuery({
    queryKey: personalizedFeedQueryKeys.list(limit, offset),
    queryFn: async () =>
      presentPersonalizedFeed(
        await api.getPersonalizedFeed({
          limite: limit,
          offset,
        }),
      ),
    enabled,
  });
}
