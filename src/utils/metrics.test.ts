import { describe, expect, it } from 'vitest';
import { averageForPeriod, celsiusToFahrenheit, collectAvailableYears, coverage, metricLabel, metricValue, periodChange } from './metrics';
import type { StationFeature } from '../types/heat-data';
const station = (metrics: StationFeature['properties']['metrics']): StationFeature => ({ type:'Feature', geometry:{type:'Point',coordinates:[-66,18]}, properties:{id:'one',name:'One',country:'Puerto Rico',metrics} });
describe('heat metric helpers', () => {
  it('uses the sorted union of station years', () => expect(collectAvailableYears([station({hot_days_32:{'2000':1}}),station({warm_nights_24:{'1999':2,'2010':3}})])).toEqual(['1999','2000','2010']));
  it('converts Celsius to Fahrenheit and preserves null', () => { expect(celsiusToFahrenheit(0)).toBe(32); expect(celsiusToFahrenheit(null)).toBeNull(); });
  it('calculates coverage and selected year lookup', () => { const features=[station({hot_days_32:{'2000':2}}),station({hot_days_32:{'2001':4}})]; expect(coverage(features,'hot_days_32','2000')).toEqual({withData:1,total:2}); expect(metricValue(features[0]!, 'hot_days_32', '2000')).toBe(2); });
  it('calculates period changes and rejects missing early data', () => { expect(periodChange({hot_days_32:{'1961':2,'2006':5}},'hot_days_32')).toBe(3); expect(periodChange({hot_days_32:{'2006':5}},'hot_days_32')).toBeNull(); });
  it('rejects a period change when late-period data is missing', () => { expect(periodChange({hot_days_32:{'1961':2}},'hot_days_32')).toBeNull(); expect(averageForPeriod({'2006':null},2006,2025)).toBeNull(); });
  it('generates unit-aware metric labels', () => expect(metricLabel('hot_days_32','F')).toContain('90 °F'));
});
