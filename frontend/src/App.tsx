import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Tooltip,
  useMapEvents,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import type {
  Borough,
  MonitoringSite,
  HealthAdviceResponse,
} from "./types/airQuality";

const API = "http://127.0.0.1:8000/api";

// Update the zoom level whenever the user zooms the map.
function ZoomHandler({
  onZoomChange,
}: {
  onZoomChange: (zoom: number) => void;
}) {
  useMapEvents({
    zoomend(event) {
      onZoomChange(event.target.getZoom());
    },
  });

  return null;
}

// Colour markers according to the air quality index.
function getColour(index: number | null | undefined): string {
  if (index == null) return "grey";
  if (index <= 3) return "green";
  if (index <= 6) return "orange";
  return "red";
}

function App() {
  const [boroughs, setBoroughs] = useState<Borough[]>([]);
  const [sites, setSites] = useState<MonitoringSite[]>([]);

  const [zoom, setZoom] = useState(9);
  const [error, setError] = useState<string | null>(null);

  const [selectedBorough, setSelectedBorough] = useState<string | null>(
    null
  );
  const [boroughReadings, setBoroughReadings] = useState<MonitoringSite[]>(
    []
  );
  const [loadingBorough, setLoadingBorough] = useState(false);
  const [panelError, setPanelError] = useState<string | null>(null);

  const [healthAdvice, setHealthAdvice] = useState<
    Record<number, HealthAdviceResponse>
  >({});

  // Fetch the initial borough and monitoring-site data.
  useEffect(() => {
    async function fetchData() {
      try {
        const [boroughResponse, siteResponse] = await Promise.all([
          fetch(`${API}/boroughs`),
          fetch(`${API}/sites`),
        ]);

        if (!boroughResponse.ok || !siteResponse.ok) {
          throw new Error("Failed to fetch air quality data.");
        }

        const boroughData: Borough[] = await boroughResponse.json();
        const siteData: MonitoringSite[] = await siteResponse.json();

        setBoroughs(boroughData);
        setSites(siteData);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "An unexpected error occurred."
        );
      }
    }

    fetchData();
  }, []);

  // Fetch readings for the selected borough.
  async function selectBorough(borough: string) {
    setSelectedBorough(borough);
    setLoadingBorough(true);
    setPanelError(null);
    setBoroughReadings([]);

    try {
      const response = await fetch(
        `${API}/boroughs/${encodeURIComponent(borough)}/sites`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch borough readings.");
      }

      const data: MonitoringSite[] = await response.json();
      setBoroughReadings(data);
    } catch (err) {
      setPanelError(
        err instanceof Error ? err.message : "Failed to load borough data."
      );
    } finally {
      setLoadingBorough(false);
    }
  }

  // Fetch official ERG health advice for each distinct index.
  useEffect(() => {
    const indexes = [
      ...new Set(
        boroughReadings.map((reading) => reading.air_quality_index)
      ),
    ].filter((index) => Number.isFinite(index));

    if (indexes.length === 0) return;

    let cancelled = false;

    async function fetchAdvice() {
      try {
        const results = await Promise.all(
          indexes.map(async (index) => {
            const response = await fetch(`${API}/health-advice/${index}`);

            if (!response.ok) {
              throw new Error(`Failed to fetch advice for index ${index}.`);
            }

            const data: HealthAdviceResponse = await response.json();

            return [index, data] as const;
          })
        );

        if (!cancelled) {
          setHealthAdvice((previous) => ({
            ...previous,
            ...Object.fromEntries(results),
          }));
        }
      } catch (err) {
        console.error("Failed to fetch health advice:", err);
      }
    }

    fetchAdvice();

    return () => {
      cancelled = true;
    };
  }, [boroughReadings]);

  // Group readings by monitoring site.
  const groupedSites = boroughReadings.reduce<
    Record<string, MonitoringSite[]>
  >((groups, reading) => {
    if (!groups[reading.site_code]) {
      groups[reading.site_code] = [];
    }

    groups[reading.site_code].push(reading);

    return groups;
  }, {});

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  return (
    <div className="app">
      <h1>London Air Quality</h1>

      <div className="map-container">
        <MapContainer
          center={[51.5072, -0.1276]}
          zoom={9}
          style={{ height: "650px", width: "100%" }}
        >
          <ZoomHandler onZoomChange={setZoom} />

          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Borough markers at lower zoom levels. */}
          {zoom < 12 &&
            boroughs.map((borough) => (
              <CircleMarker
                key={borough.borough}
                center={[borough.latitude, borough.longitude]}
                radius={10}
                pathOptions={{
                  color: getColour(borough.average_index),
                  fillColor: getColour(borough.average_index),
                  fillOpacity: 0.7,
                }}
                eventHandlers={{
                  click: () => selectBorough(borough.borough),
                }}
              >
                <Tooltip>
                  <strong>{borough.borough}</strong>
                  <br />
                  Average index: {borough.average_index}
                  <br />
                  Maximum index: {borough.maximum_index}
                  <br />
                  Monitoring sites: {borough.site_count}
                  <br />
                  Click to view borough readings
                </Tooltip>
              </CircleMarker>
            ))}

          {/* Individual monitoring sites at higher zoom levels. */}
          {zoom >= 12 &&
            sites.map((site) => (
              <CircleMarker
                key={site.site_code}
                center={[site.latitude, site.longitude]}
                radius={7}
                pathOptions={{
                  color: getColour(site.air_quality_index),
                  fillColor: getColour(site.air_quality_index),
                  fillOpacity: 0.8,
                }}
                eventHandlers={{
                  click: () => selectBorough(site.borough),
                }}
              >
                <Tooltip>
                  <strong>{site.site_name}</strong>
                  <br />
                  Borough: {site.borough}
                  <br />
                  Pollutant: {site.pollutant_name}
                  <br />
                  Index: {site.air_quality_index}
                  <br />
                  Band: {site.air_quality_band}
                </Tooltip>
              </CircleMarker>
            ))}
        </MapContainer>
      </div>

      {/* Selected borough information panel. */}
      {selectedBorough && (
        <div className="borough-panel">
          <div className="panel-header">
            <h2>{selectedBorough}</h2>

            <button
              onClick={() => {
                setSelectedBorough(null);
                setBoroughReadings([]);
                setPanelError(null);
              }}
            >
              Close
            </button>
          </div>

          {loadingBorough && <p>Loading borough readings...</p>}

          {panelError && (
            <p className="error-message">{panelError}</p>
          )}

          {!loadingBorough &&
            !panelError &&
            Object.keys(groupedSites).length === 0 && (
              <p>No readings available for this borough.</p>
            )}

          {!loadingBorough &&
            Object.entries(groupedSites).map(([siteCode, readings]) => {
              const firstReading = readings[0];

              return (
                <div className="site-card" key={siteCode}>
                  <h3>{firstReading.site_name}</h3>

                  {readings.map((reading, index) => {
                    const advice =
                      healthAdvice[reading.air_quality_index]
                        ?.AirQualityIndexHealthAdvice.AirQualityBanding;

                    return (
                      <div className="pollutant-row" key={`${reading.pollutant}-${index}`}>
                        <h4>{reading.pollutant_name}</h4>

                        <p>
                          Index: <strong>{reading.air_quality_index}</strong>
                        </p>

                        <p>
                          Band: <strong>{reading.air_quality_band}</strong>
                        </p>

                        <p>
                          Recorded:{" "}
                          {reading.recorded_at
                            ? new Date(reading.recorded_at).toLocaleString()
                            : "Unknown"}
                        </p>

                        {advice && (
                          <div className="health-advice">
                            <h4>
                              {advice["@AirQualityBand"]} air quality
                            </h4>

                            <p>
                              Index range:{" "}
                              {advice["@LowerAirQualityIndex"]}–
                              {advice["@UpperAirQualityIndex"]}
                            </p>

                            {advice.HealthAdvice.map((item) => (
                              <div key={item["@Population"]}>
                                <strong>{item["@Population"]}</strong>
                                <p>{item["@Advice"]}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}

export default App;