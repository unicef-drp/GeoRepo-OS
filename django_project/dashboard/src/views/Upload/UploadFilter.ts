export interface UploadFilterInterface {
  id: string[],
  level_0_entity: string[],
  dataset: string[],
  type: string[],
  uploaded_by: string[],
  status: string[],
  search_text: string,
}

export function getDefaultFilter():UploadFilterInterface {
    return {
      id: [],
      level_0_entity: [],
      dataset: [],
      type: [],
      uploaded_by: [],
      status: [],
      search_text: '',
    }
}
