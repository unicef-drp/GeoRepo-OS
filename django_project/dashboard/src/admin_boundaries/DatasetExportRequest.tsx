import React from 'react';
import Dataset from '../models/dataset';
import RequestDownload from '../views/Export/ExportRequest';


interface DatasetExportRequestProps {
    dataset: Dataset,
    onDatasetUpdated: () => void
}

export default function DatasetExportRequest(props: DatasetExportRequestProps) {
    const { dataset } = props;

    return (
        <RequestDownload requestObject={dataset} is_view={false} />
    )
}
