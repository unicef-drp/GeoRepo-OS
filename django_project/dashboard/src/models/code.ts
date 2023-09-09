export default interface CodeInterface {
    id: number,
    code: string
}

export const createNewCode = (): CodeInterface => {
    return {
        'id': 0,
        'code': ''
    }
}
