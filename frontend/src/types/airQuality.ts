export interface Borough {
  borough: string;
  average_index: number;
  maximum_index: number;
  site_count: number;
  latitude: number;
  longitude: number;
}

export interface MonitoringSite {
  site_code: string;
  site_name: string;
  borough: string;
  latitude: number;
  longitude: number;
  pollutant: string;
  pollutant_name: string;
  air_quality_index: number;
  air_quality_band: string;
  recorded_at: string;
}

export interface HealthAdviceItem {
  "@Population": string;
  "@Advice": string;
}

export interface AirQualityIndexHealthAdvice {
  "@AirQualityBand": string;
  "@LowerAirQualityIndex": string;
  "@UpperAirQualityIndex": string;
  HealthAdvice: HealthAdviceItem[];
}

export interface HealthAdviceResponse {
  AirQualityIndexHealthAdvice: {
    AirQualityBanding: AirQualityIndexHealthAdvice;
  };
}