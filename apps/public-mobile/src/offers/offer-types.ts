export type ProductCard = Readonly<{
  canonicalKey: string;
  title: string;
  marketplace: string | null;
  currentPrice: number | null;
  originalPrice: number | null;
  discountPercent: number | null;
  productUrl: string | null;
}>;

export type ProductDetail = Readonly<{
  canonicalKey: string;
  title: string;
  marketplace: string | null;
  currentPrice: number | null;
  originalPrice: number | null;
  discountPercent: number | null;
  productUrl: string | null;
  raw: Readonly<Record<string, unknown>>;
}>;

export type PriceHistoryPoint = Readonly<{
  timestamp: string | null;
  price: number | null;
  marketplace: string | null;
}>;

export type ProductListPage = Readonly<{
  items: readonly ProductCard[];
  total: number | null;
}>;
