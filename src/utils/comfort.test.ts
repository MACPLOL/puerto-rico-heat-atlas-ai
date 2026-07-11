import { describe, expect, it } from 'vitest';
import { bestOutdoorWindows, comfortBand } from './comfort';

describe('outdoor comfort planning', () => {
  it('uses activity, humidity and moderate-wind inputs transparently', () => {
    expect(comfortBand(82, null, 60, 5, 'walking')).toBe('more_comfortable');
    expect(comfortBand(82, null, 70, 1, 'exercise')).toBe('high_heat_stress');
    expect(comfortBand(null, null, null, null, 'walking')).toBeNull();
  });
  it('ranks lower-stress windows before time', () => {
    expect(bestOutdoorWindows([
      { startTime: '2026-01-01T12:00:00Z', comfort: 'use_caution' },
      { startTime: '2026-01-01T08:00:00Z', comfort: 'more_comfortable' },
    ])[0]?.startTime).toContain('08:00');
  });
});
