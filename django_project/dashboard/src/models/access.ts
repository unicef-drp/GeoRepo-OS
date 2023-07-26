export default interface AccessRequestInterface {
    id: number,
    name: string,
    requester_email: string,
    type: string,
    status: string,
    submitted_on: Date
}

export interface AccessRequestDetailInterface {
    id: number,
    type: string,
    status: string,
    uuid: string,
    submitted_on: Date,
    requester_first_name?: string,
    requester_last_name?: string,
    requester_email: string,
    description: string,
    request_by_id?: number,
    approved_date?: Date,
    approved_by_id?: number,
    approver_notes?: string,
    approval_by?: string
}
