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