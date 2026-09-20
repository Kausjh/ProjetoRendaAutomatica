import { useQuery } from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import {
  presentMissions,
} from "@/src/missions/mission-presenter";

const api = createPublicApiClient();

export const missionQueryKeys = {
  me: ["missions", "me"] as const,
};

export function useMissions(
  enabled = true,
) {
  return useQuery({
    queryKey: missionQueryKeys.me,
    queryFn: async () =>
      presentMissions(
        await api.getMissions()
      ),
    enabled,
  });
}
