import { describe, expect, it } from 'vitest';
import { friendlyStationName, searchStations } from './stations';
import type { StationFeature } from '../types/heat-data';
const station = (id:string,name:string):StationFeature => ({type:'Feature',geometry:{type:'Point',coordinates:[-66,18]},properties:{id,name,country:'Puerto Rico',metrics:{}}});
describe('station presentation and search', () => {
  it('uses centralized friendly names and safely falls back to source names', () => {
    expect(friendlyStationName(station('RQW00011641','San Juan (Airport)'))).toBe('San Juan Airport');
    expect(friendlyStationName(station('unknown','Official Source Name'))).toBe('Official Source Name');
  });
  it('finds friendly and official names case-insensitively', () => {
    const stations=[station('RQW00011641','San Juan (Airport)'),station('x','MAYAGÜEZ, PR US')];
    expect(searchStations(stations,'san juan')).toHaveLength(1);
    expect(searchStations(stations,'airport')).toHaveLength(1);
    expect(searchStations(stations,'mayaguez')).toHaveLength(1);
  });
});
