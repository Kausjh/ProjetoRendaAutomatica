import { useQuery } from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import {
  presentGamification,
} from "@/src/gamification/gamification-presenter";

const api = createPublicApiClient();

export const gamificationQueryKeys = {
  me: ["gamification", "me"] as const,
};

export function useGamification(
  enabled = true,
) {
  return useQuery({
    queryKey: gamificationQueryKeys.me,
    queryFn: async () =>
      presentGamification(
        await api.getGamification()
      ),
    enabled,
  });
}
