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
