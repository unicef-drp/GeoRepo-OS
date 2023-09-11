export default interface NameInterface {
    id: number,
    default: boolean,
    name: string
}

export const createNewName = (): NameInterface => {
    return {
        'id': 0,
        'default': false,
        'name': ''
    }
}
