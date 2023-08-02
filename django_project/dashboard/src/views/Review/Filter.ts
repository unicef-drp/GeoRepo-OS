export interface ReviewFilterInterface {
  level_0_entity: string[],
  upload: string[],
  revision: string[],
  dataset: string[],
  status: string[],
  search_text: string
}

export function getDefaultFilter():ReviewFilterInterface {
    return {
      level_0_entity: [],
      upload: [],
      revision: [],
      dataset: [],
      status: [],
      search_text: ''
    }
}