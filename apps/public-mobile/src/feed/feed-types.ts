export type PersonalizedFeedItem = Readonly<{
  canonicalKey: string;
  title: string;
  category: string | null;
  brand: string | null;
  model: string | null;
  relevanceScore: number;
  reasons: readonly string[];
  inWatchlist: boolean;
  targetPrice: number | null;
  currentPrice: number | null;
  marketplace: string | null;
  identifier: string | null;
  productUrl: string | null;
  updatedAt: string | null;
}>;

export type PersonalizedFeedPage = Readonly<{
  total: number;
  limit: number;
  offset: number;
  items: readonly PersonalizedFeedItem[];
}>;
