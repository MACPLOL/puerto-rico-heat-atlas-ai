import { describe, expect, it } from 'vitest';
import { parseUrlState, serializeUrlState } from './url-state';
const fallback={stationId:null,year:'2024' as const,metric:'hot_days_32' as const,unit:'F' as const,language:'en' as const};
describe('shareable URL state', () => {
  it('parses a valid state', () => expect(parseUrlState('?station=a&year=2023&metric=warm_nights_24&units=C&lang=es',['a'],['2023','2024'],fallback)).toEqual({stationId:'a',year:'2023',metric:'warm_nights_24',unit:'C',language:'es'}));
  it('falls back for malformed values, an unknown station, and unsupported year', () => {
    expect(parseUrlState('?station=nope&year=1900&metric=bad&units=K&lang=fr',['a'],['2023','2024'],fallback)).toEqual(fallback);
  });
  it('serializes URL state and omits a meaningless year for period changes', () => {
    expect(serializeUrlState({stationId:'a',year:'2024',metric:'hot_days_32',unit:'F',language:'en'})).toBe('station=a&year=2024&metric=hot_days_32&units=F&lang=en');
    expect(serializeUrlState({stationId:'a',year:'2024',metric:'delta_hot_days_32',unit:'C',language:'es'})).not.toContain('year=');
  });
});
