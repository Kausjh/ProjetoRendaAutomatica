export type AlertCard = Readonly<{
  id: string;
  type: string;
  title: string;
  message: string | null;
  canonicalKey: string | null;
  marketplace: string | null;
  previousPrice: number | null;
  currentPrice: number | null;
  occurredAt: string | null;
}>;

export type AlertListPage = Readonly<{
  items: readonly AlertCard[];
  total: number | null;
}>;
