export default interface GroupInterface {
    id: number,
    name: string
}

export const createNewGroup = (): GroupInterface => {
    return {
        'id': 0,
        'name': ''
    }
}
