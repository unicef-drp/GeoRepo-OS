import React, {useEffect, useState} from 'react';
import PermissionDetail from '../../Permissions/PermissionDetail';
import Dataset from '../../../models/dataset';


interface DatasetPermissionInterface {
    dataset: Dataset,
    onDatasetUpdated: () => void
}

export default function DatasetPermission(props: DatasetPermissionInterface) {
    return (
        <PermissionDetail objectType={'dataset'} objectUuid={props.dataset.uuid} isReadOnly={!props.dataset.is_active} />
    )
}
