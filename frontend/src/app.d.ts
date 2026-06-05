/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_GA_MEASUREMENT_ID?: string;
}

interface Window {
  dataLayer: unknown[][];
  gtag: (...args: unknown[]) => void;
}

declare module 'city-timezones' {
  export function lookupViaCity(city: string): unknown[];
  export function findFromCityStateProvince(searchString: string): unknown[];
  export function findFromIsoCode(isoCode: string): unknown[];
  const cityTimezones: {
    lookupViaCity: typeof lookupViaCity;
    findFromCityStateProvince: typeof findFromCityStateProvince;
    findFromIsoCode: typeof findFromIsoCode;
  };
  export default cityTimezones;
}
