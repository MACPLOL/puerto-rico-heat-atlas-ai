import { describe, expect, it } from 'vitest';
import { metricText, t } from './i18n';
describe('localization', () => {
  it('returns important English and Spanish copy', () => {
    expect(t('en','linkCopied')).toBe('Link copied');
    expect(t('es','linkCopied')).toBe('Enlace copiado');
    expect(t('es','title')).toBe('Atlas de Calor de Puerto Rico');
    expect(metricText('hot_days_32','C','es')).toContain('Días calurosos');
  });
});
