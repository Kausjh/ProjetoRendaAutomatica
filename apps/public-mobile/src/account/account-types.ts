export type AccountPreferences = Readonly<{
  priceNotificationsEnabled: boolean;
  preferredMarketplaces: readonly string[];
}>;

export type AccountPreferencesPatch = Readonly<{
  priceNotificationsEnabled: boolean;
  preferredMarketplaces: readonly string[];
}>;
