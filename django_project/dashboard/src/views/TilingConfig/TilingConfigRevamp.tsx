import React, {useEffect, useState, useCallback} from 'react';
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
import {postData} from "../../utils/Requests";
import AlertMessage from '../../components/AlertMessage';
import Loading from "../../components/Loading";
import Scrollable from '../../components/Scrollable';
import IconButton from '@mui/material/IconButton';
import DoDisturbOnIcon from '@mui/icons-material/DoDisturbOn';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import DeleteIcon from '@mui/icons-material/Delete';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Dataset from '../../models/dataset';
import View from '../../models/view';
import '../../styles/TilingConfig.scss';
import { AddButton } from '../../components/Elements/Buttons';
import HtmlTooltip from '../../components/HtmlTooltip';
import { TilingConfig, MAX_ZOOM } from '../../models/tiling';
import TilingConfigPreview from './TilingConfigPreview';
import StatusLoadingDialog from '../../components/StatusLoadingDialog';


const FETCH_TILING_CONFIG_URL = '/api/fetch-tiling-configs/'


interface AdminLevelTilingInterface {
    tiling_config_idx: number,
    tiling_config: TilingConfig,
    admin_level: number,
    onValueUpdated: (tilingConfigIdx: number, adminLevel: number, value: number) => void,
    onValueRemoved: (tilingConfigIdx: number, adminLevel: number) => void,
    onTileEnterEditMode: (tilingConfigIdx: number, adminLevel: number) => void,
    onTileExitEditMode: () => void,
    isReadOnly?: boolean
}

interface AdminLevelItemViewInterface {
    tiling_config_idx: number,
    tiling_config: TilingConfig,
    admin_level: number,
}

interface TilingConfigMatrixInterface {
    data: TilingConfig[]
}

interface EditTilingConfigMatrixInterface {
    initialData: TilingConfig[],
    onUpdated: (data: TilingConfig[]) => void
}

interface TilingConfigInterface {
    dataset?: Dataset,
    view?: View,
    isReadOnly?: boolean,
}


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

const getZoomTooltip = (level: number) => {
    const levelStr = level.toString()
    return zoomMapping[levelStr]
}

const cloneTilingConfig = (tilingConfig: TilingConfig[]) => {
    let _result: TilingConfig[] = []
    for (let i=0;i<tilingConfig.length;++i) {
        _result.push({
            zoom_level: tilingConfig[i].zoom_level,
            admin_level_tiling_configs: tilingConfig[i].admin_level_tiling_configs.map(a => ({...a}))
        })
    }
    return _result
}


function AdminLevelItemView(props: AdminLevelItemViewInterface) {
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

function AdminLevelItem(props: AdminLevelTilingInterface) {
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
            props.onTileEnterEditMode(props.tiling_config_idx, props.admin_level)
        } else {
            props.onValueRemoved(props.tiling_config_idx, props.admin_level)
        }
    }

    const onKeyPress = (e: any) => {
        if(e.keyCode == 13){
            e.preventDefault()
            setIsEdit(false)
            props.onValueUpdated(props.tiling_config_idx, props.admin_level, e.target.value)
            props.onTileExitEditMode()
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
            props.onTileExitEditMode()
        }
    }

    const onChange = (e: any) => {
        let _parsed = parseFloat(e.target.value)
        if (isNaN(_parsed) || _parsed < 0)
            _parsed = 0
        if (_parsed > 1)
            _parsed = 1
        let _item = {...item}
        _item.simplify_tolerance = _parsed
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
                                onClick={()=>{
                                    setIsEdit(true)
                                    props.onTileEnterEditMode(props.tiling_config_idx, props.admin_level)
                                }} disabled={props.isReadOnly}>
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
                        <Grid container flexDirection={'row'} alignItems={'center'}>
                            <Grid item>
                                <TextField
                                    id="outlined-number"
                                    label="Tolerance"
                                    type="number"
                                    InputLabelProps={{
                                        shrink: true,
                                    }}
                                    InputProps={{
                                        inputProps: {
                                            max: 1,
                                            min: 0,
                                            step: 0.01
                                        }
                                    }}
                                    size="small"
                                    sx={{
                                        width: '90px'
                                    }}
                                    value={item.simplify_tolerance}
                                    onChange={onChange}
                                    onKeyDown={onKeyPress}
                                    autoFocus
                                />
                            </Grid>
                            <Grid item className='tiling-input-tooltip'>
                                <HtmlTooltip tooltipTitle='Simplification Level'
                                    tooltipDescription={<p>Enter a value from 0 to 1 where 1 indicates 'retain 100% of the original vertices' and 0 indcates 'remove as many vertices as possible whilst still maintaining a valid polygon'. Press enter to save edits or escape to revert.</p>}
                                />
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
            )}
        </Box>        
    )
}

function TilingConfigMatrix(props: TilingConfigMatrixInterface) {
    const { data } = props

    return (
        <Scrollable>
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
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
                                            <AdminLevelItemView tiling_config_idx={index} tiling_config={tilingConfig} admin_level={0}/>
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItemView tiling_config_idx={index} tiling_config={tilingConfig} admin_level={1}/>
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItemView tiling_config_idx={index} tiling_config={tilingConfig} admin_level={2}/>
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItemView tiling_config_idx={index} tiling_config={tilingConfig} admin_level={3}/>
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItemView tiling_config_idx={index} tiling_config={tilingConfig} admin_level={4}/>
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItemView tiling_config_idx={index} tiling_config={tilingConfig} admin_level={5}/>
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItemView tiling_config_idx={index} tiling_config={tilingConfig} admin_level={6}/>
                                        </TableCell>
                                    </TableRow>
                                )) : null}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Grid>
                <Grid container flexDirection={'column'} alignItems={'flex-start'} sx={{marginTop: '10px'}}>
                    <Grid item>
                        <CheckCircleOutlineIcon fontSize='small' color='success' /><span> : included in vector tile at current zoom level</span>
                    </Grid>
                    <Grid item>
                        <DoDisturbOnIcon color='error' fontSize='small' /><span> : excluded in vector tile at current zoom level</span>
                    </Grid>
                    <Grid item sx={{width: '100%'}}>
                        <Grid container flexDirection={'row'} justifyContent='space-between'>
                            <Grid item sx={{marginTop: '10px', textAlign: 'left', width: '50%'}}>
                                <p>
                                    Use the matrix above to enable boundaries to be rendered into tiles at different zoom levels and with different simplification levels. 
                                    Enter 1 to enable rendering without simplification. Using too small a simplification factor may result in artifacts such as slivers or polygons being rendered as triangles. 
                                    Note that pressing save will result in the entire tileset to be rerendered to cache, a CPU and time intensive operation.
                                </p>
                            </Grid>
                            <Grid item sx={{marginTop: '10px', textAlign: 'right', width: '50%'}}>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
            </Box>
        </Box>
        </Scrollable>
    )
}

function EditTilingConfigMatrix(props: EditTilingConfigMatrixInterface) {
    const { initialData } = props
    const [data, setData] = useState<TilingConfig[]>(null)
    const [loading, setLoading] = useState(false)
    const [isInEditMode, setIsInEditMode] = useState(false)
    const [editTilingIdx, setEditTilingIdx] = useState(-1)
    const [editTilingAdminLevel, setEditTilingAdminLevel] = useState(-1)

    useEffect(() => {
        let _tilingConfig:TilingConfig[] = cloneTilingConfig(initialData)
        setData(_tilingConfig)
    }, [initialData])

    const onTileEnterEditMode = (tilingConfigIdx: number, adminLevel: number) => {
        setEditTilingIdx(tilingConfigIdx)
        setEditTilingAdminLevel(adminLevel)
        setIsInEditMode(true)
    }

    const onTileExitEditMode = () => {
        setEditTilingIdx(-1)
        setEditTilingAdminLevel(-1)
        setIsInEditMode(false)
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
        props.onUpdated(_data)
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
        props.onUpdated(_data)
    }

    const deleteLastZoomLevel = () => {
        let _data = [...data]
        let tilingConfigIdx = _data.length - 1
        _data.splice(tilingConfigIdx, 1)
        props.onUpdated(_data)
    }

    const addNewZoomLevel = () => {
        // find last zoom level
        let _lastZoom = -1
        if (data && data.length > 0) {
            _lastZoom = data[data.length - 1].zoom_level
        }
        if (_lastZoom === MAX_ZOOM) return;
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
        props.onUpdated([...data, _newTiling])
    }

    const isItemReadOnly = useCallback((tilingConfigIdx: number, adminLevel: number) => {
        if (isInEditMode) {
            return tilingConfigIdx !== editTilingIdx || adminLevel !== editTilingAdminLevel
        }
        return false
    }, [isInEditMode, editTilingIdx, editTilingAdminLevel])

    const canAddMoreZoomLevel = () => {
        // find last zoom level
        let _lastZoom = -1
        if (data && data.length > 0) {
            _lastZoom = data[data.length - 1].zoom_level
        }
        return _lastZoom < MAX_ZOOM
    }

    return (
        <Scrollable>
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
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
                                            { index === data.length - 1 ?  
                                                <IconButton aria-label="delete" title='Delete Zoom Level' disabled={loading || isInEditMode} onClick={deleteLastZoomLevel}>
                                                    <DeleteIcon fontSize='small' />
                                                </IconButton>
                                            : null}
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={0}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={isItemReadOnly(index, 0)}
                                                onTileEnterEditMode={onTileEnterEditMode} onTileExitEditMode={onTileExitEditMode} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={1}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={isItemReadOnly(index, 1)}
                                                onTileEnterEditMode={onTileEnterEditMode} onTileExitEditMode={onTileExitEditMode} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={2}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={isItemReadOnly(index, 2)}
                                                onTileEnterEditMode={onTileEnterEditMode} onTileExitEditMode={onTileExitEditMode} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={3}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={isItemReadOnly(index, 3)}
                                                onTileEnterEditMode={onTileEnterEditMode} onTileExitEditMode={onTileExitEditMode} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={4}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={isItemReadOnly(index, 4)}
                                                onTileEnterEditMode={onTileEnterEditMode} onTileExitEditMode={onTileExitEditMode} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={5}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={isItemReadOnly(index, 5)}
                                                onTileEnterEditMode={onTileEnterEditMode} onTileExitEditMode={onTileExitEditMode} />
                                        </TableCell>
                                        <TableCell>
                                            <AdminLevelItem tiling_config_idx={index} tiling_config={tilingConfig} admin_level={6}
                                                onValueUpdated={onValueUpdated} onValueRemoved={onValueRemoved} isReadOnly={isItemReadOnly(index, 6)}
                                                onTileEnterEditMode={onTileEnterEditMode} onTileExitEditMode={onTileExitEditMode} />
                                        </TableCell>
                                    </TableRow>
                                )) : null}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Grid>
                <Grid container flexDirection={'column'} alignItems={'flex-start'} sx={{marginTop: '10px'}}>
                    <Grid item sx={{marginBottom: '10px'}}>
                        <Button
                            variant={"contained"}
                            disabled={loading || isInEditMode || !canAddMoreZoomLevel()}
                            onClick={addNewZoomLevel}>
                            Add New Zoom Level
                        </Button>
                    </Grid>
                    <Grid item>
                        <CheckCircleOutlineIcon fontSize='small' color='success' /><span> : included in vector tile at current zoom level</span>
                    </Grid>
                    <Grid item>
                        <DoDisturbOnIcon color='error' fontSize='small' /><span> : excluded in vector tile at current zoom level</span>
                    </Grid>
                    <Grid item sx={{width: '100%'}}>
                        <p className='tiling-desc-note'>
                            Use the matrix above to enable boundaries to be rendered into tiles at different zoom levels and with different simplification levels. Enter 1 to enable rendering without simplification. Using too small a simplification factor may result polygons being rendered as triangles or overly simple shapes. Note that pressing save will result in the dataset and views that inherit it's tiling config to be marked as inconsistent.
                            Inconsistent views will need their tile caches regenerated which you can do on the Sync Status tab of this dataset or of individual views. Note that cache regeneration is a CPU and time intensive operation.
                        </p>
                    </Grid>
                </Grid>
            </Box>
        </Box>
        </Scrollable>
    )
}

export default function TilingConfiguration(props: TilingConfigInterface) {
    const [isEdit, setIsEdit] = useState(true)
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState<TilingConfig[]>(null)
    const [originalData, setOriginalData] = useState<TilingConfig[]>(null)
    const [onGeoJsonLoading, setOnGeoJsonLoading] = useState(false)

    const fetchTilingConfigs = () => {
        setLoading(true)
        let _fetch_url = FETCH_TILING_CONFIG_URL
        if (props.dataset) {
            _fetch_url = `${FETCH_TILING_CONFIG_URL}dataset/${props.dataset.uuid}/`
        } else if (props.view) {
            _fetch_url = `${FETCH_TILING_CONFIG_URL}view/${props.view.uuid}/`
        }
        axios.get(_fetch_url).then(
            response => {
                setLoading(false)
                let _data = response.data as TilingConfig[]
                setData(_data)
                setOriginalData(cloneTilingConfig(_data))
            }
        )
    }

    useEffect(() => {
        if ((props.dataset && props.dataset.uuid) ||
            (props.view && props.view.uuid)) {
            fetchTilingConfigs()
        }
    }, [props.dataset, props.view])

    const onCancel = () => {
        setData(cloneTilingConfig(originalData))
        setIsEdit(false)
    }

    return (
        <Box className='tiling-configuration-container'>
            <StatusLoadingDialog open={onGeoJsonLoading} title={'Fetching Country Boundaries'} description={'Please wait while loading selected country geojson for the preview.'} />
            <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                <Grid item>
                </Grid>
                <Grid item textAlign={'right'}>
                    {!isEdit && 
                        <Button
                            variant={"contained"}
                            disabled={loading}
                            className='action-button'
                            onClick={() => setIsEdit(true)}>
                            Edit
                        </Button>
                    }
                    {isEdit &&
                        <Grid container flexDirection={'row'} justifyContent={'space-between'} spacing={1}>
                            <Grid item>
                                <Button
                                    variant={"contained"}
                                    disabled={loading}
                                    className='action-button'
                                    onClick={() => setIsEdit(false)}>
                                    Save
                                </Button>
                            </Grid>
                            <Grid item>
                                <Button
                                    variant={"outlined"}
                                    disabled={loading}
                                    className='action-button'
                                    onClick={onCancel}>
                                    Cancel
                                </Button>
                            </Grid>
                        </Grid>
                    }
                </Grid>
            </Grid>
            { loading && <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <Grid container flexDirection={'column'} spacing={1}>
                    <Grid item>
                        <Loading/>
                    </Grid>
                    <Grid item>
                        { 'Retrieving tiling config matrix...' }                
                    </Grid>
                </Grid>
            </Box>}
            { !loading && !isEdit && <TilingConfigMatrix data={data} />}
            { !loading && isEdit && 
                <Grid container flexDirection={'row'} flex={1}>
                    <Grid item md={8} xs={12}>
                        <EditTilingConfigMatrix initialData={data} onUpdated={(data: TilingConfig[]) => setData(data)} />
                    </Grid>
                    <Grid item md={4} xs={12} sx={{display: 'flex'}}>
                        <TilingConfigPreview configData={data} dataset={props.dataset} view={props.view}
                          onGeoJsonLoading={(isLoading) => setOnGeoJsonLoading(isLoading)}/>
                    </Grid>
                </Grid>
            }
        </Box>
    )

}

