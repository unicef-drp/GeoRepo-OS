import React, { useState } from "react";
import DatasetDetail from "../views/Dataset/DatasetDetail";
import { DatasetTabElementInterface } from "../models/dataset"
import DatasetStyle from "../views/Dataset/Configurations/DatasetStyles";
import DatasetPermission from "../views/Dataset/Configurations/DatasetPermission";
import DatasetGeneral from "./Configurations/DatasetGeneral";
// import DatasetTilingConfig from "../views/Dataset/Configurations/DatasetTilingConfig";
import DatasetAdminLevelNames from "./Configurations/DatasetAdminLevelNames";
import DatasetEntities from "../views/Dataset/DatasetEntities";
import ViewSyncList from "../views/SyncStatus/List";
import TilingConfiguration from "../views/TilingConfig/TilingConfigRevamp";


export function NavigateComponent() {
    return (<></>)
}


export default function DatasetDetailWrapper() {
    const [tabs, setTabs] = useState<DatasetTabElementInterface[]>([
        {
            title: 'PREVIEW',
            element: DatasetEntities,
            permissions: ['Read']
        },
        {
            title: 'GENERAL',
            element: DatasetGeneral,
            permissions: ['Manage']
        },
        {
            title: 'PERMISSION',
            element: DatasetPermission,
            permissions: ['Manage']
        },
        {
            title: 'ADMIN LEVEL NAMES',
            element: DatasetAdminLevelNames,
            permissions: ['Manage']
        },
        {
            title: 'STYLE',
            element: DatasetStyle,
            permissions: ['Manage']
        },
        {
            title: 'TILING CONFIG',
            element: TilingConfiguration,
            permissions: ['Manage']
        },
        {
            title: 'UPLOAD HISTORY',
            element: NavigateComponent,
            permissions: ['Manage']
        },
        {
            title: 'VIEWS',
            element: NavigateComponent,
            permissions: ['Manage']
        },
        {
            title: 'SYNC STATUS',
            element: ViewSyncList,
            permissions: ['Manage']
        }
    ])
    return (
        <DatasetDetail moduleName={'admin_boundaries'} tabs={tabs} />
    )
}