export type WatchlistItem = Readonly<{
  canonicalKey: string;
  targetPrice: number | null;
  notifyPriceDrop: boolean;
}>;

export type WatchlistCollection = Readonly<{
  items: readonly WatchlistItem[];
}>;

export type WatchlistUpsertInput = Readonly<{
  canonicalKey: string;
  targetPrice: number | null;
  notifyPriceDrop: boolean;
}>;
