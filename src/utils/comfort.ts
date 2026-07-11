export type ActivityMode = 'walking' | 'exercise' | 'work';
export type ComfortBand = 'more_comfortable' | 'use_caution' | 'high_heat_stress' | 'consider_cooler_time';

/** Transparent planning categories; informational, not individualized medical advice. */
export function comfortBand(tempF: number | null, heatIndexF: number | null, dewpointF: number | null,
                            windMph: number | null, activity: ActivityMode): ComfortBand | null {
  if (tempF === null) return null;
  const activityPenalty: Record<ActivityMode, number> = { walking: 0, exercise: 8, work: 5 };
  const stress = (heatIndexF ?? tempF) + (dewpointF !== null && dewpointF >= 70 ? 5 : 0)
    + activityPenalty[activity] - (windMph !== null && windMph >= 3 && windMph <= 15 ? 3 : 0);
  if (stress < 85) return 'more_comfortable';
  if (stress < 95) return 'use_caution';
  if (stress < 105) return 'high_heat_stress';
  return 'consider_cooler_time';
}

export function bestOutdoorWindows(hours: { startTime: string; comfort: ComfortBand | null }[], limit = 6) {
  const rank: Record<ComfortBand, number> = { more_comfortable: 0, use_caution: 1, high_heat_stress: 2, consider_cooler_time: 3 };
  return hours.filter((hour): hour is { startTime: string; comfort: ComfortBand } => hour.comfort !== null)
    .sort((a, b) => rank[a.comfort] - rank[b.comfort] || a.startTime.localeCompare(b.startTime)).slice(0, limit);
}
