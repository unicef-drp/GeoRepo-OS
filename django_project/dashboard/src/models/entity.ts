export interface EntityCode {
    id: number,
    default: boolean,
    code_id: number,
    value: string
}

export const createNewEntityCode = (): EntityCode => {
    return {
        'id': 0,
        'default': false,
        'code_id': 1,
        'value': ''
    }
}

export interface EntityName {
    id: number,
    default: boolean,
    language_id: number,
    name: string
}

export const createNewName = (): EntityName => {
    return {
        'id': 0,
        'default': false,
        'language_id': 1,
        'name': ''
    }
}

export default interface EntityEditInterface {
    id: number,
    type: string,
    source: string,
    privacy_level: number,
    names: EntityName[],
    codes: EntityCode[],
}