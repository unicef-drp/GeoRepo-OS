export interface ActiveBatchReview {
    id: number,
    submitted_by: string,
    submitted_at: string,
    is_approve: boolean,
    progress: string,
    status: string
}

export interface ReviewSummaryCount {
    processing: number;
    ready_for_review: number;
}
