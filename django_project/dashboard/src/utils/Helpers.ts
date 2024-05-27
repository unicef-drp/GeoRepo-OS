import {useRef, useEffect} from 'react';

/**
 * Change string to singular
 */
export function toSingular(str: string) {
  let singularStr = str
  if (str[str.length - 1] === 's') {
    singularStr = singularStr.substring(0, singularStr.length - 1);
  }
  return singularStr
}

/**
 * Capitalize string
 */
export function capitalize(str: string) {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * Get file type from layer_type and filename
 */
export function getFileType(layer_type: string, filename: string): string {
  let extension = filename.split('.').pop()
  let file_type = ''
  if (layer_type === 'GEOJSON')
    file_type = extension==='geojson'?'application/geo+json':'application/json'
  else if (layer_type === 'GEOPACKAGE')
    file_type = 'application/geopackage+sqlite3'
  else if (layer_type === 'SHAPEFILE')
    file_type = 'application/zip'

  return file_type
}

/**
 * Limit input length on TextField with type = number
 */
export function limitInput(limit: number, evt: React.FormEvent<HTMLDivElement>): void {
  let inputElement = (evt.target as HTMLInputElement)
  inputElement.value = Math.max(0, parseInt(inputElement.value) ).toString().slice(0, 1)
}

/**
 * Get month name of a date object
 * @param date
 */
export function getMonthName(date: Date): string {
  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  return  months[date.getMonth()];
}

export function utcToLocalDateTimeString(date: Date): string {
  return `${date.getDate()} ${getMonthName(date)} ${date.getFullYear()} 
  ${date.getHours()}:${date.getMinutes()}:${date.getSeconds()}`
}

/**
 * Custom hook to get previous value
 */
export const usePrevious = <T extends unknown>(value: T): T | undefined => {
  const ref = useRef<T>();
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}


/**
 * Format bytes as human-readable text.
 * 
 * @param bytes Number of bytes.
 * @param si True to use metric (SI) units, aka powers of 1000. False to use 
 *           binary (IEC), aka powers of 1024.
 * @param dp Number of decimal places to display.
 * 
 * @return Formatted string.
 */
export function humanFileSize(bytes: number, si=false, dp=1) {
  const thresh = si ? 1000 : 1024;

  if (Math.abs(bytes) < thresh) {
    return bytes + ' B';
  }

  const units = si 
    ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'] 
    : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
  let u = -1;
  const r = 10**dp;

  do {
    bytes /= thresh;
    ++u;
  } while (Math.round(Math.abs(bytes) * r) / r >= thresh && u < units.length - 1);


  return bytes.toFixed(dp) + ' ' + units[u];
}
