export type MissionRewardStatus =
  | "locked"
  | "pending"
  | "granted";

export type MissionReward = Readonly<{
  type: string;
  amount: number;
  status: MissionRewardStatus;
  grantedAt: string | null;
}>;

export type MissionItem = Readonly<{
  code: string;
  title: string;
  description: string;
  currentProgress: number;
  targetProgress: number;
  percent: number;
  completed: boolean;
  completedAt: string | null;
  updatedAt: string | null;
  reward: MissionReward;
}>;

export type MissionsSummary = Readonly<{
  total: number;
  completed: number;
  inProgress: number;
  notStarted: number;
  rewardsPending: number;
  rewardsGranted: number;
}>;

export type MissionsSnapshot = Readonly<{
  rulesetVersion: string;
  instanceKey: string;
  summary: MissionsSummary;
  missions: readonly MissionItem[];
}>;
