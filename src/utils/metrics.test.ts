import { describe, expect, it } from 'vitest';
import { averageForPeriod, baselineAnomaly, celsiusToFahrenheit, collectAvailableYears, completenessLabel, coverage, formatCompleteness, metricDefinition, metricLabel, metricPercentile, metricValue, periodChange, selectedStation, summaryFor } from './metrics';
import type { StationFeature } from '../types/heat-data';
const station = (metrics: StationFeature['properties']['metrics']): StationFeature => ({ type:'Feature', geometry:{type:'Point',coordinates:[-66,18]}, properties:{id:'one',name:'One',country:'Puerto Rico',metrics} });
describe('heat metric helpers', () => {
  it('uses the sorted union of station years', () => expect(collectAvailableYears([station({hot_days_32:{'2000':1}}),station({warm_nights_24:{'1999':2,'2010':3}})])).toEqual(['1999','2000','2010']));
  it('converts Celsius to Fahrenheit and preserves null', () => { expect(celsiusToFahrenheit(0)).toBe(32); expect(celsiusToFahrenheit(null)).toBeNull(); });
  it('calculates coverage and selected year lookup', () => { const features=[station({hot_days_32:{'2000':2}}),station({hot_days_32:{'2001':4}})]; expect(coverage(features,'hot_days_32','2000')).toEqual({withData:1,total:2}); expect(metricValue(features[0]!, 'hot_days_32', '2000')).toBe(2); });
  it('calculates period changes and rejects missing early data', () => { expect(periodChange({hot_days_32:{'1961':2,'2006':5}},'hot_days_32')).toBe(3); expect(periodChange({hot_days_32:{'2006':5}},'hot_days_32')).toBeNull(); });
  it('rejects a period change when late-period data is missing', () => { expect(periodChange({hot_days_32:{'1961':2}},'hot_days_32')).toBeNull(); expect(averageForPeriod({'2006':null},2006,2025)).toBeNull(); });
  it('generates unit-aware metric labels', () => expect(metricLabel('hot_days_32','F')).toContain('90 °F'));
  it('writes human-readable hot-day and warm-night summaries', () => {
    const s = station({hot_days_32:{'2000':8},warm_nights_24:{'2000':12},valid_days:{'2000':100}});
    expect(summaryFor(s,'hot_days_32','2000','F')[0]).toContain('8 of 100 observed days');
    expect(summaryFor(s,'warm_nights_24','2000','C')[0]).toContain('12 of 100 observed days stayed');
  });
  it('handles percentile, positive/negative anomalies, and absent context', () => {
    const s = station({hot_days_32:{'2000':8},valid_days:{'2000':100},hot_days_32_percentile:{'2000':84},hot_days_32_anomaly:{'2000':12}});
    expect(metricPercentile(s,'hot_days_32','2000')).toBe(84); expect(baselineAnomaly(s,'hot_days_32','2000')).toBe(12);
    expect(summaryFor(s,'hot_days_32','2000','F').join(' ')).toContain('12 more');
    s.properties.metrics.hot_days_32_anomaly = {'2000':-4}; expect(summaryFor(s,'hot_days_32','2000','F').join(' ')).toContain('4 fewer');
    expect(metricPercentile(s,'warm_nights_24','2000')).toBeNull();
  });
  it('labels completeness and formats both threshold systems', () => {
    expect([completenessLabel(95),completenessLabel(80),completenessLabel(79)]).toEqual(['High coverage','Moderate coverage','Limited coverage']);
    expect(formatCompleteness(99.72602739726027)).toBe('99.7% complete');
    expect(formatCompleteness(100)).toBe('100% complete');
    expect(metricDefinition('hot_days_32','F')).toContain('89.6 °F'); expect(metricDefinition('hot_days_32','C')).toContain('32 °C');
  });
  it('falls back to an available station, preserves missing selected-year data, and keeps counts unchanged by unit', () => {
    const a=station({hot_days_32:{'2000':null}}), b={...station({hot_days_32:{'2000':7}}),properties:{...station({hot_days_32:{'2000':7}}).properties,id:'two',name:'San Juan (Airport)'}};
    expect(selectedStation([a,b],null,'hot_days_32','2000')?.properties.id).toBe('two');
    expect(selectedStation([a,b],'one','hot_days_32','2000')?.properties.id).toBe('one');
    expect(summaryFor(b,'hot_days_32','2000','F')[0]).toContain('7 of');
    expect(summaryFor(b,'hot_days_32','2000','C')[0]).toContain('7 of');
  });
});
