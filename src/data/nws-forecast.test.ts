import { describe, expect, it } from 'vitest';
import { parseHourlyForecast } from './nws-forecast';

describe('NWS hourly forecast parsing', () => {
  it('preserves nulls and converts official quantitative values', () => {
    const parsed = parseHourlyForecast({ properties: { periods: [{
      startTime: '2026-07-11T10:00:00-04:00', temperature: 30, temperatureUnit: 'C',
      relativeHumidity: { value: 70, unitCode: 'wmoUnit:percent' },
      dewpoint: { value: 20, unitCode: 'wmoUnit:degC' }, windSpeed: '5 mph',
      probabilityOfPrecipitation: { value: null, unitCode: 'wmoUnit:percent' }, shortForecast: 'Sunny',
    }] } }, 'walking');
    expect(parsed[0]).toMatchObject({ temperatureF: 86, relativeHumidity: 70, dewpointF: 68, windMph: 5, precipitationProbability: null });
  });

  it('fails clearly when the response schema is unavailable', () => {
    expect(() => parseHourlyForecast({}, 'walking')).toThrow(/missing periods/);
  });
});
