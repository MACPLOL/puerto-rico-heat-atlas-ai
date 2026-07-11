import type { Metric, TemperatureUnit, YearKey } from '../types/heat-data';
import type { Language } from './i18n';

const metrics: Metric[] = ['hot_days_32','hot_days_35','warm_nights_24','oppressive_days','delta_hot_days_32','delta_warm_nights_24'];
export interface UrlState { stationId: string | null; year: YearKey | null; metric: Metric; unit: TemperatureUnit; language: Language; }
export function parseUrlState(search: string, stationIds: string[], years: YearKey[], fallback: UrlState): UrlState {
  const p = new URLSearchParams(search); const metric = metrics.includes(p.get('metric') as Metric) ? p.get('metric') as Metric : fallback.metric;
  const unit = p.get('units') === 'C' || p.get('units') === 'F' ? p.get('units') as TemperatureUnit : fallback.unit;
  const language = p.get('lang') === 'es' || p.get('lang') === 'en' ? p.get('lang') as Language : fallback.language;
  const stationId = stationIds.includes(p.get('station') ?? '') ? p.get('station') : null;
  const requestedYear = p.get('year') as YearKey | null;
  return { stationId, year: !metric.startsWith('delta_') && requestedYear && years.includes(requestedYear) ? requestedYear : fallback.year, metric, unit, language };
}
export function serializeUrlState(state: UrlState): string {
  const p = new URLSearchParams(); if (state.stationId) p.set('station',state.stationId); if (!state.metric.startsWith('delta_') && state.year) p.set('year',state.year); p.set('metric',state.metric); p.set('units',state.unit); p.set('lang',state.language); return p.toString();
}
