import type { StationFeature } from '../types/heat-data';

/** Public-facing names are intentionally kept separate from NOAA source names. */
const DISPLAY_NAMES: Record<string, string> = {
  RQC00660158: 'Aibonito',
  RQC00660410: 'Arecibo',
  RQC00660426: 'Arecibo Observatory',
  RQC00663657: 'Fajardo',
  RQC00667292: 'Ponce',
  RQW00011630: 'Ceiba – Roosevelt Roads',
  RQW00011641: 'San Juan Airport'
};

export function friendlyStationName(feature: Pick<StationFeature, 'properties'>): string {
  return DISPLAY_NAMES[feature.properties.id] ?? feature.properties.name;
}

export function normalizeSearch(value: string): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
}

export function searchStations(features: StationFeature[], query: string): StationFeature[] {
  const term = normalizeSearch(query);
  if (!term) return features;
  return features.filter((feature) => normalizeSearch(`${friendlyStationName(feature)} ${feature.properties.name} ${feature.properties.id}`).includes(term));
}
