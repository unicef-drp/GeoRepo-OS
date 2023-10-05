import React, {useEffect, useState} from 'react';
import axios from "axios";
import Grid from '@mui/material/Grid';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HtmlTooltip from '../../components/HtmlTooltip';
import Dataset from '../../models/dataset';
import View from '../../models/view';


const TILING_CONFIGS_STATUS_URL = '/api/tiling-configs/status/'
const DONE_STATUS_LIST = ['Done', 'Error']

interface TilingConfigStatusInterface {
    dataset?: Dataset,
    view?: View,
}

export default function TilingConfigStatus(props: TilingConfigStatusInterface) {
    const [simplificationStatus, setSimplificationStatus] = useState('')
    const [simplificationProgress, setSimplificationProgress] = useState('')
    const [tilingStatus, setTilingStatus] = useState('')
    const [tilingProgress, setTilingProgress] = useState('')
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const [allFinished, setAllFinished] = useState(false)

    const fetchTilingStatus = () => {
        let _object_type = props.dataset ? 'dataset' : 'datasetview'
        let _object_uuid = props.dataset ? props.dataset.uuid : props.view?.uuid
        let _fetch_url = `${TILING_CONFIGS_STATUS_URL}${_object_type}/${_object_uuid}/`
        axios.get(_fetch_url).then(
            response => {
                setSimplificationStatus(response.data['simplification']['status'])
                setSimplificationProgress(response.data['simplification']['progress'])
                setTilingStatus(response.data['vector_tiles']['status'])
                setTilingProgress(response.data['vector_tiles']['progress'])
                if (DONE_STATUS_LIST.includes(response.data['simplification']['status']) && DONE_STATUS_LIST.includes(response.data['vector_tiles']['status'])) {
                    setAllFinished(true)
                }
            }
        ).catch((error) => {
            console.log('Fetch Tiling status failed! ', error)
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
        if (tilingStatus === 'Done') {
            return (
                <span style={{display:'flex'}}>
                    <CheckCircleIcon color='success' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Done</span>
                </span>
            )
        } else if (tilingStatus === 'Error') {
            return (
                <span style={{display:'flex'}}>
                    <ErrorIcon color='error' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Stopped with Error</span>
                </span>
            )
        } else if (tilingStatus === '') {
            return <span>-</span>
        }
        return (
            <span style={{display:'flex', marginLeft: '5px' }}>
                {tilingStatus === 'Processing' && <CircularProgress size={18} /> }
                <span style={{marginLeft: '5px' }}>{tilingStatus}{tilingStatus === 'Processing' && tilingProgress ? ` ${tilingProgress}%`:''}</span>
            </span>
        )
    }

    const getSimplificationStatus = () => {
        if (simplificationStatus === 'Done') {
            return (
                <span style={{display:'flex'}}>
                    <CheckCircleIcon color='success' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Done</span>
                </span>
            )
        } else if (simplificationStatus === 'Error') {
            return (
                <span style={{display:'flex'}}>
                    <ErrorIcon color='error' fontSize='small' />
                    <span style={{marginLeft: '5px' }}>Stopped with Error</span>
                </span>
            )
        } else if (simplificationStatus === '') {
            return <span>-</span>
        }
        return (
            <span style={{display:'flex', marginLeft: '5px'}}>
                {simplificationStatus === 'Processing' && <CircularProgress size={18} /> }
                <span style={{marginLeft: '5px' }}>{simplificationStatus === 'Processing' && simplificationProgress ? ` ${simplificationProgress}`:''}</span>
                {simplificationStatus === 'Processing' && <HtmlTooltip tooltipDescription={<p>Preview might be unavailable due to simplified geometries are being generated</p>} /> }
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

