import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import {
  presentCommunityDiscoveries,
  presentCommunityDiscoveryCreate,
} from "@/src/discoveries/discovery-presenter";

const api = createPublicApiClient();

export const communityDiscoveryQueryKeys = {
  all: ["community-discoveries"] as const,
};

export function useCommunityDiscoveries(enabled = true) {
  return useQuery({
    queryKey: communityDiscoveryQueryKeys.all,
    queryFn: async () =>
      presentCommunityDiscoveries(
        await api.listCommunityDiscoveries(),
      ),
    enabled,
  });
}

export function useCreateCommunityDiscovery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (url: string) =>
      presentCommunityDiscoveryCreate(
        await api.createCommunityDiscovery({ url }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: communityDiscoveryQueryKeys.all,
      });
    },
  });
}
