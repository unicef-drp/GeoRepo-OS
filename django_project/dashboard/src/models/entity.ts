export interface EntityCode {
    id: number,
    default: boolean,
    code_id: number,
    value: string,
    uuid?: string
}

export interface EntityName {
    id: number,
    default: boolean,
    language_id: number,
    name: string,
    uuid?: string,
    label?: string
}


export default interface EntityEditInterface {
    id: number,
    type: string,
    source: string,
    privacy_level: number,
    names: EntityName[],
    codes: EntityCode[],
    label: string,
    is_dirty: boolean
}

export interface EntityEditHistoryItemInterface {
    object_id: number,
    type: string,
    status: string,
    dataset_id: number,
    submitted_on: Date,
    user: string,
    summary?: string,
    total_count?: number,
    success_count?: number,
    error_count?: number,
    progress?: number,
}

