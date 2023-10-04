import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import toLower from "lodash/toLower";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import axios from "axios";
import {postData} from "../../../utils/Requests";
import AlertMessage from '../../../components/AlertMessage';
import Loading from "../../../components/Loading";
import Scrollable from '../../../components/Scrollable';
import IconButton from '@mui/material/IconButton';
import DoDisturbOnIcon from '@mui/icons-material/DoDisturbOn';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Dataset from '../../../models/dataset';
import View from '../../../models/view';
import '../../../styles/TilingConfig.scss';
import { AddButton } from '../../../components/Elements/Buttons';
import HtmlTooltip from '../../../components/HtmlTooltip';


const FETCH_TILING_CONFIG_URL = '/api/fetch-tiling-configs/'
const UPDATE_TILING_CONFIG_URL = '/api/update-tiling-configs/'
const TILING_CONFIGS_TEMP_CREATE_URL = '/api/tiling-configs/temporary/create/'
const TILING_CONFIGS_TEMP_DETAIL_URL = '/api/tiling-configs/temporary/detail/'
const TILING_CONFIGS_STATUS_URL = '/api/tiling-configs/status/'
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

interface AdminLevelItemViewInterface {
    tiling_config_idx: number,
    tiling_config: TilingConfig,
    admin_level: number,
}

export function AdminLevelItemView(props: AdminLevelItemViewInterface) {
    const [idx, setIdx] = useState(-1)
    const [item, setItem] = useState({
        level: props.admin_level,
        simplify_tolerance: 1
    })
    useEffect(() => {
        let _idx = props.tiling_config.admin_level_tiling_configs.findIndex((element) => element.level === props.admin_level)
        setIdx(_idx)
        if (_idx > -1) {
            let _item = props.tiling_config.admin_level_tiling_configs[_idx]
            setItem(_item)
        } else {
            setItem({
                level: props.admin_level,
                simplify_tolerance: 1
            })
        }
    }, [props.admin_level, props.tiling_config])

    return (
        <Box>
            <Grid container flexDirection={'row'} alignItems={'center'} justifyContent={'center'}>
                <Grid item>
                    { idx === -1 ? (
                        <IconButton disabled={true}><DoDisturbOnIcon color='error' fontSize='small' /></IconButton>
                    ) : (
                        <Button size='small' sx={{width:'40px'}} startIcon={<CheckCircleOutlineIcon fontSize='small' color='success' />}
                            disabled={true}>
                            {item.simplify_tolerance}
                        </Button>
                    )}
                </Grid>
                <Grid item>
                </Grid>
            </Grid>
        </Box>
    )
}

export function AdminLevelItem(props: AdminLevelTilingInterface) {
    const [isHovering, setIsHovering] = useState(false)
    const [isEdit, setIsEdit] = useState(false)
    const [idx, setIdx] = useState(-1)
    const [item, setItem] = useState({
        level: props.admin_level,
        simplify_tolerance: 1
    })
    useEffect(() => {
        let _idx = props.tiling_config.admin_level_tiling_configs.findIndex((element) => element.level === props.admin_level)
        setIdx(_idx)
        if (_idx > -1) {
            let _item = props.tiling_config.admin_level_tiling_configs[_idx]
            setItem(_item)
        } else {
            setItem({
                level: props.admin_level,
                simplify_tolerance: 1
            })
        }
    }, [props.admin_level, props.tiling_config])

    const handleMouseOver = () => {
        setIsHovering(true)
    }

    const handleMouseOut = () => {
        setIsHovering(false)
    }

    const rightButtonOnClick = () => {
        if (idx === -1) {
            setIsEdit(true)
        } else {
            props.onValueRemoved(props.tiling_config_idx, props.admin_level)
        }
    }

    const onKeyPress = (e: any) => {
        if(e.keyCode == 13){
            e.preventDefault()
            setIsEdit(false)
            props.onValueUpdated(props.tiling_config_idx, props.admin_level, e.target.value)
        } else if (e.keyCode == 27) {
            e.preventDefault()
            setIsEdit(false)
            // reset value
            if (idx > -1) {
                let _item = props.tiling_config.admin_level_tiling_configs[idx]
                setItem(_item)
            } else {
                setItem({
                    level: props.admin_level,
                    simplify_tolerance: 1
                })
            }
        }
    }

    const onChange = (e: any) => {
        let _item = {...item}
        _item.simplify_tolerance = e.target.value
        setItem(_item)
    }

    return (
        <Box>
            { !isEdit && (
                <Grid container flexDirection={'row'} alignItems={'center'} justifyContent={'center'}
                    onMouseOver={handleMouseOver}
                    onMouseOut={handleMouseOut}>
                    <Grid item>
                        { idx === -1 ? (
                            <IconButton disabled={props.isReadOnly}><DoDisturbOnIcon color='error' fontSize='small' /></IconButton>
                        ) : (
                            <Button size='small' sx={{width:'40px'}} startIcon={<CheckCircleOutlineIcon fontSize='small' color='success' />}
                                onClick={()=>setIsEdit(true)} disabled={props.isReadOnly}>
                                {item.simplify_tolerance}
                            </Button>
                        )}
                    </Grid>
                    <Grid item>
                        <IconButton aria-label="delete" sx={{visibility: isHovering?'visible':'hidden'}} onClick={rightButtonOnClick} disabled={props.isReadOnly}>
                            { idx !== -1 ? (
                                <DeleteIcon fontSize='small' />
                            ) : (
                                <AddCircleOutlineIcon fontSize='small' />
                            )}
                        </IconButton>
                    </Grid>
                </Grid>
            )}
            {isEdit && (
                <Grid container flexDirection={'row'} alignItems={'center'} justifyContent={'center'}>
                    <Grid item className='InputHideArrows'>
                        <TextField
                            id="outlined-number"
                            label="Tolerance"
                            type="number"
                            InputLabelProps={{
                                shrink: true,
                            }}
                            size="small"
                            sx={{
                                width: '100px'
                            }}
                            value={item.simplify_tolerance}
                            onChange={onChange}
                            onKeyDown={onKeyPress}
                            autoFocus
                        />
                    </Grid>
                </Grid>
            )}
        </Box>        
    )
}

export function DatasetTilingConfigMatrix(props: DatasetTilingConfigInterface) {
    const [data, setData] = useState<TilingConfig[]>(null)
    const [loading, setLoading] = useState(true)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const navigate = useNavigate()

    const headerCells = [
        '',
        'Admin Level 0',
        'Admin Level 1',
        'Admin Level 2',
        'Admin Level 3',
        'Admin Level 4',
        'Admin Level 5',
        'Admin Level 6',
      ]

    const fetchTilingConfigs = () => {
        let _fetch_url = FETCH_TILING_CONFIG_URL
        if (props.dataset) {
            _fetch_url = `${FETCH_TILING_CONFIG_URL}dataset/${props.dataset.uuid}/`
        } else if (props.view) {
            _fetch_url = `${FETCH_TILING_CONFIG_URL}view/${props.view.uuid}/`
        } else if (props.session) {
            _fetch_url = `${TILING_CONFIGS_TEMP_DETAIL_URL}${props.session}/`
        }
        axios.get(_fetch_url).then(
            response => {
                setLoading(false)
                setData(response.data as TilingConfig[])
            }
        )
    }

    useEffect(() => {
        if ((props.dataset && props.dataset.uuid) ||
            (props.view && props.view.uuid) || props.session) {
            fetchTilingConfigs()
        }
    }, [props.dataset, props.view])

    const handleSaveClick = () => {
        setLoading(true)
        let _save_url = UPDATE_TILING_CONFIG_URL
        if (props.dataset) {
            _save_url = `${UPDATE_TILING_CONFIG_URL}dataset/${props.dataset.uuid}/`
        } else if (props.view) {
            _save_url = `${UPDATE_TILING_CONFIG_URL}view/${props.view.uuid}/`
        } else if (props.session) {
            _save_url = `${TILING_CONFIGS_TEMP_DETAIL_URL}${props.session}/`
        }
        postData(_save_url, data).then(
            response => {
                setLoading(false)
                if (props.session) {
                    if (props.onTilingConfigUpdated) {
                        props.onTilingConfigUpdated()
                    }
                } else {
                    setAlertMessage('Successfully saving tiling configs!')
                }
            }
          ).catch(error => {
            setLoading(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                alert('Error saving tiling configs...')
            }
          })
    }

    const onValueUpdated = (tilingConfigIdx: number, adminLevel: number, value: number) => {
        let _data = data.map((tilingConfig, index) => {
            if (index === tilingConfigIdx) {
                let _tiling_config = {...tilingConfig}
                let _idx = _tiling_config.admin_level_tiling_configs.findIndex((element) => element.level === adminLevel)
                let _tiling_configs = [..._tiling_config.admin_level_tiling_configs]
                if (_idx === -1) {
                    _tiling_configs.push({
                        level: adminLevel,
                        simplify_tolerance: value
                    })
                } else {
                    _tiling_configs[_idx].simplify_tolerance = value
                }
                _tiling_config.admin_level_tiling_configs = _tiling_configs
                tilingConfig = _tiling_config
            }
            return tilingConfig
        })
        setData(_data)
    }

    const onValueRemoved = (tilingConfigIdx: number, adminLevel: number) => {
        let _data = data.map((tilingConfig, index) => {
            if (index === tilingConfigIdx) {
                let _tiling_config = {...tilingConfig}
                let _idx = _tiling_config.admin_level_tiling_configs.findIndex((element) => element.level === adminLevel)
                let _tiling_configs = [..._tiling_config.admin_level_tiling_configs]
                if (_idx > -1) {
                    _tiling_configs.splice(_idx, 1)
                }
                _tiling_config.admin_level_tiling_configs = _tiling_configs
                tilingConfig = _tiling_config
            }
            return tilingConfig
        })
        // check if last idx
        if (tilingConfigIdx === data.length - 1) {
            // check if all rows are excluded
            let _lastIdx = tilingConfigIdx
            while (_lastIdx > 0 &&_data[_lastIdx].admin_level_tiling_configs.length === 0) {
                _data.splice(_lastIdx, 1)
                _lastIdx--
            }
        }
        setData(_data)
    }

    const addNewZoomLevel = () => {
        // find last zoom level
        if (!data || data.length === 0) return;
        let _lastZoom = data[data.length - 1].zoom_level
        let _newTiling: TilingConfig = {
            zoom_level: _lastZoom + 1,
            admin_level_tiling_configs: []
        }
        for (let i=0; i < 7; ++i) {
            _newTiling.admin_level_tiling_configs.push({
                level: i,
                simplify_tolerance: 1
            })
        }
        setData([...data, _newTiling])
    }

    const getZoomTooltip = (level: number) => {
        const zoomMapping: {[key:string]: string} = {
            "0": "1:591,657,550.500000",
            "1": "1:295,828,775.300000",
            "2": "1:147,914,387.600000",
            "3": "1:73,957,193.820000",
            "4": "1:36,978,596.910000",
            "5": "1:18,489,298.450000",
            "6": "1:9,244,649.227000",
            "7": "1:4,622,324.614000",
            "8": "1:2,311,162.307000",
            "9": "1:1,155,581.153000",
            "10": "1:577,790.576700",
            "11": "1:288,895.288400",
            "12": "1:144,447.644200",
            "13": "1:72,223.822090",
            "14": "1:36,111.911040",
            "15": "1:18,055.955520",
            "16": "1:9,027.977761",
            "17": "1:4,513.988880",
            "18": "1:2,256.994440",
            "19": "1:1,128.497220"
        }

        const levelStr = level.toString()
        return zoomMapping[levelStr]
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => setAlertMessage('')} />
                <Grid container flexDirection={'column'} sx={{alignItems: 'flex-start', paddingTop: '10px'}}>
                    <TableContainer component={Paper} className={'tiling-config-matrix'}>
                        <Table>
                            <TableHead>
                            <TableRow>
                                {
                                headerCells.map((headerCell, index) => (
                                    <TableCell key={index}>{headerCell}</TableCell>
                                ))
                                }
                            </TableRow>
                            </TableHead>
                            <TableBody>
                                {data ? data.map((tilingConfig, index) => (
                                    <TableRow key={index}>
                                        <TableCell title={getZoomTooltip(tilingConfig.zoom_level)}>
                                            Zoom {tilingConfig.zoom_level}
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={0}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={props.isReadOnly} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={1}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={props.isReadOnly} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={2}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={props.isReadOnly} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={3}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={props.isReadOnly} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={4}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={props.isReadOnly} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={5}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={props.isReadOnly} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={6}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={props.isReadOnly} />
                                        </TableCell>
                                    </TableRow>
                                )) : null}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Grid>
                <Grid container flexDirection={'column'} alignItems={'flex-start'} sx={{marginTop: '10px'}}>
                    { !props.isReadOnly && <Grid item sx={{marginBottom: '10px'}}>
                        <Button
                            variant={"contained"}
                            disabled={loading || props.isReadOnly}
                            onClick={addNewZoomLevel}>
                            Add New Zoom Level
                        </Button>
                    </Grid>
                    }
                    <Grid item>
                        <CheckCircleOutlineIcon fontSize='small' color='success' /><span> : included in vector tile at current zoom level</span>
                    </Grid>
                    <Grid item>
                        <DoDisturbOnIcon color='error' fontSize='small' /><span> : excluded in vector tile at current zoom level</span>
                    </Grid>
                    <Grid item sx={{width: '100%'}}>
                        <Grid container flexDirection={'row'} justifyContent='space-between'>
                            <Grid item sx={{marginTop: '10px', textAlign: 'left', width: '50%'}}>
                                { props.hideBottomNotes !== true && (
                                        <p>
                                            Use the matrix above to enable boundaries to be rendered into tiles at different zoom levels and with different simplification levels. 
                                            Enter 1 to enable rendering without simplification. Using too small a simplification factor may result in artifacts such as slivers or polygons being rendered as triangles. 
                                            Note that pressing save will result in the entire tileset to be rerendered to cache, a CPU and time intensive operation.
                                        </p>
                                )}
                            </Grid>
                            <Grid item sx={{marginTop: '10px', textAlign: 'right', width: '50%'}}>
                                <div className='button-container'>
                                    { props.hideActions !== true && (
                                        <Button
                                            variant={"contained"}
                                            disabled={loading || props.isReadOnly}
                                            onClick={handleSaveClick}>
                                            <span style={{ display: 'flex' }}>
                                            { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Save" }</span>
                                        </Button>
                                    )}
                                </div>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
                
            </Box>
        </Box>
    )
}

function TilingSimplificationStatus(props: any) {

    return (
        <div>
            
        </div>
    )
}


export default function DatasetTilingConfig(props: DatasetTilingConfigInterface) {
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)
    const [simplificationStatus, setSimplificationStatus] = useState('')
    const [simplificationProgress, setSimplificationProgress] = useState('')
    const [tilingStatus, setTilingStatus] = useState('')
    const [tilingProgress, setTilingProgress] = useState('')
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const [allFinished, setAllFinished] = useState(false)

    const fetchTilingStatus = () => {
        setLoading(true)
        let _object_type = props.dataset ? 'dataset' : 'datasetview'
        let _object_uuid = props.dataset ? props.dataset.uuid : props.view?.uuid
        let _fetch_url = `${TILING_CONFIGS_STATUS_URL}${_object_type}/${_object_uuid}/`
        axios.get(_fetch_url).then(
            response => {
                setLoading(false)
                setSimplificationStatus(response.data['simplification']['status'])
                setSimplificationProgress(response.data['simplification']['progress'])
                setTilingStatus(response.data['vector_tiles']['status'])
                setTilingProgress(response.data['vector_tiles']['progress'])
                if (DONE_STATUS_LIST.includes(response.data['simplification']['status']) && DONE_STATUS_LIST.includes(response.data['vector_tiles']['status'])) {
                    setAllFinished(true)
                }
            }
        )
    }

    const updateTilingStatus = () => {
        let _data = {
            'object_type': props.dataset ? 'dataset': 'datasetview',
            'object_uuid': props.dataset ? props.dataset.uuid: props.view?.uuid
        }
        let _url = TILING_CONFIGS_TEMP_CREATE_URL
        setLoading(true)
        postData(_url, _data).then(
            response => {
                setLoading(false)
                let _query_params = 'session=' + response.data['session']
                if (props.dataset) {
                    _query_params = _query_params + `&dataset_uuid=${props.dataset.uuid}`
                } else if (props.view) {
                    _query_params = _query_params + `&view_uuid=${props.view.uuid}` + `&dataset_uuid=${props.view.dataset_uuid}`
                }
                let _moduleName = ''
                if (props.dataset) {
                    _moduleName = toLower(props.dataset.type.replace(' ', '_'))
                    navigate(`/${_moduleName}/tiling_config_wizard?${_query_params}`)
                } else if (props.view) {
                    navigate(`/view_edit_tiling_config_wizard?${_query_params}`)
                }
            }
          ).catch(error => {
            setLoading(false)
            console.log('error ', error)
            alert('Error: Unable to update tiling config matrix! ' + error)
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
            }, 5000);
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
        }
        return (
            <span style={{display:'flex', marginLeft: '5px'}}>
                <CircularProgress size={18} />
                <span style={{marginLeft: '5px' }}>{simplificationStatus === 'Processing' && simplificationProgress ? ` ${simplificationProgress}`:''}</span>
                {simplificationStatus === 'Processing' && <HtmlTooltip tooltipDescription={<p>Preview might be outdated due to simplified geometries are being generated</p>} /> }
            </span>
        )
    }

    return (
        <Scrollable>
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto' }}>
                <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                    <Grid item>
                        <Grid container flexDirection={'row'} sx={{height: '100%', alignItems: 'center'}}>
                            <Grid item sx={{display:'flex', flexDirection:'row'}}>
                                Tiling status: { getTilingStatus() }
                            </Grid>
                            <Grid item sx={{ display:'flex', flexDirection:'row', marginLeft: '20px' }}>
                                Simplification status: { getSimplificationStatus() }
                            </Grid>
                        </Grid>
                    </Grid>
                    <Grid item textAlign={'right'}>
                        <AddButton
                            text={"Update Matrix"}
                            variant={"secondary"}
                            disabled={loading}
                            useIcon={false}
                            onClick={updateTilingStatus} />
                    </Grid>
                </Grid>
                <DatasetTilingConfigMatrix {...props} isReadOnly={true} hideActions={true} />
            </Box>
        </Scrollable>
    )
}