export type GamificationProfile = Readonly<{
  xpTotal: number;
  level: number;
  reputationTotal: number;
  eventsTotal: number;
  updatedAt: string | null;
}>;

export type GamificationLevelProgress = Readonly<{
  currentLevel: number;
  xpTotal: number;
  levelStartXp: number;
  nextLevelXp: number | null;
  xpInLevel: number;
  xpNeededInLevel: number | null;
  xpRemaining: number;
  percent: number;
  maxLevel: boolean;
}>;

export type GamificationAchievement = Readonly<{
  code: string;
  name: string;
  description: string;
  badge: string | null;
  unlocked: boolean;
  currentProgress: number;
  targetProgress: number;
}>;

export type GamificationSnapshot = Readonly<{
  profile: GamificationProfile;
  levelProgress: GamificationLevelProgress;
  achievements: readonly GamificationAchievement[];
  unlockedBadges: readonly string[];
  rulesetVersion: string;
}>;
