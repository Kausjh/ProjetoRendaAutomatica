import { useQuery } from "@tanstack/react-query";

import { createPublicApiClient } from "@/src/api";
import {
  presentCommunityTrustEvidenceHistory,
  presentCommunityTrustProfile,
} from "@/src/trust/trust-presenter";
import { CommunityTrustEvidencePagination } from "@/src/trust/trust-types";

const api = createPublicApiClient();

export const communityTrustQueryKeys = {
  all: ["community-trust"] as const,
  profile: ["community-trust", "profile"] as const,
  evidence: (limit: number, offset: number) =>
    ["community-trust", "evidence", limit, offset] as const,
};

export function normalizeCommunityTrustEvidencePagination(
  limit = 20,
  offset = 0,
): CommunityTrustEvidencePagination {
  if (
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 100
  ) {
    throw new RangeError(
      "Community Trust limit deve estar entre 1 e 100.",
    );
  }

  if (
    !Number.isInteger(offset) ||
    offset < 0
  ) {
    throw new RangeError(
      "Community Trust offset deve ser maior ou igual a zero.",
    );
  }

  return {
    limit,
    offset,
  };
}

export function useCommunityTrustProfile() {
  return useQuery({
    queryKey: communityTrustQueryKeys.profile,
    queryFn: async () =>
      presentCommunityTrustProfile(
        await api.getCommunityTrustProfile(),
      ),
  });
}

export function useCommunityTrustEvidenceHistory(
  limit = 20,
  offset = 0,
) {
  const pagination =
    normalizeCommunityTrustEvidencePagination(
      limit,
      offset,
    );

  return useQuery({
    queryKey: communityTrustQueryKeys.evidence(
      pagination.limit,
      pagination.offset,
    ),
    queryFn: async () =>
      presentCommunityTrustEvidenceHistory(
        await api.listCommunityTrustEvidence({
          limite: pagination.limit,
          offset: pagination.offset,
        }),
      ),
  });
}
