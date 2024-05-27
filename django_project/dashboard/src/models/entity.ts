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
    status_text: string,
    date: Date,
    user_first_name: string,
    user_last_name: string,
    summary_text?: string
}

