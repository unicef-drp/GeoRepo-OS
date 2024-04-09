import React, {useState, useEffect} from "react";
import {
    Alert,
    AlertTitle,
    Button,
    Grid,
    AlertColor
} from "@mui/material";
import {Link} from 'react-router-dom';
import axios from "axios";
import '../../styles/UploadWizard.scss'
import LoadingButton from '@mui/lab/LoadingButton';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import Scrollable from '../../components/Scrollable';
import List from "../../components/List";
import LinearProgressWithLabel from "../../components/LinearProgressWithLabel";
import { BatchEntityEditInterface } from "../../models/upload";

interface Step2Interface {
    batchEdit: BatchEntityEditInterface,
    onStartToImportClicked: () => void,
    onBackClicked?: () => void,
    onClickNext?: () => void,
}

const FINAL_STATUS_LIST = ['DONE', 'ERROR', 'CANCELLED']
const LOAD_RESULT_BATCH_ENTITY_EDIT_URL = '/api/batch-entity-edit/result/'

const KNOWN_COLUMNS = ['Country', 'Level', 'Ucode', 'Default Name', 'Default Code', 'Status', 'Errors']
const FIXED_COLUM_OPTIONS = {
    'Country': {
        filter: true,
        sort: true,
        display: true,
        filterOptions: {
          fullWidth: true,
        }
    },
    'Level': {
        filter: true,
        filterOptions: {
          fullWidth: true,
        }
    },
    'Ucode': {
        filter: false,
    },
    'Default Name': {
        filter: false,
    },
    'Default Code': {
        filter: false,
    },
    'Status': {
        filter: true,
        filterOptions: {
          fullWidth: true,
        },
        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
            if (value === 'ERROR') {
                return <span className="text-error">{value}</span>
            }
            return <span className="text-success">{value}</span>
        }
    },
    'Errors': {
        filter: false,
    }
}


export default function Step2(props: Step2Interface) {
    const [loading, setLoading] = useState(true)
    const [alertTitle, setAlertTitle] = useState('')
    const [alertMessage, setAlertMessage] = useState('')
    const [alertSeverity, setAlertSeverity] = useState<AlertColor>('success')
    const [resultData, setResultData] = useState<any[]>([])
    const [customColumnOptions, setCustomColumnOptions] = useState(FIXED_COLUM_OPTIONS)

    const fetchResultData = () => {
        let _preview = props.batchEdit.status === 'PENDING' && props.batchEdit.has_preview
        axios.get(LOAD_RESULT_BATCH_ENTITY_EDIT_URL + `?batch_edit_id=${props.batchEdit.id}&preview=${_preview ? 'true':'false'}`).then(response => {
            if (response.data) {
                setResultData(response.data)
                let _customOptions:any = {...FIXED_COLUM_OPTIONS}
                let _itemKeys = Object.keys(response.data[0])
                for (let _key of _itemKeys) {
                    if (KNOWN_COLUMNS.includes(_key)) continue
                    _customOptions[_key] = {
                        'filter': false
                    }
                }
                setCustomColumnOptions(_customOptions)
            } else {
                setResultData([])
            }
            setLoading(false)
        }).catch(error => {
            setLoading(false)
            console.log(error)
            let _message = 'Unable to fetch batch edit result!'
            if (error.response) {
                if ('detail' in error.response.data) {
                    _message = error.response.data.detail
                }
            }
            alert(_message)
        })
    }

    useEffect(() => {
        if (FINAL_STATUS_LIST.includes(props.batchEdit.status)) {
            if (props.batchEdit.status === 'DONE' || props.batchEdit.status === 'ERROR') {
                fetchResultData()
            } else {
                setLoading(false)
            }
        } else if (props.batchEdit.status === 'PENDING' && props.batchEdit.has_preview) {
            fetchResultData()
        }
    }, [props.batchEdit.status])

    useEffect(() => {
        if (loading) {
            setAlertSeverity('info')
            setAlertTitle('Batch Editor is processing, please stand by...')
        } else {
            if (props.batchEdit.errors) {
                setAlertSeverity('error')
                setAlertTitle('Failed to process batch editor!')
                setAlertMessage(props.batchEdit.errors)
            } else {
                if (props.batchEdit.success_count > 0 && props.batchEdit.error_count > 0) {
                    setAlertSeverity('warning')
                } else if (props.batchEdit.success_count > 0 && props.batchEdit.error_count === 0) {
                    setAlertSeverity('success')
                } else if (props.batchEdit.success_count === 0 && props.batchEdit.error_count > 0) {
                    setAlertSeverity('error')
                }
                setAlertTitle('Batch editor processing completed.')
                setAlertMessage(props.batchEdit.success_notes)
            }
        }
    }, [loading])

    return (
        <Scrollable>
            <div className="Step3Container Step4Container Step2BatchEdit">
                <Grid container className='Step2' flexDirection='column' flex={1}>
                    <Grid item>
                        <Grid container flexDirection={'row'} justifyContent={'center'}>
                            { alertTitle ?
                                <Alert className="UploadAlertMessage" severity={alertSeverity}>
                                    <AlertTitle>{alertTitle}</AlertTitle>
                                    <p className="display-linebreak">
                                        { alertMessage }
                                    </p>
                                    { loading ? <LinearProgressWithLabel value={props.batchEdit.progress} maxBarWidth={'90%'} /> : null }
                                    { props.batchEdit.status === 'DONE' && (
                                        <div>
                                            <span className='vertical-center'>
                                                <LightbulbIcon color="warning" sx={{paddingRight: '3px'}} fontSize="small" />
                                                Please note that you will need to regenerate your vector tiles for these changes to propagate to end users.
                                            </span>
                                            <span className="AlertLink">Click <Link to={`/admin_boundaries/dataset_entities?id=${props.batchEdit.dataset_id}&tab=8`}>here</Link> to view the sync status tab.</span>
                                        </div>
                                    )}
                                </Alert> : null }
                        </Grid>
                    </Grid>
                    <Grid item flex={1}>
                        <Grid container flexDirection={'column'} sx={{height: '100%'}}>
                            { FINAL_STATUS_LIST.includes(props.batchEdit.status) || props.batchEdit.has_preview ? <List
                                pageName={'BatchEdit'}
                                listUrl={''}
                                initData={resultData}
                                isRowSelectable={false}
                                selectionChanged={(data: any) => {}}
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
                            /> : null }
                        </Grid>
                    </Grid>
                </Grid>
                <div className='button-container button-submit-container'>
                    <Grid container direction='row' justifyContent='space-between' spacing={1}>
                        <Grid item>
                            <LoadingButton loading={false} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => props.onBackClicked()} variant="outlined">
                                Back
                            </LoadingButton>
                        </Grid>
                        <Grid item>
                            { FINAL_STATUS_LIST.includes(props.batchEdit.status) ?
                                <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => props.onClickNext()} variant="contained" sx={{width: '220px !important'}}>
                                    {'Back to Dataset Detail'}
                                </LoadingButton> : null
                            }
                            { props.batchEdit.status === 'PENDING' && props.batchEdit.has_preview ?
                                <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => {
                                    setAlertSeverity('info')
                                    setAlertTitle('')
                                    setAlertMessage('')
                                    setLoading(true)
                                    props.onStartToImportClicked()
                                }} variant="contained" sx={{width: '220px !important'}}>
                                    {'Start Import'}
                                </LoadingButton> : null
                            }
                        </Grid>
                    </Grid>
                </div>
            </div>
        </Scrollable>
    )
}
