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
import { fetchTilingStatusAPI } from '../../utils/api/TilingStatus';
import '../../styles/TilingConfig.scss';

const DONE_STATUS_LIST = ['Done', 'Error']

interface TilingConfigStatusInterface {
    dataset?: Dataset,
    view?: View,
}

export default function TilingConfigStatus(props: TilingConfigStatusInterface) {
    const dispatch = useAppDispatch()
    const simplificationStatus = useAppSelector((state: RootState) => props.dataset ? state.datasetTabs.simplificationStatus : state.viewTabs.simplificationStatus)
    const tilingStatus = useAppSelector((state: RootState) => props.dataset ? state.datasetTabs.tilingStatus : state.viewTabs.tilingStatus)
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const [allFinished, setAllFinished] = useState(false)

    const fetchTilingStatus = () => {
        let _object_type = props.dataset ? 'dataset' : 'datasetview'
        let _object_uuid = props.dataset ? props.dataset.uuid : props.view?.uuid
        fetchTilingStatusAPI(_object_type, _object_uuid, (response: any, error: any) => {
           if (response) {
                let _simplification: StatusAndProgress = {
                    progress: response['simplification']['progress'],
                    status: response['simplification']['status']
                }
                let _tiling: StatusAndProgress = {
                    progress: response['vector_tiles']['progress'],
                    status: response['vector_tiles']['status']
                }
                if (props.dataset) {
                    dispatch(updateDatasetTabStatuses([_simplification, _tiling]))
                } else {
                    dispatch(updateViewTabStatuses([_simplification, _tiling]))
                }                
                if (DONE_STATUS_LIST.includes(response['simplification']['status']) && DONE_STATUS_LIST.includes(response['vector_tiles']['status'])) {
                    setAllFinished(true)
                }
           } 
        })
    }

    useEffect(() => {
        if (!allFinished) {
            if (currentInterval) {
                clearInterval(currentInterval)
                setCurrentInterval(null)
            }
            const interval = setInterval(() => {
                fetchTilingStatus()
            }, 3000);
            setCurrentInterval(interval)
            return () => clearInterval(interval);
        }
    }, [allFinished])

    useEffect(() => {
        fetchTilingStatus()
    }, [])

    const getTilingStatus = () => {
        if (tilingStatus.status === 'Done') {
            return (
                <span className='tiling-status-desc-icon'>
                    <CheckCircleIcon color='success' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Done</span>
                </span>
            )
        } else if (tilingStatus.status === 'Error') {
            return (
                <span className='tiling-status-desc-icon'>
                    <ErrorIcon color='error' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Stopped with Error</span>
                </span>
            )
        } else if (tilingStatus.status === '') {
            return <span>-</span>
        }
        return (
            <span className='tiling-status-desc-icon margin-left-small'>
                {tilingStatus.status === 'Processing' && <CircularProgress size={18} /> }
                <span style={{marginLeft: '5px' }}>{tilingStatus.status}{tilingStatus.status === 'Processing' && tilingStatus.progress ? ` ${tilingStatus.progress}%`:''}</span>
            </span>
        )
    }

    const getSimplificationStatus = () => {
        if (simplificationStatus.status === 'Done') {
            return (
                <span className='tiling-status-desc-icon'>
                    <CheckCircleIcon color='success' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Done</span>
                </span>
            )
        } else if (simplificationStatus.status === 'Error') {
            return (
                <span className='tiling-status-desc-icon'>
                    <ErrorIcon color='error' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Stopped with Error</span>
                </span>
            )
        } else if (simplificationStatus.status === '') {
            return <span>-</span>
        }
        return (
            <span className='tiling-status-desc-icon margin-left-small'>
                {simplificationStatus.status === 'Processing' && <CircularProgress size={18} /> }
                <span style={{marginLeft: '5px' }}>{simplificationStatus.status === 'Processing' && simplificationStatus.progress ? ` ${simplificationStatus.progress}`:''}</span>
                {simplificationStatus.status === 'Processing' && <HtmlTooltip tooltipDescription={<p>Preview might be unavailable due to simplified geometries are being generated</p>} /> }
            </span>
        )
    }

    return (
        <Grid container flexDirection={'row'} sx={{height: '100%', alignItems: 'center'}}>
            <Grid item sx={{ display:'flex', flexDirection:'row' }}>
                Simplification status: { getSimplificationStatus() }
            </Grid>
            <Grid item sx={{display:'flex', flexDirection:'row', marginLeft: '20px'}}>
                Tiling status: { getTilingStatus() }
            </Grid>
        </Grid>
    )
}

