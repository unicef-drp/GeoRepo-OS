import React, {useEffect, useState} from 'react';
import Grid from '@mui/material/Grid';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import {RootState} from "../../app/store";
import {useAppDispatch, useAppSelector} from "../../app/hooks";
import {updateDatasetTabStatuses} from "../../reducers/datasetTabs";
import {updateViewTabStatuses} from "../../reducers/viewTabs";
import HtmlTooltip from '../../components/HtmlTooltip';
import Dataset from '../../models/dataset';
import View from '../../models/view';
import { StatusAndProgress } from '../../models/syncStatus';
import { fetchSyncStatusAPI } from '../../utils/api/TilingStatus';
import SyncProblemIcon from '@mui/icons-material/SyncProblem';
import '../../styles/TilingConfig.scss';
import CircularProgressWithLabel from '../../components/CircularProgressWithLabel';

const DONE_STATUS_LIST = ['Done', 'Error', 'synced']

interface TilingConfigStatusInterface {
    dataset?: Dataset,
    view?: View,
}

export default function TilingConfigStatus(props: TilingConfigStatusInterface) {
    const dispatch = useAppDispatch()
    const simplificationStatus = useAppSelector((state: RootState) => props.dataset ? state.datasetTabs.simplificationStatus : state.viewTabs.simplificationStatus)
    const [allFinished, setAllFinished] = useState(true)

    const fetchTilingStatus = () => {
        let _object_type = props.dataset ? 'dataset' : 'datasetview'
        let _object_uuid = props.dataset ? props.dataset.uuid : props.view?.uuid
        fetchSyncStatusAPI(_object_type, _object_uuid, (response: any, error: any) => {
           if (response) {
                let _simplification: StatusAndProgress = {
                    progress: response['simplification']['progress'],
                    status: response['simplification']['status']
                }
                let _obj_status = response['sync_status']
                if (props.dataset) {
                    dispatch(updateDatasetTabStatuses({
                        objSyncStatus: _obj_status,
                        simplificationStatus: _simplification
                    }))
                } else {
                    dispatch(updateViewTabStatuses({
                        objSyncStatus: _obj_status,
                        simplificationStatus: _simplification
                    }))
                }
                if (DONE_STATUS_LIST.includes(response['simplification']['status']) && _obj_status === 'synced') {
                    setAllFinished(true)
                } else {
                    setAllFinished(false)
                }
           } 
        })
    }

    useEffect(() => {
        if (!allFinished) {
            const interval = setInterval(() => {
                fetchTilingStatus()
            }, 5000);
            return () => clearInterval(interval);
        }
    }, [allFinished])

    useEffect(() => {
        fetchTilingStatus()
    }, [])

    const getSimplificationStatus = () => {
        if (simplificationStatus.status === 'synced') {
            return (
                <span className='tiling-status-desc-icon'>
                    <CheckCircleIcon color='success' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Done</span>
                </span>
            )
        } else if (simplificationStatus.status === 'error') {
            return (
                <span className='tiling-status-desc-icon'>
                    <ErrorIcon color='error' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Stopped with Error</span>
                </span>
            )
        } else if (simplificationStatus.status === 'out_of_sync') {
            return (
                <span className='tiling-status-desc-icon'>
                    <SyncProblemIcon color='warning' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Out of sync</span>
                </span>
            )
        } else if (simplificationStatus.status === '') {
            return <span>-</span>
        }
        return (
            <span className='tiling-status-desc-icon margin-left-small'>
                {simplificationStatus.status === 'syncing' && <CircularProgressWithLabel value={parseFloat(simplificationStatus.progress)} /> }
                <span style={{marginLeft: '5px' }}>{simplificationStatus.status === 'syncing' ? 'Syncing' : simplificationStatus.status}</span>
                {simplificationStatus.status === 'syncing' && <HtmlTooltip tooltipDescription={<p>Preview might be unavailable due to simplified geometries are being generated</p>} /> }
            </span>
        )
    }

    return (
        <Grid container flexDirection={'row'} sx={{height: '100%', alignItems: 'center'}}>
            <Grid item sx={{ display:'flex', flexDirection:'row', alignItems: 'center'}}>
                Simplification status: { getSimplificationStatus() }
            </Grid>
        </Grid>
    )
}

