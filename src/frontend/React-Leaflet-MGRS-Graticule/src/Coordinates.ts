import { forward } from 'mgrs';
import type { LatLngPoint, UtmPoint } from './types';

// MGRS-84
const a = 6378137.0; // ellip.radius;
const eccSquared = 0.00669438; // ellip.eccsq;

function utmToLl(easting: number, northing: number, zoneNumber: number, zoneLetter: string): LatLngPoint {
  return _utmToLl(easting, northing, zoneNumber, zoneLetter);
}

function llToUtm(lat: number, lng: number, resolution = 0): UtmPoint {
  return _LLtoUTM({ lat, lng });
}

/**
 * Wrapper around MGRS forward function
 * @param {number[]} point [Lng,Lat]
 * @param {number} resolution
 */
function llToMgrs(point: [number, number], resolution = 1): string {
  return forward(point, resolution);
}

function _utmToLl(UTMEasting: number, UTMNorthing: number, UTMZoneNumber: number, UTMZoneLetter: string): LatLngPoint {
  const e1 = (1 - Math.sqrt(1 - eccSquared)) / (1 + Math.sqrt(1 - eccSquared));
  const x = UTMEasting - 500000.0; // remove 500,000 meter offset for longitude
  let y = UTMNorthing;
  const ZoneNumber = UTMZoneNumber;
  const ZoneLetter = UTMZoneLetter;
  let NorthernHemisphere: number;

  if (['N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'].indexOf(ZoneLetter) !== -1) {
    NorthernHemisphere = 1;
  } else {
    NorthernHemisphere = 0;
    y -= 10000000.0;
  }

  const LongOrigin = (ZoneNumber - 1) * 6 - 180 + 3;
  const eccPrimeSquared = eccSquared / (1 - eccSquared);
  const M = y / 0.9996;
  const mu = M / (a * (1 - eccSquared / 4 - (3 * eccSquared * eccSquared) / 64 - (5 * eccSquared * eccSquared * eccSquared) / 256));

  const phi1Rad = mu +
    ((3 * e1) / 2 - (27 * e1 * e1 * e1) / 32) * Math.sin(2 * mu) +
    ((21 * e1 * e1) / 16 - (55 * e1 * e1 * e1 * e1) / 32) * Math.sin(4 * mu) +
    ((151 * e1 * e1 * e1) / 96) * Math.sin(6 * mu);
  const phi1 = toDegrees(phi1Rad);

  const N1 = a / Math.sqrt(1 - eccSquared * Math.sin(phi1Rad) * Math.sin(phi1Rad));
  const T1 = Math.tan(phi1Rad) * Math.tan(phi1Rad);
  const C1 = eccPrimeSquared * Math.cos(phi1Rad) * Math.cos(phi1Rad);
  const R1 = (a * (1 - eccSquared)) / Math.pow(1 - eccSquared * Math.sin(phi1Rad) * Math.sin(phi1Rad), 1.5);
  const D = x / (N1 * 0.9996);

  let Lat = phi1Rad -
    ((N1 * Math.tan(phi1Rad)) / R1) *
      ((D * D) / 2 -
        ((5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * eccPrimeSquared) * D * D * D * D) / 24 +
        ((61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * eccPrimeSquared - 3 * C1 * C1) * D * D * D * D * D * D) / 720);
  Lat = toDegrees(Lat);

  let Long = (D -
      ((1 + 2 * T1 + C1) * D * D * D) / 6 +
      ((5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * eccPrimeSquared + 24 * T1 * T1) * D * D * D * D * D) / 120) /
    Math.cos(phi1Rad);
  Long = LongOrigin + toDegrees(Long);
  return { lat: Lat, lng: Long };
}

function _LLtoUTM(ll: LatLngPoint): UtmPoint {
  const Lat = ll.lat;
  const Long = ll.lon || ll.lng || 0;

  const k0 = 0.9996;
  const LatRad = degToRad(Lat);
  const LongRad = degToRad(Long);

  let ZoneNumber = Math.floor((Long + 180) / 6) + 1;

  if (Long === 180) ZoneNumber = 60;
  if (Lat >= 56.0 && Lat < 64.0 && Long >= 3.0 && Long < 12.0) ZoneNumber = 32;
  if (Lat >= 72.0 && Lat < 84.0) {
    if (Long >= 0.0 && Long < 9.0) ZoneNumber = 31;
    else if (Long >= 9.0 && Long < 21.0) ZoneNumber = 33;
    else if (Long >= 21.0 && Long < 33.0) ZoneNumber = 35;
    else if (Long >= 33.0 && Long < 42.0) ZoneNumber = 37;
  }

  const LongOrigin = (ZoneNumber - 1) * 6 - 180 + 3;
  const LongOriginRad = degToRad(LongOrigin);

  const eccPrimeSquared = eccSquared / (1 - eccSquared);

  const N = a / Math.sqrt(1 - eccSquared * Math.sin(LatRad) * Math.sin(LatRad));
  const T = Math.tan(LatRad) * Math.tan(LatRad);
  const C = eccPrimeSquared * Math.cos(LatRad) * Math.cos(LatRad);
  const A = Math.cos(LatRad) * (LongRad - LongOriginRad);

  const M = a * ((1 - eccSquared / 4 - (3 * eccSquared * eccSquared) / 64 - (5 * eccSquared * eccSquared * eccSquared) / 256) * LatRad -
      ((3 * eccSquared) / 8 + (3 * eccSquared * eccSquared) / 32 + (45 * eccSquared * eccSquared * eccSquared) / 1024) * Math.sin(2 * LatRad) +
      ((15 * eccSquared * eccSquared) / 256 + (45 * eccSquared * eccSquared * eccSquared) / 1024) * Math.sin(4 * LatRad) -
      ((35 * eccSquared * eccSquared * eccSquared) / 3072) * Math.sin(6 * LatRad));

  const UTMEasting = k0 * N * (A + ((1 - T + C) * A * A * A) / 6.0 + ((5 - 18 * T + T * T + 72 * C - 58 * eccPrimeSquared) * A * A * A * A * A) / 120.0) + 500000.0;

  let UTMNorthing = k0 * (M + N * Math.tan(LatRad) * ((A * A) / 2 + ((5 - T + 9 * C + 4 * C * C) * A * A * A * A) / 24.0 + ((61 - 58 * T + T * T + 600 * C - 330 * eccPrimeSquared) * A * A * A * A * A * A) / 720.0));
  if (Lat < 0.0) UTMNorthing += 10000000.0;

  return { northing: Math.round(UTMNorthing), easting: Math.round(UTMEasting), zoneNumber: ZoneNumber, zoneLetter: getLetterDesignator(Lat) };
}

function toDegrees(rad: number): number { return (rad / Math.PI) * 180; }
function degToRad(deg: number): number { return deg * (Math.PI / 180.0); }

function getLetterDesignator(lat: number): string {
  if (84 >= lat && lat >= 72) return 'X';
  if (72 > lat && lat >= 64) return 'W';
  if (64 > lat && lat >= 56) return 'V';
  if (56 > lat && lat >= 48) return 'U';
  if (48 > lat && lat >= 40) return 'T';
  if (40 > lat && lat >= 32) return 'S';
  if (32 > lat && lat >= 24) return 'R';
  if (24 > lat && lat >= 16) return 'Q';
  if (16 > lat && lat >= 8) return 'P';
  if (8 > lat && lat >= 0) return 'N';
  if (0 > lat && lat >= -8) return 'M';
  if (-8 > lat && lat >= -16) return 'L';
  if (-16 > lat && lat >= -24) return 'K';
  if (-24 > lat && lat >= -32) return 'J';
  if (-32 > lat && lat >= -40) return 'H';
  if (-40 > lat && lat >= -48) return 'G';
  if (-48 > lat && lat >= -56) return 'F';
  if (-56 > lat && lat >= -64) return 'E';
  if (-64 > lat && lat >= -72) return 'D';
  if (-72 > lat && lat >= -80) return 'C';
  return 'Z';
}

export { utmToLl, llToUtm, llToMgrs };