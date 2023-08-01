export interface ViewsFilterInterface {
  tags: string[],
  mode: string[],
  dataset: string[],
  is_default: string[],
  min_privacy: string[],
  max_privacy: string[],
  search_text: string,
}

export function getDefaultFilter():ViewsFilterInterface {
    return {
      tags: [],
      mode: [],
      dataset: [],
      is_default: [],
      min_privacy: [],
      max_privacy: [],
      search_text: '',
    }
}
