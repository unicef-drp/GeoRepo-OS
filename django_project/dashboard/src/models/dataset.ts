export default interface Dataset {
    id: number,
    dataset: string,
    created_by: string,
    type: string,
    date: Date,
    uuid: string,
    source_name: string,
    geometry_similarity_threshold_new: number,
    geometry_similarity_threshold_old: number,
    tiling_status: string,
    short_code?: string,
    generate_adm0_default_views?: boolean,
    max_privacy_level?: number,
    min_privacy_level?: number,
    permissions?: string[],
    is_active?: boolean,
    is_empty?: boolean,
}


export interface DatasetDetailItemInterface {
    dataset: Dataset,
    onDatasetUpdated: () => void,
    isReadOnly?: boolean,
    onSyncStatusShouldBeUpdated: () => void
}

export interface DatasetTabElementInterface {
    title: string,
    element: React.ElementType,
    permissions: string[]
}
