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

export interface reviewTableRowInterface {
  id: number,
  level_0_entity: string,
  upload: string,
  dataset: string,
  start_date: string,
  revision: number,
  status: string,
  submitted_by: string,
  module: string,
  is_comparison_ready: string
}

