export type CommunityReportReason =
  | "spam"
  | "fraud"
  | "malicious_link"
  | "abuse"
  | "off_topic"
  | "duplicate"
  | "other";

export type CommunityReportStatus =
  | "received"
  | "under_review"
  | "resolved";

export type CommunityReportSummary = Readonly<{
  id: string;
  targetType: "community_discovery";
  targetId: string;
  reason: CommunityReportReason;
  status: CommunityReportStatus;
  createdAt: string;
  updatedAt: string;
}>;

export type CommunityReportDetail = CommunityReportSummary &
  Readonly<{
    details: string | null;
  }>;

export type CommunityReportPage = Readonly<{
  items: readonly CommunityReportSummary[];
  limit: number;
  offset: number;
  count: number;
}>;

export type CommunityReportCreateCommand = Readonly<{
  targetId: string;
  reason: CommunityReportReason;
  details?: string | null;
}>;

export type CommunityReportCreateResult = Readonly<{
  report: CommunityReportDetail;
  created: boolean;
  idempotentReplay: boolean;
}>;
