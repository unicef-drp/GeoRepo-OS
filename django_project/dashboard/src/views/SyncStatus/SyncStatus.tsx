import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import axios from "axios";
import Scrollable from '../../components/Scrollable';
import Dataset from '../../models/dataset';
import View from '../../models/view';
import '../../styles/TilingConfig.scss';
import {AddButton} from '../../components/Elements/Buttons';
import List from "../../components/List";
import {v4 as uuidv4} from "uuid";
import {EntityCode} from "../../models/entity";


const FETCH_TILING_CONFIG_URL = '/api/fetch-tiling-configs/'
const UPDATE_TILING_CONFIG_URL = '/api/update-tiling-configs/'
const TILING_CONFIGS_TEMP_CREATE_URL = '/api/tiling-configs/temporary/create/'
const TILING_CONFIGS_TEMP_DETAIL_URL = '/api/tiling-configs/temporary/detail/'
const VIEW_SYNC_LIST_URL = '/api/view-sync-list/'
const DONE_STATUS_LIST = ['Done', 'Error']

interface DatasetTilingConfigInterface {
    dataset?: Dataset,
    view?: View,
    isReadOnly?: boolean,
    session?: string,
    onTilingConfigUpdated?: () => void,
    hideActions?: boolean,
    hideBottomNotes?: boolean
}

export interface AdminLevelTiling {
    level: number,
    simplify_tolerance: number
}

export interface TilingConfig {
    zoom_level: number,
    admin_level_tiling_configs: AdminLevelTiling[]
}

interface AdminLevelTilingInterface {
    tiling_config_idx: number,
    tiling_config: TilingConfig,
    admin_level: number,
    onValueUpdated: (tilingConfigIdx: number, adminLevel: number, value: number) => void,
    onValueRemoved: (tilingConfigIdx: number, adminLevel: number) => void,
    isReadOnly?: boolean
}

interface ViewSyncStatusInterface {
    dataset?: Dataset
}

interface ViewSync {
  id: number,
  name: string,
  is_tiling_config_match: boolean,
  vector_tile_sync_status: string,
  product_sync_status: string,
  vector_tile_sync_progress: number,
  product_sync_progress: number
}


export default function ViewSyncStatus(props: ViewSyncStatusInterface) {
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)
    const [simplificationStatus, setSimplificationStatus] = useState('')
    const [simplificationProgress, setSimplificationProgress] = useState('')
    const [tilingStatus, setTilingStatus] = useState('')
    const [tilingProgress, setTilingProgress] = useState('')
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const [allFinished, setAllFinished] = useState(false)
    const [viewList, setViewList] = useState<ViewSync[]>()

    const fetchSyncStatus = () => {
        setLoading(true)
        let datasetId = props.dataset?.id
        let _fetch_url = datasetId ? `${VIEW_SYNC_LIST_URL}${datasetId}/` : VIEW_SYNC_LIST_URL
        axios.get(_fetch_url).then(
            response => {
                setLoading(false)
                setViewList(response.data)
                const productSyncStatus: string[] = response.data.reduce((res: string[], row: ViewSync) => {
                    if (!res.includes(row.vector_tile_sync_status)) {
                        res.push(row.vector_tile_sync_status)
                    }
                }, [] as string[])
                const vectorTileSyncStatus: string[] = response.data.reduce((res: string[], row: ViewSync) => {
                    if (!res.includes(row.product_sync_status)) {
                        res.push(row.product_sync_status)
                    }
                }, [] as string[])
                if (!productSyncStatus.includes('Syncing') && !vectorTileSyncStatus.includes('Syncing')) {
                    setAllFinished(true)
                }
            }
        )
    }

    const triggerSync = (viewId: number, key: string) => {

    }


    // useEffect(() => {
    //     if (!allFinished) {
    //         if (currentInterval) {
    //             clearInterval(currentInterval)
    //             setCurrentInterval(null)
    //         }
    //         const interval = setInterval(() => {
    //             fetchSyncStatus()
    //         }, 5000);
    //         setCurrentInterval(interval)
    //         return () => clearInterval(interval);
    //     }
    // }, [allFinished])

    useEffect(() => {
        fetchSyncStatus()
    }, [])

    const selectionChanged = (data: any) => {
      return
    }

    return (
        <Scrollable>
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto' }}>
                {/*<DatasetTilingConfigMatrix {...props} isReadOnly={true} hideActions={true} />*/}
                <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                    <Grid item textAlign={'right'}>
                        <AddButton
                            text={"Update all string matrices to match dataset"}
                            variant={"secondary"}
                            disabled={loading}
                            useIcon={false}
                            onClick={triggerSync} />
                    </Grid>
                    <Grid item textAlign={'right'}>
                        <AddButton
                            text={"Synchronize All"}
                            variant={"secondary"}
                            disabled={loading}
                            useIcon={false}
                            onClick={triggerSync} />
                    </Grid>
                </Grid>
                <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                  <List
                    pageName={'View Sync'}
                    listUrl={''}
                    initData={viewList}
                    isRowSelectable={true}
                    selectionChanged={selectionChanged}
                    // canRowBeSelected={canRowBeSelected}
                    editUrl={''}
                    // excludedColumns={['is_importable', 'progress', 'error_summaries', 'error_report', 'is_warning']}
                    // customOptions={customColumnOptions}
                  />
                </Grid>
            </Box>
        </Scrollable>
    )
}