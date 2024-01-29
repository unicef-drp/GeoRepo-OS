import React, {useEffect, useRef, useState} from 'react';
import Grid from '@mui/material/Grid';
import { Box, Button } from "@mui/material";
import View from "../../models/view";
import axios from "axios";
import {useNavigate, useSearchParams} from "react-router-dom";
import {RootState} from "../../app/store";
import LinearProgress from '@mui/material/LinearProgress';
import Scrollable from '../../components/Scrollable';
import List from "../../components/List";
import Loading from "../../components/Loading";


const EXPORTER_URL = '/api/exporter/'


function ExportViewDetail(props: any) {
    return (
        <div>ExportViewDetail</div>
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
                let _message = 'Unable to fetch export view history!'
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
    console.log('ViewDownload render')
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
                {props.view && <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                {requestId || filterSession ? <ExportViewDetail view={props.view} requestId={requestId} filterSession={filterSession} />
                : <ExportViewList view={props.view} />}
                </Box>}
            </Box>
        </Scrollable>
    )
}

