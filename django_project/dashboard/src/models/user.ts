export default interface UserInterface {
    id: number,
    first_name: string,
    last_name: string,
    email: string,
    username: string,
    role: string,
    is_active: boolean,
    joined_date: string,
    last_login: string
}

export interface APIKeyInterface {
    user_id: number,
    api_key?: string,
    created: string,
    platform?: string
    is_active: boolean
}
