export type YearKey = `${number}`;
export type TemperatureUnit = 'C' | 'F';
export type CoreMetric = 'hot_days_32' | 'hot_days_35' | 'warm_nights_24' | 'oppressive_days';
export type DeltaMetric = 'delta_hot_days_32' | 'delta_warm_nights_24';
export type Metric = CoreMetric | DeltaMetric;
export type MetricValues = Record<YearKey, number | null>;
export interface StationMetrics { [name: string]: MetricValues | undefined; }
export interface StationProperties { id: string; name: string; country: string; metrics: StationMetrics; data_start_year?: number; data_end_year?: number; valid_year_count?: number; }
export interface StationFeature { type: 'Feature'; geometry: { type: 'Point'; coordinates: [number, number] }; properties: StationProperties; }
export interface StationCollection { type: 'FeatureCollection'; features: StationFeature[]; metadata?: Record<string, unknown>; }
export interface BoundaryCollection { type: 'FeatureCollection'; features: GeoJSON.Feature[]; }
export interface AppState { year: YearKey | null; metric: Metric; unit: TemperatureUnit; playing: boolean; years: YearKey[]; stations: StationCollection | null; selectedStation: StationFeature | null; }
