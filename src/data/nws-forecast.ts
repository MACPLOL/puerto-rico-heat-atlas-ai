import { comfortBand, type ActivityMode, type ComfortBand } from '../utils/comfort';

export interface ForecastHour {
  startTime: string;
  temperatureF: number | null;
  relativeHumidity: number | null;
  dewpointF: number | null;
  windMph: number | null;
  precipitationProbability: number | null;
  shortForecast: string;
  comfort: ComfortBand | null;
}

type QuantitativeValue = { value?: number | null; unitCode?: string } | null;

function cToF(value: number): number { return value * 9 / 5 + 32; }

function mph(value: string | null | undefined): number | null {
  const match = value?.match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : null;
}

function quantitative(value: unknown): QuantitativeValue {
  if (!value || typeof value !== 'object') return null;
  const q = value as { value?: unknown; unitCode?: unknown };
  return typeof q.value === 'number' || q.value === null
    ? { value: q.value, unitCode: typeof q.unitCode === 'string' ? q.unitCode : undefined }
    : null;
}

export function parseHourlyForecast(payload: unknown, activity: ActivityMode): ForecastHour[] {
  const periods = (payload as { properties?: { periods?: unknown } } | null)?.properties?.periods;
  if (!Array.isArray(periods)) throw new Error('NWS hourly forecast is missing periods.');
  return periods.flatMap((raw): ForecastHour[] => {
    if (!raw || typeof raw !== 'object') return [];
    const p = raw as Record<string, unknown>;
    if (typeof p.startTime !== 'string') return [];
    const temperatureF = typeof p.temperature === 'number'
      ? (p.temperatureUnit === 'C' ? cToF(p.temperature) : p.temperature) : null;
    const humidity = quantitative(p.relativeHumidity)?.value ?? null;
    const dewpoint = quantitative(p.dewpoint);
    const dewpointF = dewpoint?.value == null ? null
      : dewpoint.unitCode?.endsWith('degF') ? dewpoint.value : cToF(dewpoint.value);
    const windMph = mph(typeof p.windSpeed === 'string' ? p.windSpeed : null);
    return [{
      startTime: p.startTime, temperatureF, relativeHumidity: humidity, dewpointF, windMph,
      precipitationProbability: quantitative(p.probabilityOfPrecipitation)?.value ?? null,
      shortForecast: typeof p.shortForecast === 'string' ? p.shortForecast : '',
      comfort: comfortBand(temperatureF, null, dewpointF, windMph, activity),
    }];
  });
}

export async function fetchNwsHourly(latitude: number, longitude: number, activity: ActivityMode,
                                     signal?: AbortSignal): Promise<ForecastHour[]> {
  const headers = { Accept: 'application/geo+json' };
  const point = await fetch(`https://api.weather.gov/points/${latitude.toFixed(4)},${longitude.toFixed(4)}`, { headers, signal });
  if (!point.ok) throw new Error(`NWS point lookup failed (HTTP ${point.status}).`);
  const pointJson = await point.json() as { properties?: { forecastHourly?: unknown } };
  const hourlyUrl = pointJson.properties?.forecastHourly;
  if (typeof hourlyUrl !== 'string' || !hourlyUrl.startsWith('https://api.weather.gov/'))
    throw new Error('NWS did not provide an hourly forecast URL for this location.');
  const forecast = await fetch(hourlyUrl, { headers, signal });
  if (!forecast.ok) throw new Error(`NWS hourly forecast failed (HTTP ${forecast.status}).`);
  return parseHourlyForecast(await forecast.json(), activity);
}
