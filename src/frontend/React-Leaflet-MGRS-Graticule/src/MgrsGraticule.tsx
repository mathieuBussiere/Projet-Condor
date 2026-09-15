import {
  connectToGzdBoundary,
  drawLabel,
  getAdjustedLatitude,
  getAllVisibleGzds,
  getGzd,
  getLineSlope,
} from './CommonUtils';
import { llToMgrs, llToUtm, utmToLl } from './Coordinates';

import { useMap } from 'react-leaflet';
import { useEffect } from 'react';
import {GraticuleOptions} from "./types.ts";
const SW_INDEX = 0;
const NW_INDEX = 1;
const NE_INDEX = 2;

const LATITUDE_INDEX = 1;
const LONGITUDE_INDEX = 0;

const MGRS_REGEX = /([0-9]+[A-Z])([A-Z]{2})(\d+)/;
const GZD_INDEX = 1;
const HK_INDEX = 2;
const GRID_INDEX = 3;

const MgrsGraticule = (props) => {
  const map = useMap();

  useEffect(() => {
    const g = new Graticule(map, props.name, props.checked, props.options);

    return () => {
      if (g) {
        map.off('viewreset', g.reset, g);
        map.off('move', g.reset, g);
        map.off('overlayadd', g.showGraticule, g);
        map.off('overlayremove', g.clearRect, g);

        if (g.canvas && g.canvas.parentNode) {
          g.canvas.parentNode.removeChild(g.canvas);
        }
      }
    };
  }, [map, props.name, props.checked]);

  return null;
};

class Graticule {
  map: L.Map;
  name: string;
  options: GraticuleOptions;
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  currLatInterval = 8;
  currLngInterval = 6;
  mgrsGridInterval: number | null = null;

  defaultOptions: GraticuleOptions = {
    showGrid: true,
    color: '#888888',
    font: '14px Courier New',
    fontColor: '#ffffff',
    dashArray: [6, 6],
    weight: 1.5,
    gridColor: '#000',
    hkColor: '#990000',
    hkDashArray: [4, 4],
    gridFont: '14px Courier New',
    gridFontColor: '#ffffff',
    gridDashArray: [],
    hundredKMinZoom: 6,
    tenKMinZoom: 9,
    oneKMinZoom: 12,
    hundredMMinZoom: 15,
    minZoom: 0,
  };

  constructor(map: L.Map, name: string, checked: boolean, opt?: GraticuleOptions) {
    this.options = { ...this.defaultOptions, ...opt };
    this.map = map;
    this.canvas = document.createElement('canvas');
    this.canvas.classList.add('leaflet-zoom-animated');
    this.name = name.replace(/\s/g, '');
    this.canvas.classList.add(this.name);

    // Non-null assertion since we know it's a 2D canvas
    this.ctx = this.canvas.getContext('2d')!;

    this.map.on('viewreset', this.reset, this);
    this.map.on('move', this.reset, this);
    this.map.on('overlayadd', this.showGraticule, this);
    this.map.on('overlayremove', this.clearRect, this);

    if (checked) {
      this.options.showGrid = true;
      this.reset();
    } else {
      this.options.showGrid = false;
    }

    if (!this.map.getPanes().overlayPane.classList.contains(this.name)) {
      this.map.getPanes().overlayPane.appendChild(this.canvas);
    }
  }

  clearRect(e: any) {
    if (e.name === this.name) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.options.showGrid = false;
    }
  }

  showGraticule(e: any) {
    if (e.name === this.name) {
      this.options.showGrid = true;
      this.reset();
    }
  }

  reset() {
    if (!this.options.showGrid) return;

    const mapSize = this.map.getSize();
    const mapLeftTop = this.map.containerPointToLayerPoint([0, 0]);

    this.canvas.style.transform = `translate3d(${mapLeftTop.x}px,${mapLeftTop.y}px,0)`;
    this.canvas.width = mapSize.x;
    this.canvas.height = mapSize.y;

    const zoom = this.map.getZoom();
    if (zoom > (this.options.hundredMMinZoom || 15)) this.mgrsGridInterval = 100;
    else if (zoom > (this.options.oneKMinZoom || 12)) this.mgrsGridInterval = 1000;
    else if (zoom > (this.options.tenKMinZoom || 9)) this.mgrsGridInterval = 10000;
    else if (zoom > (this.options.hundredKMinZoom || 6)) this.mgrsGridInterval = 100000;
    else this.mgrsGridInterval = null;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.drawGrid(this.ctx);
    this.drawGzd(this.ctx);
  }

  drawGzd(ctx: CanvasRenderingContext2D) {
    if (!this.canvas || !this.map || !this.ctx || this.map.getZoom() < (this.options.minZoom || 0)) return;

    ctx.lineWidth = this.options.weight || 1.5;
    ctx.strokeStyle = this.options.color || '#888';
    ctx.fillStyle = this.options.color || '#888';
    ctx.setLineDash(this.options.dashArray || []);
    if (this.options.font) ctx.font = this.options.font;

    let leftTop = this.map.containerPointToLatLng({ x: 0, y: 0 });
    let rightBottom = this.map.containerPointToLatLng({ x: this.canvas.width, y: this.canvas.height });

    let pointPerLat = (leftTop.lat - rightBottom.lat) / (this.canvas.height * 0.2);
    let pointPerLon = (rightBottom.lng - leftTop.lng) / (this.canvas.width * 0.2);

    if (isNaN(pointPerLat) || isNaN(pointPerLon)) return;

    if (pointPerLat < 1) pointPerLat = 1;
    if (pointPerLon < 1) pointPerLon = 1;

    rightBottom.lat = rightBottom.lat < -90 ? -90 : parseInt((rightBottom.lat - pointPerLat).toString(), 10);
    leftTop.lat = leftTop.lat > 90 ? 90 : parseInt((leftTop.lat + pointPerLat).toString(), 10);

    if (leftTop.lng > 0 && rightBottom.lng < 0) rightBottom.lng += 360;

    rightBottom.lng = parseInt((rightBottom.lng + pointPerLon).toString(), 10);
    leftTop.lng = parseInt((leftTop.lng - pointPerLon).toString(), 10);

    for (let i = this.currLatInterval; i <= leftTop.lat; i += this.currLatInterval) {
      if (i >= rightBottom.lat) {
        if (i === 80) i = 84;
        this.drawLatitudeLine(ctx, i, leftTop.lng, rightBottom.lng);
      }
    }

    for (let i = 0; i >= rightBottom.lat; i -= this.currLatInterval) {
      if (i <= leftTop.lat) this.drawLatitudeLine(ctx, i, leftTop.lng, rightBottom.lng);
    }

    for (let i = -180; i <= rightBottom.lng + 6; i += this.currLngInterval) {
      this.drawLongitudeLine(ctx, i, leftTop.lat, rightBottom.lat);
    }
  }

  drawLatitudeLine(ctx: CanvasRenderingContext2D, tick: number, lngLeft: number, lngRight: number) {
    const leftEnd = this.map.latLngToContainerPoint({ lat: tick, lng: lngLeft });
    const rightEnd = this.map.latLngToContainerPoint({ lat: tick, lng: lngRight });
    ctx.beginPath();
    ctx.moveTo(leftEnd.x, leftEnd.y);
    ctx.lineTo(rightEnd.x, rightEnd.y);
    ctx.stroke();
  }

  drawLongitudeLine(ctx: CanvasRenderingContext2D, tick: number, latTop: number, latBottom: number) {
    if (latTop >= 84) latTop = 84;
    if (latBottom <= -80) latBottom = -80;

    const canvasTop = this.map.latLngToContainerPoint({ lat: latTop, lng: tick });
    const canvasBottom = this.map.latLngToContainerPoint({ lat: latBottom, lng: tick });
    const TOP_OF_W_SERIES_GZD = 72;

    ctx.beginPath();

    if (tick === 6) {
      const TOP_OF_V_SERIES_GZD = 64;
      const BOTTOM_OF_V_SERIES_GZD = 56;
      const RIGHT_OF_31_SERIES_GZD = 3;

      const RIGHT_TOP_OF_GZD = this.map.latLngToContainerPoint({ lat: TOP_OF_V_SERIES_GZD, lng: tick });
      const LEFT_TOP_OF_GZD = this.map.latLngToContainerPoint({ lat: TOP_OF_V_SERIES_GZD, lng: RIGHT_OF_31_SERIES_GZD });
      const LEFT_BOTTOM_OF_GZD = this.map.latLngToContainerPoint({ lat: BOTTOM_OF_V_SERIES_GZD, lng: RIGHT_OF_31_SERIES_GZD });
      const RIGHT_BOTTOM_OF_GZD = this.map.latLngToContainerPoint({ lat: BOTTOM_OF_V_SERIES_GZD, lng: tick });

      if (latTop > TOP_OF_V_SERIES_GZD && latBottom > BOTTOM_OF_V_SERIES_GZD) {
        if (latTop > TOP_OF_W_SERIES_GZD) {
          const TOP_LEFT_OF_32_SERIES_GZD = this.map.latLngToContainerPoint({ lat: TOP_OF_W_SERIES_GZD, lng: tick });
          ctx.moveTo(TOP_LEFT_OF_32_SERIES_GZD.x, TOP_LEFT_OF_32_SERIES_GZD.y);
        } else {
          ctx.moveTo(canvasTop.x, canvasTop.y);
        }
        ctx.lineTo(RIGHT_TOP_OF_GZD.x, RIGHT_TOP_OF_GZD.y);
        ctx.moveTo(LEFT_TOP_OF_GZD.x, LEFT_TOP_OF_GZD.y);
        ctx.lineTo(LEFT_TOP_OF_GZD.x, canvasBottom.y);
      } else if (latTop < TOP_OF_V_SERIES_GZD && latBottom < BOTTOM_OF_V_SERIES_GZD) {
        ctx.moveTo(LEFT_TOP_OF_GZD.x, canvasTop.y);
        ctx.lineTo(LEFT_BOTTOM_OF_GZD.x, LEFT_BOTTOM_OF_GZD.y);
        ctx.moveTo(RIGHT_BOTTOM_OF_GZD.x, RIGHT_BOTTOM_OF_GZD.y);
        ctx.lineTo(RIGHT_BOTTOM_OF_GZD.x, canvasBottom.y);
      } else if (latTop >= TOP_OF_V_SERIES_GZD && latBottom <= BOTTOM_OF_V_SERIES_GZD) {
        if (latTop > TOP_OF_W_SERIES_GZD) {
          const TOP_LEFT_OF_32_SERIES_GZD = this.map.latLngToContainerPoint({ lat: TOP_OF_W_SERIES_GZD, lng: tick });
          ctx.moveTo(TOP_LEFT_OF_32_SERIES_GZD.x, TOP_LEFT_OF_32_SERIES_GZD.y);
        } else {
          ctx.moveTo(canvasTop.x, canvasTop.y);
        }
        ctx.lineTo(RIGHT_TOP_OF_GZD.x, RIGHT_TOP_OF_GZD.y);
        ctx.moveTo(LEFT_TOP_OF_GZD.x, LEFT_TOP_OF_GZD.y);
        ctx.lineTo(LEFT_BOTTOM_OF_GZD.x, LEFT_BOTTOM_OF_GZD.y);
        ctx.moveTo(RIGHT_TOP_OF_GZD.x, LEFT_BOTTOM_OF_GZD.y);
        ctx.lineTo(RIGHT_TOP_OF_GZD.x, canvasBottom.y);
      } else if (latTop <= TOP_OF_V_SERIES_GZD && latBottom >= BOTTOM_OF_V_SERIES_GZD) {
        ctx.moveTo(LEFT_TOP_OF_GZD.x, canvasTop.y);
        ctx.lineTo(LEFT_BOTTOM_OF_GZD.x, canvasBottom.y);
      }
    } else if (tick === 12 || tick === 24 || tick === 36) {
        // Standardized Svalbard logic for intervals
        const specificLng = tick === 12 ? 9 : tick === 24 ? 21 : 33;
        if (latTop > TOP_OF_W_SERIES_GZD && latTop <= 84) {
          const TOP_LEFT = this.map.latLngToContainerPoint({ lat: latTop, lng: specificLng });
          const BOTTOM_LEFT = this.map.latLngToContainerPoint({ lat: TOP_OF_W_SERIES_GZD, lng: specificLng });
          const TOP_RIGHT = this.map.latLngToContainerPoint({ lat: TOP_OF_W_SERIES_GZD, lng: tick });
          ctx.moveTo(TOP_LEFT.x, TOP_LEFT.y);
          ctx.lineTo(BOTTOM_LEFT.x, BOTTOM_LEFT.y);
          ctx.moveTo(TOP_RIGHT.x, TOP_RIGHT.y);
          ctx.lineTo(canvasBottom.x, canvasBottom.y);
        } else {
          ctx.moveTo(canvasTop.x, canvasTop.y);
          ctx.lineTo(canvasBottom.x, canvasBottom.y);
        }
    } else if (tick === 18 || tick === 30) {
      if (latTop > TOP_OF_W_SERIES_GZD) {
        const TOP_LEFT = this.map.latLngToContainerPoint({ lat: TOP_OF_W_SERIES_GZD, lng: tick });
        ctx.moveTo(TOP_LEFT.x, TOP_LEFT.y);
      } else {
        ctx.moveTo(canvasTop.x, canvasTop.y);
      }
      ctx.lineTo(canvasBottom.x, canvasBottom.y);
    } else {
      ctx.moveTo(canvasTop.x, canvasTop.y);
      ctx.lineTo(canvasBottom.x, canvasBottom.y);
    }
    ctx.stroke();
    this.drawGzdLabels(tick);
  }

  drawGzdLabels(longitude: number) {
    for (let labelLatitude = -76; labelLatitude < 84; labelLatitude += 8) {
      let labelLongitude: number;
      if (labelLatitude === 60) {
        labelLongitude = longitude === 0 ? 1.5 : longitude === 6 ? 7.5 : longitude + 3;
      } else if (labelLatitude === 76) {
        labelLongitude = longitude === 0 ? 4.5 : longitude === 12 ? 15 : longitude === 24 ? 27 : longitude === 36 ? 37.5 : longitude + 3;
      } else {
        labelLongitude = longitude + 3;
      }

      let gzdLabel = '';
      try {
        gzdLabel = llToMgrs([labelLongitude, labelLatitude], 1).match(MGRS_REGEX)?.[GZD_INDEX] || '';
      } catch (error) { continue; }

      if (gzdLabel && !(gzdLabel === '33X' && longitude === 6) && !(gzdLabel === '35X' && longitude === 18) && !(gzdLabel === '37X' && longitude === 30)) {
        const labelXy = this.map.latLngToContainerPoint({ lat: labelLatitude, lng: labelLongitude });
        drawLabel(this.ctx, gzdLabel, this.options.fontColor || '#fff', this.options.color || '#000', labelXy);
      }
    }
  }

  _getLabelText(element: number) {
    let label = (this.mgrsGridInterval === 10000 || this.mgrsGridInterval === 1000)
        ? ((element % 100000) / 1000).toString()
        : ((element % 100000) / 100).toString();

    if (this.mgrsGridInterval === 100) label = label.padStart(3, '0');
    return label;
  }

  _drawLine(ctx: CanvasRenderingContext2D, notHkLine: boolean) {
    if (notHkLine) {
      ctx.setLineDash(this.options.gridDashArray || []);
      ctx.lineWidth = (this.options.weight || 1.5) + 1;
      ctx.strokeStyle = this.options.gridFontColor || '#fff';
      ctx.stroke();
      ctx.lineWidth = this.options.weight || 1.5;
      ctx.strokeStyle = this.options.gridColor || '#000';
      ctx.stroke();
    } else {
      ctx.lineWidth = this.options.weight || 1.5;
      ctx.strokeStyle = this.options.hkColor || '#900';
      ctx.setLineDash(this.options.hkDashArray || [4, 4]);
      ctx.stroke();
    }
  }

  getVizGzds() {
    try {
      const nw = llToMgrs([this.map.getBounds().getNorthWest().lng, this.map.getBounds().getNorthWest().lat], 1);
      const ne = llToMgrs([this.map.getBounds().getNorthEast().lng, this.map.getBounds().getNorthEast().lat], 1);
      const se = llToMgrs([this.map.getBounds().getSouthEast().lng, this.map.getBounds().getSouthEast().lat], 1);
      const sw = llToMgrs([this.map.getBounds().getSouthWest().lng, this.map.getBounds().getSouthWest().lat], 1);

      return getAllVisibleGzds(
        nw.match(MGRS_REGEX)![GZD_INDEX],
        ne.match(MGRS_REGEX)![GZD_INDEX],
        se.match(MGRS_REGEX)![GZD_INDEX],
        sw.match(MGRS_REGEX)![GZD_INDEX]
      );
    } catch {
      return null;
    }
  }

  drawGrid(ctx: CanvasRenderingContext2D) {
    if (!this.canvas || !this.map || this.map.getZoom() < (this.options.hundredKMinZoom || 6)) return;

    ctx.lineWidth = (this.options.weight || 1.5) + 0.75;
    ctx.strokeStyle = this.options.gridFontColor || '#fff';
    ctx.fillStyle = this.options.gridColor || '#000';
    ctx.setLineDash(this.options.dashArray || []);
    ctx.font = this.options.gridFont || '14px Courier New';

    const visibleGzds = this.getVizGzds();
    if (!visibleGzds || !this.mgrsGridInterval) return;

    const mapBounds = this.map.getBounds();

    visibleGzds.forEach((gzd) => {
      let gzdObject: number[][];
      try { gzdObject = getGzd(gzd); } catch { return; }

      const gzdWestBoundary = gzdObject[NW_INDEX][LONGITUDE_INDEX];
      const gzdEastBoundary = gzdObject[NE_INDEX][LONGITUDE_INDEX];
      const gzdNorthBoundary = gzdObject[NW_INDEX][LATITUDE_INDEX];
      const gzdSouthBoundary = gzdObject[SW_INDEX][LATITUDE_INDEX];

      const effectiveWestBoundary = gzdWestBoundary < mapBounds.getWest() && this.mgrsGridInterval !== 100000 ? mapBounds.getWest() : gzdWestBoundary;
      const effectiveEastBoundary = gzdEastBoundary > mapBounds.getEast() && this.mgrsGridInterval !== 100000 ? mapBounds.getEast() : gzdEastBoundary;
      const effectiveNorthBoundary = gzdNorthBoundary > mapBounds.getNorth() ? mapBounds.getNorth() : gzdNorthBoundary;
      const effectiveSouthBoundary = gzdSouthBoundary < mapBounds.getSouth() ? mapBounds.getSouth() : gzdSouthBoundary;

      const buffer = 0.00001;
      const swCornerUtm = llToUtm(effectiveSouthBoundary + buffer, effectiveWestBoundary + buffer);
      const seCornerUtm = llToUtm(effectiveSouthBoundary + buffer, effectiveEastBoundary - buffer);
      const nwCornerUtm = llToUtm(effectiveNorthBoundary - buffer, effectiveWestBoundary + buffer);
      const neCornerUtm = llToUtm(effectiveNorthBoundary - buffer, effectiveEastBoundary - buffer);

      let startingEasting = this.map.getCenter().lat >= 0 ? swCornerUtm.easting : nwCornerUtm.easting;
      let finalEasting = this.map.getCenter().lat >= 0 ? seCornerUtm.easting : neCornerUtm.easting;
      let startingNorthing = swCornerUtm.northing > seCornerUtm.northing ? seCornerUtm.northing : swCornerUtm.northing;
      let finalNorthing = nwCornerUtm.northing > neCornerUtm.northing ? nwCornerUtm.northing : neCornerUtm.northing;

      startingEasting = Math.floor(startingEasting / this.mgrsGridInterval) * this.mgrsGridInterval;
      finalEasting = Math.ceil(finalEasting / this.mgrsGridInterval) * this.mgrsGridInterval;
      startingNorthing = Math.floor(startingNorthing / this.mgrsGridInterval) * this.mgrsGridInterval;
      finalNorthing = Math.ceil(finalNorthing / this.mgrsGridInterval) * this.mgrsGridInterval;

      let eastingArray = [];
      for (let i = startingEasting; i <= finalEasting; i += this.mgrsGridInterval) eastingArray.push(i);

      let northingArray = [];
      for (let i = startingNorthing; i <= finalNorthing; i += this.mgrsGridInterval) northingArray.push(i);

      let zoneLetter = nwCornerUtm.zoneLetter;
      let zoneNumber = nwCornerUtm.zoneNumber;

      // Lines of constant Eastings
      eastingArray.forEach((eastingElem) => {
        let initialPlacementCompleted = false;
        ctx.beginPath();
        try {
          northingArray.forEach((northingElem, northingIndex, northArr) => {
            let gridIntersectionLl = utmToLl(eastingElem, northingElem, zoneNumber, zoneLetter);

            if (gridIntersectionLl.lng > gzdEastBoundary || gridIntersectionLl.lng < gzdWestBoundary) return;

            if (gridIntersectionLl.lat < gzdSouthBoundary) {
              let nextIntersectionLl = utmToLl(eastingElem, northArr[northingIndex + 1], zoneNumber, zoneLetter);
              gridIntersectionLl = connectToGzdBoundary(gridIntersectionLl, nextIntersectionLl, 'North');
            } else if (gridIntersectionLl.lat > gzdNorthBoundary) {
              let previousIntersectionLl = utmToLl(eastingElem, northArr[northingIndex - 1], zoneNumber, zoneLetter);
              gridIntersectionLl = connectToGzdBoundary(gridIntersectionLl, previousIntersectionLl, 'South');
            }

            if (Number.isFinite(gridIntersectionLl.lat) && Number.isFinite(gridIntersectionLl.lng)) {
              let gridIntersectionXy = this.map.latLngToContainerPoint(gridIntersectionLl);
              if (!initialPlacementCompleted) {
                ctx.moveTo(gridIntersectionXy.x, gridIntersectionXy.y);
                initialPlacementCompleted = true;
              } else {
                ctx.lineTo(gridIntersectionXy.x, gridIntersectionXy.y);
              }
            }
          });
          this._drawLine(ctx, eastingElem % 100000 !== 0);
        } catch (e) {}
      });

      // Lines of constant Northings
      northingArray.forEach((northingElem) => {
        let beginPathCalled = false;
        eastingArray.forEach((eastingElem, eastingIndex, eastArr) => {
          let gridIntersectionLl = utmToLl(eastingElem, northingElem, zoneNumber, zoneLetter);

          if (gridIntersectionLl.lat > gzdNorthBoundary || gridIntersectionLl.lat < gzdSouthBoundary) {
            if (!beginPathCalled) { ctx.beginPath(); beginPathCalled = true; }
            return;
          }

          let gridIntersectionXy = this.map.latLngToContainerPoint(gridIntersectionLl);
          if (!beginPathCalled) {
            if (gridIntersectionLl.lng < effectiveWestBoundary) {
              const nextGridIntersectionLl = utmToLl(eastArr[eastingIndex + 1], northingElem, zoneNumber, zoneLetter);
              if (nextGridIntersectionLl.lng < effectiveWestBoundary) return;
              const slope = getLineSlope(gridIntersectionLl, nextGridIntersectionLl);
              try {
                gridIntersectionLl.lat = getAdjustedLatitude(slope, effectiveWestBoundary, gridIntersectionLl);
                gridIntersectionLl.lng = effectiveWestBoundary;
                gridIntersectionXy = this.map.latLngToContainerPoint(gridIntersectionLl);
              } catch (e) { }
            }
            ctx.beginPath();
            beginPathCalled = true;
            ctx.moveTo(gridIntersectionXy.x, gridIntersectionXy.y);
          } else {
            if (gridIntersectionLl.lng > effectiveEastBoundary) {
              const previousGridIntersectionLl = utmToLl(eastArr[eastingIndex - 1], northingElem, zoneNumber, zoneLetter);
              const slope = getLineSlope(gridIntersectionLl, previousGridIntersectionLl);
              try {
                gridIntersectionLl.lat = getAdjustedLatitude(slope, effectiveEastBoundary, gridIntersectionLl);
                gridIntersectionLl.lng = effectiveEastBoundary;
                gridIntersectionXy = this.map.latLngToContainerPoint(gridIntersectionLl);
              } catch (e) { }
            }
            ctx.lineTo(gridIntersectionXy.x, gridIntersectionXy.y);
          }
        });
        this._drawLine(ctx, northingElem % 100000 !== 0);
      });

      // --- LABELS ---
      if (this.mgrsGridInterval === 100000) {
        // Standard 100k view: Draws letters in middle of the grid
        eastingArray.forEach((eastingElem, eastingIndex, ea) => {
          northingArray.forEach((northingElem, northingIndex, na) => {
             // Logic retained unchanged from JS version
             let currentLl = utmToLl(eastingElem, northingElem, zoneNumber, zoneLetter);
             let adjacentLlNorthing: LatLngPoint, adjacentLlEasting: LatLngPoint;

             if (ea[eastingIndex + 1]) {
               adjacentLlEasting = utmToLl(ea[eastingIndex + 1], northingElem, zoneNumber, zoneLetter);
               if (adjacentLlEasting.lng > effectiveEastBoundary) {
                 const slope = getLineSlope(currentLl, adjacentLlEasting);
                 adjacentLlEasting.lat = getAdjustedLatitude(slope, effectiveEastBoundary, adjacentLlEasting);
                 adjacentLlEasting.lng = effectiveEastBoundary;
               }
             } else return;

             if (na[northingIndex + 1]) {
               if (eastingIndex === 0) adjacentLlNorthing = utmToLl(ea[eastingIndex + 1], na[northingIndex + 1], zoneNumber, zoneLetter);
               else adjacentLlNorthing = utmToLl(eastingElem, na[northingIndex + 1], zoneNumber, zoneLetter);
             } else return;

             if (currentLl.lng < effectiveWestBoundary) {
               const slope = getLineSlope(currentLl, adjacentLlEasting);
               currentLl.lat = getAdjustedLatitude(slope, effectiveWestBoundary, currentLl);
               currentLl.lng = effectiveWestBoundary;
             } else if (currentLl.lng > effectiveEastBoundary) return;

             let labelLl = { lat: (currentLl.lat + adjacentLlNorthing.lat) / 2, lng: (currentLl.lng + adjacentLlEasting.lng) / 2 };

             try {
               const effectiveBounds = L.latLngBounds(L.latLng(effectiveNorthBoundary, effectiveWestBoundary), L.latLng(effectiveSouthBoundary, effectiveEastBoundary));
               if (labelLl && effectiveBounds.contains(labelLl)) {
                 let labelText = llToMgrs([labelLl.lng, labelLl.lat]).match(MGRS_REGEX)?.[HK_INDEX] || '';
                 if (this.map.latLngToContainerPoint(L.latLng(currentLl)).distanceTo(this.map.latLngToContainerPoint(L.latLng(adjacentLlEasting))) < ctx.measureText(labelText).width * 2) return;
                 drawLabel(this.ctx, labelText, this.options.gridFontColor || '#fff', this.options.hkColor || '#900', this.map.latLngToContainerPoint(labelLl));
               }
             } catch (e) { return; }
          });
        });
      } else {
        // ZOMMED IN: Draws numerical labels + Prepends the HK string
        eastingArray.forEach((eastingElem, eastingIndex, ea) => {
          if (eastingIndex !== 0 && eastingIndex !== ea.length - 1) {
            try {
              let labelLl = utmToLl(eastingElem, northingArray[1], zoneNumber, zoneLetter);
              let labelXy = this.map.latLngToContainerPoint({ lat: effectiveSouthBoundary, lng: labelLl.lng });

              // NEW: Get the HK prefix for this specific tick
              const hkPrefix = llToMgrs([labelLl.lng, labelLl.lat]).match(MGRS_REGEX)?.[HK_INDEX] || "";
              let labelText = `${hkPrefix} ${this._getLabelText(eastingElem)}`;

              drawLabel(this.ctx, labelText, this.options.gridFontColor || '#fff', this.options.gridColor || '#000', { x: labelXy.x, y: labelXy.y - 15 });
            } catch (e) {}
          }
        });

        northingArray.forEach((northingElem) => {
          try {
            let labelLl = utmToLl(eastingArray[eastingArray.length - 1], northingElem, zoneNumber, zoneLetter);
            let labelXy = this.map.latLngToContainerPoint({ lat: labelLl.lat, lng: effectiveEastBoundary });

            // NEW: Get the HK prefix for this specific tick
            const hkPrefix = llToMgrs([labelLl.lng, labelLl.lat]).match(MGRS_REGEX)?.[HK_INDEX] || "";
            let labelText = `${hkPrefix} ${this._getLabelText(northingElem)}`;

            drawLabel(this.ctx, labelText, this.options.gridFontColor || '#fff', this.options.gridColor || '#000', { x: labelXy.x - 15, y: labelXy.y });
          } catch (e) {}
        });
      }
    });
  }
}

export default MgrsGraticule;