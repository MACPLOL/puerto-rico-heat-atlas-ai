import type { CoreMetric, Metric, MetricValues, StationFeature, StationMetrics, TemperatureUnit, YearKey } from '../types/heat-data';

export const DELTA_YEAR_KEY = 'late_minus_early' as YearKey;
export const CORE_METRICS: CoreMetric[] = ['hot_days_32', 'hot_days_35', 'warm_nights_24', 'oppressive_days'];
export const DELTA_METRICS: Metric[] = ['delta_hot_days_32', 'delta_warm_nights_24'];
export const isDeltaMetric = (metric: Metric): boolean => metric.startsWith('delta_');
export const celsiusToFahrenheit = (value: number | null): number | null => value === null ? null : value * 9 / 5 + 32;
export function formatTemperature(value: number | null | undefined, unit: TemperatureUnit): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
  return `${(unit === 'F' ? celsiusToFahrenheit(value) : value)?.toFixed(1)} °${unit}`;
}
export function metricLabel(metric: Metric, unit: TemperatureUnit): string {
  const t = unit === 'F' ? { hot: 90, very: 95, night: 75 } : { hot: 32, very: 35, night: 24 };
  const labels: Record<Metric, string> = {
    hot_days_32: `Hot days (Tmax ≥ ${t.hot} °${unit})`, hot_days_35: `Very hot days (Tmax ≥ ${t.very} °${unit})`,
    warm_nights_24: `Warm nights (Tmin ≥ ${t.night} °${unit})`, oppressive_days: `Oppressive days (Tmax ≥ ${t.hot} °${unit} & Tmin ≥ ${t.night} °${unit})`,
    delta_hot_days_32: 'Change in hot days (late − early)', delta_warm_nights_24: 'Change in warm nights (late − early)'
  };
  return labels[metric];
}
export function averageForPeriod(values: MetricValues | undefined, start: number, end: number): number | null {
  if (!values) return null; let sum = 0; let count = 0;
  for (const [key, value] of Object.entries(values)) { const year = Number(key); if (year >= start && year <= end && value !== null && Number.isFinite(value)) { sum += value; count++; } }
  return count ? sum / count : null;
}
export function periodChange(metrics: StationMetrics, base: CoreMetric): number | null {
  const early = averageForPeriod(metrics[base], 1961, 1980); const late = averageForPeriod(metrics[base], 2006, 2025);
  return early === null || late === null ? null : Number((late - early).toFixed(1));
}
export function metricValue(feature: StationFeature, metric: Metric, year: YearKey | null): number | null {
  const values = feature.properties.metrics[metric];
  if (isDeltaMetric(metric)) return values?.[DELTA_YEAR_KEY] ?? periodChange(feature.properties.metrics, metric.replace('delta_', '') as CoreMetric);
  return year === null ? null : values?.[year] ?? null;
}
export function collectAvailableYears(features: StationFeature[]): YearKey[] {
  const years = new Set<number>();
  for (const feature of features) for (const [metric, values] of Object.entries(feature.properties.metrics)) if (!metric.startsWith('delta_') && values) for (const key of Object.keys(values)) if (/^\d{4}$/.test(key)) years.add(Number(key));
  return [...years].sort((a, b) => a - b).map(String) as YearKey[];
}
export function coverage(features: StationFeature[], metric: Metric, year: YearKey | null): { withData: number; total: number } {
  return { withData: features.filter((feature) => metricValue(feature, metric, year) !== null).length, total: features.length };
}
export function markerColor(value: number | null, metric: Metric): string {
  if (value === null) return '#999999'; if (isDeltaMetric(metric)) return value <= -40 ? '#2166ac' : value <= -20 ? '#67a9cf' : value < 0 ? '#d1e5f0' : value < 20 ? '#fddbc7' : value < 40 ? '#ef8a62' : '#b2182b';
  return value < 30 ? '#4575b4' : value < 60 ? '#91bfdb' : value < 90 ? '#fee090' : value < 120 ? '#fdae61' : '#d73027';
}
