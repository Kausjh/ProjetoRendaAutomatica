import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import * as Crypto from "expo-crypto";

import { createPublicApiClient } from "@/src/api";
import {
  presentCommunityReportCreate,
  presentCommunityReportDetail,
  presentCommunityReports,
} from "@/src/reporting/reporting-presenter";
import { CommunityReportCreateCommand } from "@/src/reporting/reporting-types";

const api = createPublicApiClient();

export const communityReportQueryKeys = {
  all: ["community-reports"] as const,
  list: (limit: number, offset: number) =>
    ["community-reports", "list", limit, offset] as const,
  detail: (reportId: string) =>
    ["community-reports", "detail", reportId] as const,
};

export function createCommunityReportIdempotencyKey(): string {
  return `mobile-${Crypto.randomUUID()}`;
}

export function useCommunityReports(
  limit = 20,
  offset = 0,
  enabled = true,
) {
  return useQuery({
    queryKey: communityReportQueryKeys.list(limit, offset),
    queryFn: async () =>
      presentCommunityReports(
        await api.listCommunityReports({
          limite: limit,
          offset,
        }),
      ),
    enabled,
  });
}

export function useCommunityReport(
  reportId: string,
  enabled = true,
) {
  const normalizedReportId = reportId.trim();

  return useQuery({
    queryKey: communityReportQueryKeys.detail(normalizedReportId),
    queryFn: async () =>
      presentCommunityReportDetail(
        await api.getCommunityReport(
          normalizedReportId,
        ),
      ),
    enabled: enabled && Boolean(normalizedReportId),
  });
}

export function useCreateCommunityReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      command: CommunityReportCreateCommand,
    ) => {
      const targetId = command.targetId.trim();

      if (!targetId) {
        throw new Error(
          "A contribuição denunciada não foi identificada.",
        );
      }

      const details =
        typeof command.details === "string" &&
        command.details.trim()
          ? command.details.trim()
          : null;

      const result = presentCommunityReportCreate(
        await api.createCommunityReport(
          {
            target_id: targetId,
            motivo: command.reason,
            detalhes: details,
          },
          createCommunityReportIdempotencyKey(),
        ),
      );

      return result;
    },
    onSuccess: async (result) => {
      queryClient.setQueryData(
        communityReportQueryKeys.detail(
          result.report.id,
        ),
        result.report,
      );

      await queryClient.invalidateQueries({
        queryKey: communityReportQueryKeys.all,
      });
    },
  });
}
