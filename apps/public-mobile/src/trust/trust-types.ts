export type CommunityTrustClassification =
  | "positive"
  | "negative"
  | "neutral";

export type CommunityTrustProfile = Readonly<{
  evidenceTotal: number;
  positiveTotal: number;
  negativeTotal: number;
  neutralTotal: number;
  updatedAt: string | null;
  modelVersion: number;
  numericScoreDefined: false;
}>;

export type CommunityTrustEvidenceItem = Readonly<{
  type: string;
  classification: CommunityTrustClassification;
  occurredAt: string;
}>;

export type CommunityTrustEvidenceHistoryPage = Readonly<{
  items: readonly CommunityTrustEvidenceItem[];
  limit: number;
  offset: number;
  count: number;
}>;

export type CommunityTrustEvidencePagination = Readonly<{
  limit: number;
  offset: number;
}>;
