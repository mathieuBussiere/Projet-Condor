import { forward } from 'mgrs';
import type { LatLngPoint } from './types';

const SW_INDEX = 0;
const NW_INDEX = 1;
const NE_INDEX = 2;
const LONGITUDE_INDEX = 0;
const LATITUDE_INDEX = 1;

const TEN_K_MGRS_REGEX = /([0-9]+[A-Z])([A-Z]{2})([0-9]{2})/;
const GZD_INDEX = 1;

const latBands = 'CDEFGHJKLMNPQRSTUVWX';

function getLineSlope(pointOne: LatLngPoint, pointTwo: LatLngPoint): number {
  if (pointOne.lat === pointTwo.lat && pointOne.lng === pointTwo.lng) return 0;
  if (pointOne.lng === pointTwo.lng) return NaN;
  return (pointTwo.lat - pointOne.lat) / (pointTwo.lng - pointOne.lng);
}

function getAdjustedLatitude(slope: number, adjustedLongitude: number, unadjustedLatLong: LatLngPoint): number {
  return !isNaN(slope) ? unadjustedLatLong.lat + slope * (adjustedLongitude - unadjustedLatLong.lng) : unadjustedLatLong.lat;
}

function getAdjustedLongitude(slope: number, adjustedLatitude: number, unadjustedLatLong: LatLngPoint): number {
  if (slope === 0) throw new Error('getAdjustedLongitude: Zero slope received');
  return !isNaN(slope) ? (adjustedLatitude - unadjustedLatLong.lat + slope * unadjustedLatLong.lng) / slope : unadjustedLatLong.lng;
}

function getNextMgrsGzdCharacter(char: string): string {
  const result = String.fromCharCode(char.charCodeAt(0) + 1);
  return (result === 'I' || result === 'O') ? getNextMgrsGzdCharacter(result) : result;
}

function connectToGzdBoundary(pointOne: LatLngPoint, pointTwo: LatLngPoint, direction: 'East' | 'West' | 'North' | 'South'): LatLngPoint {
  const slope = getLineSlope(pointOne, pointTwo);
  const grid = forward([pointOne.lng, pointOne.lat], 1);
  const match = grid.match(TEN_K_MGRS_REGEX);
  if (!match) return pointTwo;

  let adjustedLongitude = 0;
  let adjustedLatitude = 0;

  switch (direction) {
    case 'East':
      adjustedLongitude = getGzd(match[GZD_INDEX])[NE_INDEX][LONGITUDE_INDEX];
      adjustedLatitude = getAdjustedLatitude(slope, adjustedLongitude, pointTwo);
      break;
    case 'West':
      adjustedLongitude = getGzd(match[GZD_INDEX])[NW_INDEX][LONGITUDE_INDEX];
      adjustedLatitude = getAdjustedLatitude(slope, adjustedLongitude, pointTwo);
      break;
    case 'North':
      adjustedLatitude = getGzd(match[GZD_INDEX])[NW_INDEX][LATITUDE_INDEX];
      adjustedLongitude = getAdjustedLongitude(slope, adjustedLatitude, pointTwo);
      const WEST_LNG_32V_BOUNDARY = 3;
      if (match[GZD_INDEX] === '31V' && adjustedLongitude < WEST_LNG_32V_BOUNDARY && pointTwo.lng > WEST_LNG_32V_BOUNDARY) {
        adjustedLatitude = getAdjustedLatitude(slope, WEST_LNG_32V_BOUNDARY, pointTwo);
        adjustedLongitude = WEST_LNG_32V_BOUNDARY;
      }
      break;
    case 'South':
      adjustedLatitude = getGzd(match[GZD_INDEX])[SW_INDEX][LATITUDE_INDEX];
      adjustedLongitude = getAdjustedLongitude(slope, adjustedLatitude, pointTwo);
      break;
  }
  return { lat: adjustedLatitude, lng: adjustedLongitude };
}

function getAllVisibleGzds(nwGzd: string, neGzd: string, seGzd: string, swGzd: string): string[] {
  const GZD_REGEX = /([0-9]+)([A-Z])/;
  const LONGITUDE_BAND_INDEX = 1;
  const LATITUDE_BAND_INDEX = 2;

  if (nwGzd === seGzd) return [nwGzd];

  const nwMatch = nwGzd.match(GZD_REGEX);
  const neMatch = neGzd.match(GZD_REGEX);
  const swMatch = swGzd.match(GZD_REGEX);

  if (!nwMatch || !neMatch || !swMatch) return [];

  const nwLongitudeBand = parseInt(nwMatch[LONGITUDE_BAND_INDEX]);
  const nwLatitudeBand = nwMatch[LATITUDE_BAND_INDEX];
  const neLongitudeBand = parseInt(neMatch[LONGITUDE_BAND_INDEX]);
  const swLatitudeBand = swMatch[LATITUDE_BAND_INDEX];

  let result: string[] = [];
  const longitudeBands: string[] = [];

  if (nwGzd === '32V') longitudeBands.push('31');

  if (nwLongitudeBand !== neLongitudeBand) {
    for (let i = nwLongitudeBand; i <= neLongitudeBand; i++) longitudeBands.push(i.toString());
    if (nwLatitudeBand !== swLatitudeBand) {
      const initialLongitudeBand = [...longitudeBands];
      let currentLatitudeBand = swLatitudeBand;
      while (currentLatitudeBand <= nwLatitudeBand) {
        for (let i = 0; i < initialLongitudeBand.length; i++) {
          result.push(initialLongitudeBand[i] + currentLatitudeBand);
        }
        currentLatitudeBand = getNextMgrsGzdCharacter(currentLatitudeBand);
      }
    } else {
      for (let i = 0; i < longitudeBands.length; i++) {
        longitudeBands[i] = longitudeBands[i] + nwLatitudeBand;
      }
      result = [...longitudeBands];
    }
  } else {
    let currentLatitudeBand = swLatitudeBand;
    while (currentLatitudeBand <= nwLatitudeBand) {
      result.push(nwLongitudeBand.toString() + currentLatitudeBand);
      currentLatitudeBand = getNextMgrsGzdCharacter(currentLatitudeBand);
    }
  }

  result = result.filter(a => a !== '32X' && a !== '34X' && a !== '36X');

  if (result.includes('31W') && !result.includes('32V')) result.push('32V');
  if (neGzd === '32V' && seGzd === '32U' && !result.includes('31U')) result.push('31U');
  if (nwGzd === '32V' && neGzd === '32V' && !result.includes('31U')) result.push('31U');

  return result;
}

function drawLabel(ctx: CanvasRenderingContext2D, labelText: string, textColor: string, backgroundColor: string, labelPosition: { x: number; y: number }) {
  const textDimensions = ctx.measureText(labelText);
  const textWidth = textDimensions.width;
  const textHeight = textDimensions.fontBoundingBoxAscent ? textDimensions.fontBoundingBoxAscent : parseInt(ctx.font, 10) - 2;

  const labelX = labelPosition.x;
  const labelY = labelPosition.y;
  ctx.fillStyle = backgroundColor;
  ctx.fillRect(labelX - textWidth / 2 - 1, labelY - textHeight + 1, textWidth + 3, textHeight + 2);
  ctx.fillStyle = textColor;
  ctx.fillText(labelText, labelX - textWidth / 2, labelY);
}

function getGzd(gzd: string): number[][] {
  const lngBand = parseInt(gzd, 10);
  const latBand = gzd.replace(lngBand.toString(), '');

  if (lngBand < 1 || lngBand > 60) throw new RangeError('longitudeBand must be between 1 and 60');
  if (latBand.length !== 1) throw new RangeError('Invalid latitudeBand provided, should be one letter');
  if (!latBands.includes(latBand)) throw new RangeError(`Invalid latitudeBand provided, valid bands: ${latBands}`);
  if (latBand === 'X' && (lngBand === 32 || lngBand === 34 || lngBand === 36)) throw new RangeError('Invalid band');

  let longitudeMin = -180 + (lngBand - 1) * 6;
  let longitudeMax = longitudeMin + 6;

  const i = latBands.indexOf(latBand);
  const latitudeMin = -80 + i * 8;
  const latitudeMax = latBand !== 'X' ? latitudeMin + 8 : latitudeMin + 12;

  if (lngBand === 31 && latBand === 'V') longitudeMax -= 3;
  else if (lngBand === 32 && latBand === 'V') longitudeMin -= 3;

  if (lngBand === 31 && latBand === 'X') longitudeMax += 3;
  else if (lngBand === 33 && latBand === 'X') { longitudeMin -= 3; longitudeMax += 3; }
  else if (lngBand === 35 && latBand === 'X') { longitudeMin -= 3; longitudeMax += 3; }
  else if (lngBand === 37 && latBand === 'X') longitudeMin -= 3;

  return [
    [longitudeMin, latitudeMin],
    [longitudeMin, latitudeMax],
    [longitudeMax, latitudeMax],
    [longitudeMax, latitudeMin],
  ];
}

export { connectToGzdBoundary, drawLabel, getAdjustedLatitude, getAdjustedLongitude, getAllVisibleGzds, getGzd, getLineSlope, getNextMgrsGzdCharacter };