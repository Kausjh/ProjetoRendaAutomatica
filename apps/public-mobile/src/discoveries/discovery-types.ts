export type CommunityDiscoveryStatus =
  | "received"
  | "processing"
  | "retry"
  | "approved"
  | "rejected";

export type CommunityDiscoveryItem = Readonly<{
  id: string;
  url: string;
  marketplace: string | null;
  status: CommunityDiscoveryStatus;
  statusReason: string | null;
  canonicalKey: string | null;
  createdAt: string;
  updatedAt: string;
}>;

export type CommunityDiscoveryCollection = Readonly<{
  total: number;
  items: readonly CommunityDiscoveryItem[];
}>;

export type CommunityDiscoveryCreateResult = Readonly<{
  item: CommunityDiscoveryItem;
  duplicate: boolean;
}>;
