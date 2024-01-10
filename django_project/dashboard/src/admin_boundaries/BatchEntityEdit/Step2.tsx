import React, {useState, useEffect} from "react";
import {
    Alert,
    AlertTitle,
    Button,
    Grid,
    AlertColor
} from "@mui/material";
import axios from "axios";
import '../../styles/UploadWizard.scss'
import LoadingButton from '@mui/lab/LoadingButton';
import Scrollable from '../../components/Scrollable';
import List from "../../components/List";
import LinearProgressWithLabel from "../../components/LinearProgressWithLabel";
import { BatchEntityEditInterface } from "../../models/upload";

interface Step2Interface {
    batchEdit: BatchEntityEditInterface,
    onBackClicked?: () => void,
    onClickNext?: () => void,
}

const FINAL_STATUS_LIST = ['DONE', 'ERROR', 'CANCELLED']
const LOAD_RESULT_BATCH_ENTITY_EDIT_URL = '/api/batch-entity-edit/result/'

const KNOWN_COLUMNS = ['Country', 'Level', 'Ucode', 'Default Name', 'Default Code', 'Status', 'Errors']

export default function Step2(props: Step2Interface) {
    const [loading, setLoading] = useState(true)
    const [alertTitle, setAlertTitle] = useState('')
    const [alertMessage, setAlertMessage] = useState('')
    const [alertSeverity, setAlertSeverity] = useState<AlertColor>('success')
    const [resultData, setResultData] = useState<any[]>([])
    const [customColumnOptions, setCustomColumnOptions] = useState({
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
    })

    const fetchResultData = () => {
        axios.get(LOAD_RESULT_BATCH_ENTITY_EDIT_URL + `?batch_edit_id=${props.batchEdit.id}`).then(response => {
            if (response.data) {
                setResultData(response.data)
                let _customOptions:any = {...customColumnOptions}
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
            if (props.batchEdit.status === 'DONE') {
                fetchResultData()
            } else {
                setLoading(false)
            }
        }
    }, [props.batchEdit.status])

    useEffect(() => {
        if (loading) {
            setAlertSeverity('info')
            setAlertTitle('Processing Batch Entity Edit in the background!')
        } else {
            if (props.batchEdit.errors) {
                setAlertSeverity('error')
                setAlertTitle('Failed to process batch entity edit!')
                setAlertMessage(props.batchEdit.errors)
            } else {
                if (props.batchEdit.success_count > 0 && props.batchEdit.error_count > 0) {
                    setAlertSeverity('warning')
                } else if (props.batchEdit.success_count > 0 && props.batchEdit.error_count === 0) {
                    setAlertSeverity('success')
                } else if (props.batchEdit.success_count === 0 && props.batchEdit.error_count > 0) {
                    setAlertSeverity('error')
                }
                setAlertTitle('System has finished processing batch entity edit!')
                setAlertMessage(props.batchEdit.success_notes)
            }
        }
    }, [loading])

    return (
        <Scrollable>
            <div className="Step3Container Step4Container">
                <Grid container className='Step2' flexDirection='column' flex={1}>
                    <Grid item>
                        <Grid container flexDirection={'row'} justifyContent={'center'}>
                            { alertTitle ?
                                <Alert className="UploadAlertMessage" severity={alertSeverity}>
                                    <AlertTitle>{alertTitle}</AlertTitle>
                                    <p className="display-linebreak">
                                        { alertMessage }
                                    </p>
                                    { loading ? <LinearProgressWithLabel value={props.batchEdit.progress} /> : null }
                                </Alert> : null }
                        </Grid>
                    </Grid>
                    <Grid item flex={1}>
                        <Grid container flexDirection={'column'} sx={{height: '100%'}}>
                            { FINAL_STATUS_LIST.includes(props.batchEdit.status) ? <List
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
                            <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => props.onClickNext()} variant="contained" sx={{width: '220px !important'}}>
                                {'Back to Dataset Detail'}
                            </LoadingButton>
                        </Grid>
                    </Grid>
                </div>
            </div>
        </Scrollable>
    )
}
