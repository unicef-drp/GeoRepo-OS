import React, {useEffect, useRef, useState} from 'react';
import Grid from '@mui/material/Grid';
import Box from "@mui/material/Box";
import Alert, { AlertColor } from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import View from "../../models/view";
import axios from "axios";
import {useNavigate, useSearchParams} from "react-router-dom";
import Select, { SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Slider from '@mui/material/Slider';
import WarningIcon from '@mui/icons-material/Warning';
import Tooltip from '@mui/material/Tooltip';
import {useAppDispatch} from "../../app/hooks";
import Scrollable from '../../components/Scrollable';
import List from "../../components/List";
import Loading from "../../components/Loading";
import { EntitiesFilterInterface } from '../Dataset/EntitiesFilter';
import { TilingConfig, MAX_ZOOM } from '../../models/tiling';
import '../../styles/ViewDownload.scss';
import '../../styles/TilingConfig.scss';
import LoadingButton from '@mui/lab/LoadingButton';
import {postData} from "../../utils/Requests";
import {setPollInterval, FETCH_INTERVAL_JOB} from "../../reducers/notificationPoll";
import { capitalize, humanFileSize } from '../../utils/Helpers';
import LinearProgressWithLabel from "../../components/LinearProgressWithLabel";
import AlertMessage from "../../components/AlertMessage";
import { AdminLevelItemView, getZoomTooltip } from '../TilingConfig/TilingConfigRevamp';


const EXPORTER_URL = '/api/exporter/'
const ONGOING_STATUS_LIST = ['PENDING', 'PROCESSING']
interface MetadataInterface {
    filters: EntitiesFilterInterface;
    available_formats: string[];
    is_simplification_available: boolean;
    tiling_configs: TilingConfig[];
    current_simplification_status?: string;
}
interface ExportRequestDetailInterface {
    id: number;
    uuid: string;
    format: string;
    is_simplified_entities: boolean;
    simplification_zoom_level: number;
    status_text?: string;
    status?: string;
    filters: EntitiesFilterInterface;
    download_link?: string;
    download_link_expired_on?: Date;
    source?: string;
    progress?: number;
    requester_name?: string;
    errors?: string;
    submitted_on?: Date;
    finished_at?: Date;
    file_output_size?: number;
}

const EXCLUDED_FILTER_KEYS = [
    'updated_at', 'points'
]

const displayFilter = (key: string, filters: any) => {
    if (key === 'valid_from') {
        return new Date(filters[key]).toLocaleString([], {dateStyle: 'short', timeStyle: 'short'})
    }

    return filters[key].join(', ')
}

const tilingConfigHeaderCells = [
    '',
    'Admin Level 0',
    'Admin Level 1',
    'Admin Level 2',
    'Admin Level 3',
    'Admin Level 4',
    'Admin Level 5',
    'Admin Level 6',
]

function EntityFilters(props: any) {
    const {filters} = props

    if (filters === null) {
        return <span>-</span>
    }

    const usedFilterKeys = Object.keys(filters).reduce(function (filtered, key) {
        if (!EXCLUDED_FILTER_KEYS.includes(key)) {
            if (key === 'valid_from' && filters[key]) {
                filtered.push(key)
            } else if (filters[key] && filters[key].length) {
                filtered.push(key)
            }
        }
        return filtered;
    }, [])

    if (usedFilterKeys.length === 0) {
        return <span>-</span>
    }

    return (
        <pre>
            <div>
                { usedFilterKeys.map((dictKey: string, index: number) => (
                    <div key={index}>{dictKey} = {displayFilter(dictKey, filters)}</div>
                ))
                }
            </div>
      </pre>
    )
}


function TilingConfigDisplay(props: {tiling_configs: TilingConfig[], selected_zoom_level: number}) {
    const {tiling_configs, selected_zoom_level} = props
    const tilingConfigIdx = tiling_configs.findIndex((value: TilingConfig) => value.zoom_level === selected_zoom_level)
    const selectedTilingConfig = tilingConfigIdx > -1 ? tiling_configs[tilingConfigIdx] : {
        zoom_level: selected_zoom_level,
        admin_level_tiling_configs: []
    }

    return (
        <TableContainer component={Paper} className={'tiling-config-matrix'}>
            <Table>
                <TableHead>
                <TableRow>
                    {
                        tilingConfigHeaderCells.map((headerCell, index) => (
                            <TableCell key={index}>{headerCell}</TableCell>
                        ))
                    }
                </TableRow>
                </TableHead>
                <TableBody>
                    <TableRow key={tilingConfigIdx}>
                        <TableCell title={getZoomTooltip(selected_zoom_level)}>
                            Zoom {selected_zoom_level}
                        </TableCell>
                        <TableCell>
                            <AdminLevelItemView tiling_config_idx={tilingConfigIdx} tiling_config={selectedTilingConfig} admin_level={0}/>
                        </TableCell>
                        <TableCell>
                            <AdminLevelItemView tiling_config_idx={tilingConfigIdx} tiling_config={selectedTilingConfig} admin_level={1}/>
                        </TableCell>
                        <TableCell>
                            <AdminLevelItemView tiling_config_idx={tilingConfigIdx} tiling_config={selectedTilingConfig} admin_level={2}/>
                        </TableCell>
                        <TableCell>
                            <AdminLevelItemView tiling_config_idx={tilingConfigIdx} tiling_config={selectedTilingConfig} admin_level={3}/>
                        </TableCell>
                        <TableCell>
                            <AdminLevelItemView tiling_config_idx={tilingConfigIdx} tiling_config={selectedTilingConfig} admin_level={4}/>
                        </TableCell>
                        <TableCell>
                            <AdminLevelItemView tiling_config_idx={tilingConfigIdx} tiling_config={selectedTilingConfig} admin_level={5}/>
                        </TableCell>
                        <TableCell>
                            <AdminLevelItemView tiling_config_idx={tilingConfigIdx} tiling_config={selectedTilingConfig} admin_level={6}/>
                        </TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        </TableContainer>
    )
}

function ExportViewDetail(props: any) {
    const {view, requestId, filterSession} = props
    const [loading, setLoading] = useState(true)
    const navigate = useNavigate()
    const [metadata, setMetadata] = useState<MetadataInterface>(null)
    const [data, setData] = useState<ExportRequestDetailInterface>(null)
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const [alertTitle, setAlertTitle] = useState('')
    const [alertMessage, setAlertMessage] = useState('')
    const [alertSeverity, setAlertSeverity] = useState<AlertColor>('success')
    const [toastMessage, setToastMessage] = useState('')
    const dispatch = useAppDispatch()
    const marks = [
        {
            value: 0,
            label: 'Zoom 0',
        },
        {
            value: MAX_ZOOM,
            label: `Zoom ${MAX_ZOOM}`,
        }
    ]

    const fetchMetadata = () => {
        let _url = EXPORTER_URL + `${view.id}/metadata/`
        if (filterSession) {
            _url = _url + `?session=${filterSession}`
        }
        axios.get(_url).then(response => {
            if (response.data) {
                let _metadata: MetadataInterface = response.data
                setMetadata(_metadata)
                if (requestId) {
                    fetchRequestDetail()
                } else {
                    setData({
                        id: 0,
                        uuid: '',
                        format: _metadata.available_formats[0],
                        is_simplified_entities: false,
                        simplification_zoom_level: 0,
                        filters: _metadata.filters
                    })
                    setLoading(false)
                }                
            } else {
                setMetadata(null)
                setLoading(false)
            }
        }).catch(error => {
            console.log(error)
            setLoading(false)
            let _message = 'Unable to fetch export view metadata, Please try again or contact the administrator!'
            if (error.response) {
                if ('detail' in error.response.data) {
                    _message = error.response.data.detail
                }
            }
            alert(_message)
        })
    }

    const fetchRequestDetail = (isInterval?: boolean) => {
        if (!isInterval) {
            setLoading(true)
        }
        axios.get(EXPORTER_URL + `${view.id}/detail/?request_id=${requestId}`).then(response => {
            if (response.data) {
                let _data = response.data as ExportRequestDetailInterface
                setData(_data)
                if (_data.status === 'PROCESSING') {
                    setAlertSeverity('info')
                    setAlertTitle('The job is processing in the background, please stand by...')
                    setAlertMessage('')
                } else if (isInterval && _data.status === 'DONE') {
                    setAlertSeverity('success')
                    setAlertTitle('Your download is ready!')
                    setAlertMessage('You may download the file from the link below.')
                } else if (isInterval && _data.status === 'ERROR') {
                    setAlertSeverity('error')
                    setAlertTitle('Your download is finished with errors!')
                    let _message = _data.errors ? _data.errors : 'Please try again or contact the administrator!'
                    setAlertMessage(_message)
                }
            } else {
                setData(null)
            }
            if (!isInterval) {
                setLoading(false)
            }
        }).catch(error => {
            console.log(error)
            if (!isInterval) {
                setLoading(false)
                let _message = 'Unable to fetch request detail, Please try again or contact the administrator!'
                if (error.response) {
                    if ('detail' in error.response.data) {
                        _message = error.response.data.detail
                    }
                }
                alert(_message)
            }
        })
    }

    useEffect(() => {
        setLoading(true)
        fetchMetadata()
    }, [view, requestId, filterSession])

    useEffect(() => {
        if (data && ONGOING_STATUS_LIST.includes(data.status)) {
            if (currentInterval) {
                clearInterval(currentInterval)
                setCurrentInterval(null)
            }
            const interval = setInterval(() => {
                fetchRequestDetail(true)
            }, 5000)
            setCurrentInterval(interval)
            return () => clearInterval(interval)
        }
    }, [data?.status])

    const submitExportRequest = () => {
        setLoading(true)
        let _data = {
            'filters': metadata.filters,
            'is_simplified_entities': data.is_simplified_entities,
            'simplification_zoom_level': data.simplification_zoom_level,
            'format': data.format
        }
        postData(EXPORTER_URL + `${view.id}/detail/`, _data).then(
            response => {
                // trigger fetch request detail
                let _requestId = response.data['id']
                let _navigate_to = `/view_edit?id=${view.id}&tab=2&requestId=${_requestId}`
                navigate(_navigate_to)
                setToastMessage('Successfully submitting download request. Your request will be processed in the background.')
                // trigger to fetch notification frequently
                dispatch(setPollInterval(FETCH_INTERVAL_JOB))
            }
          ).catch(error => {
            let _message = 'Please try again or contact the administrator!'
            if (error.response) {
                if ('detail' in error.response.data && error.response.data.detail) {
                    _message = error.response.data.detail
                }
            }
            setAlertTitle('Error submitting download request!')
            setAlertSeverity('error')
            setAlertMessage(_message)
            if (_message.includes('simplification') || _message.includes('simplified')) {
                // fetch metadata again
                fetchMetadata()
            }
        })
    }

    if (loading) {
        return <Loading/>
    }

    return (
        <Box className='ExportViewDetail'>
            <AlertMessage message={toastMessage} onClose={() => setToastMessage('')} />
            <Grid container display={'flex'} flexDirection={'column'} spacing={1}>
                <Grid item>
                    <Grid container flexDirection={'row'} justifyContent={'center'}>
                        { alertTitle ?
                            <Alert className="UploadAlertMessage" severity={alertSeverity}>
                                <AlertTitle>{alertTitle}</AlertTitle>
                                <p className="display-linebreak">
                                    { alertMessage }
                                </p>
                                { data?.status === 'PROCESSING' ? <LinearProgressWithLabel value={data.progress} maxBarWidth={'90%'} /> : null }
                            </Alert> : null }
                    </Grid>
                </Grid>
                <Grid item className='RowItem'>
                    <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                        <Grid item className='Title' md={3} xl={3} xs={12}>Filters</Grid>
                        <Grid item md={9} xl={9} xs={12}>
                            { requestId > 0 && data && <EntityFilters filters={data.filters} /> }
                            { filterSession && metadata && <EntityFilters filters={metadata.filters} /> }
                        </Grid>
                    </Grid>
                </Grid>
                <Grid item className='RowItem'>
                    <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                        <Grid item className='Title' md={3} xl={3} xs={12}>Format</Grid>
                        <Grid item md={9} xl={9} xs={12}>
                            <FormControl sx={{minWidth: '300px'}} disabled={requestId > 0}>
                                <Select
                                    id="format-type-select"
                                    value={data?.format}
                                    label=""
                                    onChange={(event: SelectChangeEvent) => {
                                        setData({
                                            ...data,
                                            format: event.target.value
                                        })
                                    }}
                                >
                                    { metadata.available_formats.map((val: string, index: number) => {
                                        return <MenuItem value={val} key={index}>{val}</MenuItem>
                                    })
                                    }
                                </Select>
                            </FormControl>
                        </Grid>
                    </Grid>
                </Grid>
                <Grid item className='RowItem'>
                    <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                        <Grid item className='Title' md={3} xl={3} xs={12}>Extract simplified geometries</Grid>
                        <Grid item md={9} xl={9} xs={12}>
                            <FormControlLabel className='SimplifiedCheckBox' control={<Checkbox value={data?.is_simplified_entities} checked={data?.is_simplified_entities}
                                onChange={(val) => setData({...data, is_simplified_entities: val.target.checked})} />}
                                label={ metadata?.is_simplification_available === false && requestId === 0 ? <span>
                                    <Tooltip title={metadata.current_simplification_status === 'syncing' ? 'There is ongoing simplification process for this view.' : 'The simplified entities for this view are out of sync.'}>
                                        <WarningIcon fontSize="medium" color="warning" sx={{ ml: '10px' }} />
                                    </Tooltip>
                                </span> : "" } disabled={requestId > 0 || !metadata?.is_simplification_available} />
                        </Grid>
                    </Grid>
                </Grid>
                {/* zoom sliders */}
                { metadata && data?.is_simplified_entities && (
                    <Grid item className='RowItem'>
                        <Grid container flexDirection={'column'}>
                            <Grid item md={7} xl={7} xs={12} sx={{paddingLeft: '30px', paddingRight: '30px'}}>
                                <Slider
                                    aria-label="Simplification Zoom Level"
                                    defaultValue={0}
                                    getAriaValueText={(value: number) => `Zoom ${value}`}
                                    valueLabelDisplay="on"
                                    step={1}
                                    marks={marks}
                                    min={0}
                                    max={MAX_ZOOM}
                                    valueLabelFormat={value => `Zoom ${value}`}
                                    value={data?.simplification_zoom_level}
                                    onChange={(event: Event, newValue: number | number[]) => {
                                        setData({
                                            ...data,
                                            simplification_zoom_level: newValue as number
                                        })
                                    }}
                                    disabled={requestId > 0}
                                />
                            </Grid>
                            <Grid item md={7} xl={7} xs={12}>
                                <TilingConfigDisplay tiling_configs={metadata.tiling_configs} selected_zoom_level={data.simplification_zoom_level} />
                            </Grid>
                        </Grid>
                    </Grid>
                )}
                {/* submitted on */}
                {requestId > 0 && data?.id > 0 && (
                    <Grid item className='RowItem'>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Submitted On</Grid>
                            <Grid item md={9} xl={9} xs={12}>{new Date(data.submitted_on).toDateString()}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* status */}
                {requestId > 0 && data?.id > 0 && (
                    <Grid item className='RowItem'>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Status</Grid>
                            <Grid item md={9} xl={9} xs={12}>{capitalize(data.status_text.replaceAll('_', ' '))}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* errors */}
                {requestId > 0 && data?.id > 0 && (
                    <Grid item className='RowItem'>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Error message</Grid>
                            <Grid item md={9} xl={9} xs={12}>{data.errors ? data.errors : '-'}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* completed on */}
                {requestId > 0 && data?.id > 0 && data?.status === 'DONE' && (
                    <Grid item className='RowItem'>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Completed On</Grid>
                            <Grid item md={9} xl={9} xs={12}>{data.finished_at ? new Date(data.finished_at).toDateString() : '-'}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* Download link expiry on */}
                {requestId > 0 && data?.id > 0 && data?.status === 'DONE' && (
                    <Grid item className='RowItem' sx={{height: '65px'}}>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Download Link Expired On</Grid>
                            <Grid item md={9} xl={9} xs={12}>{data.download_link_expired_on ? new Date(data.download_link_expired_on).toDateString() : '-'}</Grid>
                        </Grid>
                    </Grid>
                )}
                {requestId > 0 && data?.id > 0 && data?.status === 'DONE' && (
                    <Grid item className='RowItem' sx={{height: '65px'}}>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Download File Size</Grid>
                            <Grid item md={9} xl={9} xs={12}>{humanFileSize(data.file_output_size)}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* Download link */}
                {requestId > 0 && data?.id > 0 && data?.status === 'DONE' && (
                    <Grid item className='RowItem'>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1} className='RowItemContainer'>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Download Link</Grid>
                            <Grid item md={9} xl={9} xs={12}>
                                { data.status_text !== 'expired' && data.download_link ? <span>
                                    <a href={`${data.download_link}`} target='_blank'>Download</a>
                                </span> : <span>-</span>}
                            </Grid>
                        </Grid>
                    </Grid>
                )}
                {/* Buttons */}
                {requestId > 0 && <Grid item className='RowItem'>
                    <Grid container flexDirection={'row'} justifyContent={'space-between'} className='RowItemContainer'>
                        <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>}
                            onClick={() => {
                                let _navigate_to = `/view_edit?id=${view.id}&tab=2`
                                navigate(_navigate_to)
                            }} variant="outlined">
                            Back
                        </LoadingButton>
                    </Grid>
                </Grid>}
                {filterSession && <Grid item className='RowItem'>
                    <Grid container flexDirection={'row'} justifyContent={'flex-start'} className='RowItemContainer' spacing={1}>
                        <Grid item>
                            <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>}
                                onClick={() => {
                                    let _navigate_to = `/view_edit?id=${view.id}&tab=1`
                                    navigate(_navigate_to)
                                }} variant="outlined">
                                Back
                            </LoadingButton>
                        </Grid>
                        <Grid item>
                            <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>}
                                onClick={submitExportRequest} variant="contained">
                                Add to Queue
                            </LoadingButton>
                        </Grid>
                    </Grid>
                </Grid>}
            </Grid>
        </Box>
    )
}


function ExportViewList(props: any) {
    const {view} = props
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState<any[]>([])
    const [allFinished, setAllFinished] = useState(true)
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const customColumnOptions = {
        'id': {
            'display': false,
            'filter': false
        },
        'job_uuid': {
            'filter': false,
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let rowData = tableMeta.rowData
                const handleClick = (e: any) => {
                    e.preventDefault()
                    let _navigate_to = `/view_edit?id=${view.id}&tab=2&requestId=${rowData[0]}`
                    navigate(_navigate_to)
                };
                return (
                    <a href='#' onClick={handleClick}>{`${rowData[1]}`}</a>
                )
            },
        },
        'error_message': {
            'filter': false
        },
        'download_link': {
            'filter': false,
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let rowData = tableMeta.rowData
                if (rowData[12]) {
                    return (
                        <a href={`${rowData[12]}`} target='_blank'>Download</a>
                    )
                }
                return <span>-</span>
            },
        },
        'download_expiry': {
            'filter': false,
            'label': 'Expired On',
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let rowData = tableMeta.rowData
                if (rowData[13]) {
                    return (
                        <span>{new Date(rowData[13]).toDateString()}</span>
                    )    
                }
                return <span>-</span>                
            },
        },
        'current_status': {
            'filter': true,
            'label': 'Current Status',
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                return capitalize(value.replaceAll('_', ' '))
            }
        },
        'progress': {
            'display': false,
            'filter': false
        },
        'filter_summary': {
            'display': false,
            'filter': false
        },
        'status': {
            'display': false,
            'filter': false
        }
    }

    const fetchData = (isInterval?: boolean) => {
        if (!isInterval) {
            setLoading(true)
        }
        axios.get(EXPORTER_URL + `${view.id}/list/`).then(response => {
            if (response.data) {
                setData(response.data['results'])
                setAllFinished(!response.data['is_processing'])
            } else {
                setData([])
            }
            if (!isInterval) {
                setLoading(false)
            }
        }).catch(error => {
            console.log(error)
            if (!isInterval) {
                setLoading(false)
                let _message = 'Unable to fetch export view history, Please try again or contact the administrator!'
                if (error.response) {
                    if ('detail' in error.response.data) {
                        _message = error.response.data.detail
                    }
                }
                alert(_message)
            }
        })
    }

    useEffect(() => {
        fetchData()
    }, [view])

    useEffect(() => {
        if (!allFinished) {
            if (currentInterval) {
                clearInterval(currentInterval)
                setCurrentInterval(null)
            }
            const interval = setInterval(() => {
                fetchData(true)
            }, 5000);
            setCurrentInterval(interval)
            return () => clearInterval(interval);
        }
    }, [allFinished])

    if (loading) {
        return <Loading/>
    }

    return (
        <List
            pageName={'Download History'}
            listUrl={''}
            initData={data as any[]}
            selectionChanged={null}
            onRowClick={null}
            customOptions={customColumnOptions}
            isRowSelectable={false}
            options={{
                'confirmFilters': true,
                'customFilterDialogFooter': (currentFilterList: any, applyNewFilters: any) => {
                    return (
                        <div style={{marginTop: '40px'}}>
                            <Button variant="contained" onClick={() => applyNewFilters()}>Apply Filters</Button>
                        </div>
                    );
                },
                'rowsPerPage': 100
            }}
        />
    )
}

interface ViewDownloadInterface {
    view: View
}


export default function ViewDownload(props: ViewDownloadInterface) {
    const [searchParams, setSearchParams] = useSearchParams()
    const [requestId, setRequestId] = useState(null)
    const [filterSession, setFilterSession] = useState(null)

    useEffect(() => {
        let _requestId = searchParams.get('requestId') ? parseInt(searchParams.get('requestId')) : 0
        setRequestId(_requestId)
        let _filterSession = searchParams.get('filterSession') ? searchParams.get('filterSession') : null
        setFilterSession(_filterSession)
    }, [searchParams])

    return (
        <Scrollable>
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
                {props.view?.id && <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                {requestId || filterSession ? <ExportViewDetail view={props.view} requestId={requestId} filterSession={filterSession} />
                : <ExportViewList view={props.view} />}
                </Box>}
            </Box>
        </Scrollable>
    )
}

