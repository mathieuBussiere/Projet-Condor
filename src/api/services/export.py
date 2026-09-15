import gpxpy
import gpxpy.gpx
import json
from xml.sax.saxutils import escape
from src.api.schemas.export import RouteExportRequest


class ExportService:
    @staticmethod
    def export_to_gpx(request: RouteExportRequest) -> str:
        """
        Convert a RouteExportRequest to GPX 1.1 format using gpxpy.

        Parameters
        ----------
        request : RouteExportRequest
            The export request with trajectory_id, start, end, and custom waypoints.

        Returns
        -------
        str
            GPX XML content as a string.
        """
        gpx = gpxpy.gpx.GPX()

        # Set metadata
        gpx.name = request.name_track
        gpx.description = "Optimized hiking route from Condor"

        # Add waypoints (start, end, and custom points)
        all_points = [request.start] + request.points + [request.end]

        for i, point in enumerate(all_points):
            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=point.lat,
                longitude=point.lng,
                name=f"WP-{i:03d}",
                description=f"Waypoint {i}",
            )
            gpx.waypoints.append(wpt)

        # Add track (route as a continuous track segment)
        if all_points:
            track = gpxpy.gpx.GPXTrack(name=request.name_track)
            gpx.tracks.append(track)

            segment = gpxpy.gpx.GPXTrackSegment()
            track.segments.append(segment)

            for point in all_points:
                segment.points.append(
                    gpxpy.gpx.GPXTrackPoint(
                        latitude=point.lat,
                        longitude=point.lng,
                    )
                )

        return gpx.to_xml()

    @staticmethod
    def export_to_geojson(request: RouteExportRequest) -> str:
        """
        Convert a RouteExportRequest to a GeoJSON FeatureCollection: one
        LineString feature for the route, plus one Point feature per
        waypoint (start, custom points, end) — mirrors the track + waypoints
        structure of export_to_gpx.

        Returns
        -------
        str
            GeoJSON content as a string (ready to write to a .geojson file).
        """
        all_points = [request.start] + request.points + [request.end]

        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    # GeoJSON coordinate order is [lng, lat], opposite of GPX/KML
                    "coordinates": [[p.lng, p.lat] for p in all_points],
                },
                "properties": {
                    "name": request.name_track,
                    "trajectory_id": request.trajectory_id,
                    "description": "Optimized hiking route from Condor",
                },
            }
        ]

        for i, point in enumerate(all_points):
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [point.lng, point.lat],
                    },
                    "properties": {
                        "name": f"WP-{i:03d}",
                        "description": f"Waypoint {i}",
                    },
                }
            )

        feature_collection = {
            "type": "FeatureCollection",
            "features": features,
        }
        return json.dumps(feature_collection, indent=2)

    @staticmethod
    def export_to_kml(request: RouteExportRequest) -> str:
        """
        Convert a RouteExportRequest to KML 2.2. Builds the XML directly
        rather than pulling in a library like simplekml, since the
        structure needed (one LineString + a handful of Placemarks) is
        small enough not to warrant the dependency.

        Returns
        -------
        str
            KML XML content as a string.
        """
        all_points = [request.start] + request.points + [request.end]
        name = escape(request.name_track)

        # KML coordinate order is lng,lat[,altitude] — same as GeoJSON, opposite of GPX.
        line_coords = " ".join(f"{p.lng},{p.lat},0" for p in all_points)

        placemarks = []
        for i, point in enumerate(all_points):
            placemarks.append(f"""    <Placemark>
          <name>{escape(f"WP-{i:03d}")}</name>
          <description>{escape(f"Waypoint {i}")}</description>
          <Point>
            <coordinates>{point.lng},{point.lat},0</coordinates>
          </Point>
        </Placemark>""")

        placemarks_xml = "\n".join(placemarks)

        return f"""<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <name>{name}</name>
        <description>Optimized hiking route from Condor</description>
        <Placemark>
          <name>{name}</name>
          <LineString>
            <tessellate>1</tessellate>
            <coordinates>{line_coords}</coordinates>
          </LineString>
        </Placemark>
    {placemarks_xml}
      </Document>
    </kml>"""
