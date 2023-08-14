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