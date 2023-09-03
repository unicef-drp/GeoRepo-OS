

export interface EntitiesFilterInterface {
    country: string[],
    level: string[],
    level_name: string[],
    type: string[],
    valid_from: Date,
    valid_to: Date,
    status: string[],
    revision: string[],
    search_text: string,
    updated_at: Date,
    privacy_level: string[],
    points?: any[]
}

export function getDefaultFilter():EntitiesFilterInterface {
    return {
        country: [],
        level: [],
        level_name: [],
        type: [],
        valid_from: null,
        valid_to: null,
        status: [],
        revision: [],
        search_text: '',
        updated_at: null,
        privacy_level: [],
        points: []
    }
}

export interface EntitiesFilterUpdateInterface {
    criteria: string,
    type: string,
    values?: string[],
    date_from?: Date,
    date_to?: Date
}

export interface EntitiesFilterPropInterface {
    filter: EntitiesFilterInterface,
    dataset_id: string,
    onFilterUpdated? : (data: EntitiesFilterUpdateInterface) => void
}

