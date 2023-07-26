import React, {useEffect, useState} from 'react';
import PermissionDetail from '../Permissions/PermissionDetail';
import View from "../../models/view";


interface ViewPermissionInterface {
    view: View,
    onViewUpdated: () => void
}

export default function ViewPermission(props: ViewPermissionInterface) {
    return (
        <PermissionDetail objectType={'datasetview'} objectUuid={props.view.uuid} isReadOnly={props.view.is_read_only} />
    )
}
