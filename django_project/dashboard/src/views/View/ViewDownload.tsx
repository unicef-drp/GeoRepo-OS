import React, {useEffect, useRef, useState} from 'react';
import Grid from '@mui/material/Grid';
import Box from "@mui/material/Box";
import View from "../../models/view";
import axios from "axios";
import {useNavigate, useSearchParams} from "react-router-dom";
import {RootState} from "../../app/store";
import LinearProgress from '@mui/material/LinearProgress';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import Scrollable from '../../components/Scrollable';
import List from "../../components/List";
import Loading from "../../components/Loading";
import { EntitiesFilterInterface } from '../Dataset/EntitiesFilter';
import { TilingConfig } from '../../models/tiling';
import '../../styles/ViewDownload.scss';
import LoadingButton from '@mui/lab/LoadingButton';
import {postData} from "../../utils/Requests";


const EXPORTER_URL = '/api/exporter/'
const ONGOING_STATUS_LIST = ['PENDING', 'PROCESSING']
interface MetadataInterface {
    filters: EntitiesFilterInterface;
    available_formats: string[];
    is_simplification_available: boolean;
    tiling_configs: TilingConfig[];
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
}


function EntityFilters(props: any) {
    const {filters} = props

    if (filters === null || Object.keys(filters).length === 0) {
        return <span>-</span>
    }

    return (
        <div>Placeholders</div>
    )
}

function ExportViewDetail(props: any) {
    const {view, requestId, filterSession} = props
    const [loading, setLoading] = useState(true)
    const navigate = useNavigate()
    const [metadata, setMetadata] = useState<MetadataInterface>(null)
    const [data, setData] = useState<ExportRequestDetailInterface>(null)
    const [currentInterval, setCurrentInterval] = useState<any>(null)

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
                setData(response.data as ExportRequestDetailInterface)
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
                let _message = 'Unable to fetch export view detail, Please try again or contact the administrator!'
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
            }
          ).catch(error => {
            alert('Error submitting download request...')
        })
    }


    if (loading) {
        return <Loading/>
    }

    return (
        <Box className='ExportViewDetail'>
            <Grid container display={'flex'} flexDirection={'column'}>
                <Grid item>
                    <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                        <Grid item className='Title' md={3} xl={3} xs={12}>Filters</Grid>
                        <Grid item md={9} xl={9} xs={12}>
                            { requestId > 0 && data && <EntityFilters filters={data.filters} /> }
                            { filterSession && metadata && <EntityFilters filters={metadata.filters} /> }
                        </Grid>
                    </Grid>
                </Grid>
                <Grid item>
                    <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                        <Grid item className='Title' md={3} xl={3} xs={12}>Format</Grid>
                        <Grid item md={9} xl={9} xs={12}>
                            <FormControl sx={{minWidth: '300px'}} disabled={requestId > 0 || (filterSession && !metadata?.is_simplification_available)}>
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
                <Grid item>
                    <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                        <Grid item className='Title' md={3} xl={3} xs={12}>Extract simplified geometries</Grid>
                        <Grid item md={9} xl={9} xs={12}>
                            <FormControlLabel control={<Checkbox value={data?.is_simplified_entities} checked={data?.is_simplified_entities}
                                onChange={(val) => setData({...data, is_simplified_entities: val.target.checked})}/>}
                                label="" />
                        </Grid>
                    </Grid>
                </Grid>
                {/* zoom sliders */}
                <Grid item></Grid>
                {/* submitted on */}
                {requestId > 0 && data?.id && (
                    <Grid item>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Submitted On</Grid>
                            <Grid item md={9} xl={9} xs={12}>{new Date(data.submitted_on).toDateString()}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* status */}
                {requestId > 0 && data?.id && (
                    <Grid item>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Status</Grid>
                            <Grid item md={9} xl={9} xs={12}>{data.status_text}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* errors */}
                {requestId > 0 && data?.id && data?.errors && (
                    <Grid item>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Error message</Grid>
                            <Grid item md={9} xl={9} xs={12}>{data.errors}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* completed on */}
                {requestId > 0 && data?.id && data?.status == 'DONE' && (
                    <Grid item>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Completed On</Grid>
                            <Grid item md={9} xl={9} xs={12}>{new Date(data.finished_at).toDateString()}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* Download link expiry on */}
                {requestId > 0 && data?.id && data?.status == 'DONE' && (
                    <Grid item>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Download Link Expired On</Grid>
                            <Grid item md={9} xl={9} xs={12}>{new Date(data.download_link_expired_on).toDateString()}</Grid>
                        </Grid>
                    </Grid>
                )}
                {/* Download link */}
                {requestId > 0 && data?.id && data?.status == 'DONE' && (
                    <Grid item>
                        <Grid container display={'flex'} flexDirection={'row'} spacing={1}>
                            <Grid item className='Title' md={3} xl={3} xs={12}>Download Link</Grid>
                            <Grid item md={9} xl={9} xs={12}>
                                { data.status_text !== 'expired' ? <span>
                                    <a href={`${data.download_link}`} target='_blank'>Download</a>
                                </span> : <span>-</span>}
                            </Grid>
                        </Grid>
                    </Grid>
                )}
                {/* Buttons */}
                {requestId > 0 && <Grid item>
                    <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                        <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>}
                            onClick={() => {
                                let _navigate_to = `/view_edit?id=${view.id}&tab=2`
                                navigate(_navigate_to)
                            }} variant="outlined">
                            Back
                        </LoadingButton>
                    </Grid>
                </Grid>}
                {filterSession && <Grid item>
                    <Grid container flexDirection={'row'} justifyContent={'flex-end'}>
                        <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>}
                            onClick={submitExportRequest} variant="contained">
                            Add to Queue
                        </LoadingButton>
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
                return (
                    <a href={`${rowData[12]}`} target='_blank'>Download</a>
                )
            },
        },
        'download_expiry': {
            'filter': false,
            'label': 'Expired On',
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let rowData = tableMeta.rowData
                return (
                    <span>{new Date(rowData[13]).toDateString()}</span>
                )
            },
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
                fetchData()
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
            options={{
                'confirmFilters': true,
                'customFilterDialogFooter': (currentFilterList: any, applyNewFilters: any) => {
                    return (
                        <div style={{marginTop: '40px'}}>
                            <Button variant="contained" onClick={() => applyNewFilters()}>Apply Filters</Button>
                        </div>
                    );
                },
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

