import React from "react"

export interface NameField {
    id: string,
    selectedLanguage?: string,
    field: string,
    default: boolean,
    label?: string,
    duplicateError?: boolean
}

export interface IdType {
    id: string,
    name: string
}

export interface IdField {
    id: string,
    field: string,
    idType: IdType | null,
    type?: string,
    default: boolean
}

export interface UploadInterface {
    id: string,
    upload_date: string,
    layer_file: string,
    processed: boolean,
    name: string,
    level: string,
    entity_type: string,
    uploader: number,
    layer_upload_session: number,
    location_type_field?: string,
    parent_id_field?: string,
    source_field?: string,
    name_fields?: NameField[],
    id_fields?: IdField[],
    form_valid?: boolean,
    field_mapping?: string,
    is_read_only?: boolean,
    boundary_type?: string,
    privacy_level_field?: string,
    privacy_level?: string
}

export const ALLOWABLE_FILE_TYPES = [
    'application/geo+json',
    'application/geopackage+sqlite3',
    'application/zip',
    'application/json',
    'application/x-zip-compressed',
    '.gpkg'
  ]
  
export interface Level {
    [layerId: string]: string;
}
  
export const nameIdSeparator = '@+@'

export interface SummaryInterface {
    id: number,
    level: string,
    file_name: string,
    field_mapping: any,
    feature_count: number,
    properties: string
}

export interface WizardStepInterface {
    datasetId: string,
    uploadSession: string,
    isReadOnly: boolean,
    isUpdatingStep: boolean,
    setFormIsDirty: (isDirty: boolean) => void,
    canChangeTab: (tab: number) => boolean,
    isFormDirty: () => boolean,
    setEditable: (editable: boolean) => void,
    // setIsReadOnly?: (isReadOnly: boolean) => void,
    initChildTab?: number,
    canResetProgress?: boolean,
    setChildTab?: (tab: number) => void,
    onBackClicked?: () => void,
    onClickNext?: () => void,
    onReset?: Date,
    onResetProgress?: () => void,
    onCheckProgress?: () => void
}

export interface WizardStepElementInterface {
    title: string,
    element: React.ElementType
}


export interface UploadSession {
    id: string,
    name: string,
    created_at: string,
    created_by: string,
    status: string,
    datasetUuid: string,
    levels?: string[],
    comparisonReady?: boolean,
    entityUploadId?: string,
    revisedEntityUuid?: string,
    datasetStyleSource?: string,
    bbox?: [],
    types?: string[],
    revisionNumber?: number,
    uploadStatus?: string,
    progress?: string,
    datasetName?: string,
    adm0Entity?: string,
    moduleName?: string
}

export interface BoundaryData {
    label: string,
    code: string,
    area: number,
    perimeter: number
}

export interface ReviewTabInterface {
    uploadSession: UploadSession,
    updated_date?: Date
}

export interface ReviewTabElementInterface {
    summary: React.ElementType,
    detail: React.ElementType,
    moduleName: string
}

export const APPROVED = 'Approved'
export const PROCESSING_APPROVAL = 'Processing_Approval'
export const DISABLED_STATUS_LIST = [APPROVED, PROCESSING_APPROVAL]
export const getUploadStatusLabel = (status: string): string => {
    if (status === PROCESSING_APPROVAL) return 'Processing'
    return status
}

export interface BatchEntityEditInterface {
    id: number;
    uuid: string;
    status: string;
    dataset_id: number;
    name_fields?: NameField[];
    id_fields?: IdField[];
    ucode_field: string;
    error_notes: string;
    success_notes: string;
    total_count: number;
    success_count: number;
    error_count: number;
    headers: string[];
    has_file: boolean;
    step: number;
    is_read_only: boolean;
    dataset: string;
    input_file_name?: string;
    errors?: string;
    progress?: number;
    input_file_size?: number;
    has_preview?: boolean;
}
