import React, {useEffect, useState} from "react";
import List from "../../components/List";
import '../../styles/Step3.scss';
import axios from "axios";
import clsx from 'clsx';
import {useNavigate, useSearchParams} from "react-router-dom";
import Modal from '@mui/material/Modal';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import CircularProgress from '@mui/material/CircularProgress';
import { DataGrid, GridColDef, GridColumnHeaderParams, GridCellParams } from '@mui/x-data-grid';
import {postData} from "../../utils/Requests";
import {useAppDispatch} from "../../app/hooks";
import {setPollInterval, FETCH_INTERVAL_JOB} from "../../reducers/notificationPoll";
import {ReviewListRoute} from "../../views/routes";
import Scrollable from "../../components/Scrollable";
import ColumnHeaderIcon from '../../components/ColumnHeaderIcon'
import { WizardStepInterface } from "../../models/upload";
import {utcToLocalDateTimeString} from '../../utils/Helpers';
import UploadActionStatus from "../../components/UploadActionStatus";
import AlertMessage from '../../components/AlertMessage';

const URL = '/api/entity-upload-status-list/'
const READY_TO_REVIEW_URL = '/api/ready-to-review/'

const COLUMN_DESCRIPTION: {
  [key: string]: string,
 } = {
  'Boundary Type Missing/Invalid': 'There are entities with invalid boundary types',
  'Invalid Privacy Level': 'Privacy level is higher than maximum level in dataset configuration',
  'Privacy Level Missing': 'Empty/Missing Privacy Level',
  'Upgraded Privacy Level': 'Privacy level has been upgraded to dataset minimum privacy level',
}

const columnRenderHeader = (field: string) => {
  if (field in COLUMN_DESCRIPTION) {
    return <ColumnHeaderIcon title={field} tooltipTitle={field}
      tooltipDescription={<p>{COLUMN_DESCRIPTION[field]}</p>}
    />
  }
  return <span>{field}</span>
}

const warningErrorTypes = [
  "Upgraded Privacy Level"
]

const getCellClassName = (params: GridCellParams<any, any>) => {
  if (params.value == null || params.value == 0) {
    return ''
  }
  let _is_warning_col = warningErrorTypes.includes(params.field)
  return clsx('error-summary', {
    warning: params.value > 0 && _is_warning_col,
    error: params.value > 0&& !_is_warning_col,
  })
}

const columns: GridColDef[] = [
  { field: 'Level', sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Boundary Type Missing/Invalid', width: 250, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Privacy Level Missing', width: 180, sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Invalid Privacy Level', width: 180, sortable: false, filterable: false, disableColumnMenu: true , renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName},
  { field: 'Upgraded Privacy Level', width: 200, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
]


const IN_PROGRES_STATUS_LIST = ['Started', 'Processing']

export default function Step3(props: WizardStepInterface) {
  const [uploadData, setUploadData] = useState<any[]>([])
  const [errorSummaries, setErrorSummaries] = useState<any[]>([])
  const [errorReportPath, setErrorReportPath] = useState<string>('')
  const [allFinished, setAllFinished] = useState<boolean>(false)
  const [openErrorModal, setOpenErrorModal] = useState<boolean>(false)
  const [selectedEntities, setSelectedEntities] = useState<number[]>([])
  const url = URL + `?id=${props.uploadSession}`
  const [searchParams, setSearchParams] = useSearchParams()
  const [actionUuid, setActionUuid] = useState('')
  const [alertMessage, setAlertMessage] = useState('')
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [isReadOnly, setIsReadOnly] = useState(false)
  const [customColumnOptions, setCustomColumnOptions] = useState({
    'status': {
        filter: true,
        sort: true,
        display: true,
        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          let id = tableMeta['rowData'][0]
          let isImportable = tableMeta['rowData'][6]
          let isWarning = tableMeta['rowData'][7]
          let progress = tableMeta['rowData'][8] ? tableMeta['rowData'][8] : ''
          let summaries = tableMeta['rowData'][4]
          let error_report = tableMeta['rowData'][5]
          if (IN_PROGRES_STATUS_LIST.includes(value)) {
            return <span style={{display:'flex'}}>
                    <CircularProgress size={18} />
                    <span style={{marginLeft: '5px' }}>{value}{value === 'Processing' && progress ? ` ${progress}`:''}</span>
                  </span>
          } else  if (value === 'Error') {
            if (props.isReadOnly) {
              return <span>
                      <span>{isWarning?'Warning':value}</span>
                      <Button id={`error-btn-${id}`} variant={'contained'} color={isWarning?"warning":"error"} onClick={
                        () => showError(id, summaries, error_report, isImportable)} style={{marginLeft:'10px'}}
                      >{isWarning?'Show Warning':'Show Error'}</Button>
                    </span>
            } else {
              return <Button id={`error-btn-${id}`} variant={'contained'} color={isWarning?"warning":"error"} onClick={
                        () => showError(id, summaries, error_report, isImportable)}
                      >{isWarning?'Show Warning':'Show Error'}</Button>
            }
          }
          return value
        }
    }
  })

  const getStatus = () => {
    axios.get(url).then(
      response => {
        if (response.data && response.data['is_read_only']){
          setIsReadOnly(true)
          let _results = response.data['results']
          setAllFinished(true)
          setUploadData(_results.map((responseData: any) => {
            const uploadRow: any = {}
            for (let key of Object.keys(responseData)) {
                uploadRow[key] = responseData[key]
            }
            uploadRow['started at'] = utcToLocalDateTimeString(new Date(uploadRow['started at']))
            return uploadRow
          }))
        } else if (response.data && response.data['results']) {
          let _results = response.data['results']
          const unfinished = _results.filter((responseData: any) => {
            return responseData['status'] == 'Started' || responseData['status'] == 'Processing';
          })
          if (unfinished.length == 0) {
            setAllFinished(true)
            const errors = _results.filter((responseData: any) => {
              return responseData['status'] == 'Error';
            })
            props.setEditable(true)
          } else {
            props.setEditable(false)
          }
          setUploadData(_results.map((responseData: any) => {
            const uploadRow: any = {}
            for (let key of Object.keys(responseData)) {
                uploadRow[key] = responseData[key]
            }
            uploadRow['started at'] = utcToLocalDateTimeString(new Date(uploadRow['started at']))
            return uploadRow
          }))
        }
      }
    )
  }

  useEffect(() => {
    if (uploadData.length > 0 && !allFinished) {
      const interval = setInterval(() => {
        getStatus()
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [uploadData, allFinished])

  useEffect(() => {
    getStatus()
  }, [searchParams])

  const showError = async (id: any, errorSummariesData: any[], errorPath: string, is_importable: boolean) => {
    setErrorSummaries(errorSummariesData)
    setErrorReportPath(errorPath)
    setOpenErrorModal(true)
  }

  const selectionChanged = (data: any) => {
    setSelectedEntities(data)
  }

  const downloadReport = (reportPath: string) => {
    const link = document.createElement("a");
    link.download = `error_report.csv`;
    link.href = reportPath;
    link.click();
  }

  const handleImportClick = () => {
    postData(
      READY_TO_REVIEW_URL,
      {
        'upload_entities': selectedEntities.join(',')
      }
    ).then((response) => {
      if (response.status === 200) {
        let _data = response.data
        if (_data['action_uuid']) {
          setActionUuid(_data['action_uuid'])
        } else {
          console.log('response data ', _data)
          setAlertMessage('There is unexpected error when submitting selected entities!')
        }
      }
    }).catch((error) => {
      if (error.response && error.response.data && error.response.data['detail']) {
        setAlertMessage(error.response.data['detail'])
      } else {
        setAlertMessage("Error importing data")
      }
    })
  }

  const canRowBeSelected = (dataIndex: number, rowData: any) => {
    if (isReadOnly || !allFinished)
      return false
    return rowData['is_importable']
  }

  const getColumnHeader = (header: string) => {
    if (!(header in COLUMN_DESCRIPTION)) {
      return header
    }

    return <ColumnHeaderIcon title={header} tooltipTitle={header}
      tooltipDescription={<p>{COLUMN_DESCRIPTION[header]}</p>}
    />
  }
  
  const onSessionActionError = (error: string) => {
    setActionUuid('')
    // show error to User
    setAlertMessage(error)
  }

  const onSessionActionSuccess = (result?: any) => {
    setActionUuid('')
    let _defaultError = 'There is an unxpected error from importing of selected entities! Please try again or retry from previous step!'
    // check if success validation
    let _isValid = result?.is_valid
    let _error = result?.error
    if (result) {
      if (_isValid) {
        // go to next step
        // trigger to fetch notification frequently
        dispatch(setPollInterval(FETCH_INTERVAL_JOB))
        if ((window as any).is_admin) {
          navigate(`${ReviewListRoute.path}?upload=${props.uploadSession}`)
        } else {
          navigate(ReviewListRoute.path)
        }
      } else {
        _error = _error || _defaultError
        setAlertMessage(_error)
      }
    } else {
      setAlertMessage(_defaultError)
    }
  }

  return (
    <Scrollable>
    <div className="Step3Container Step4Container">
      <Modal open={openErrorModal} onClose={() => {
            setOpenErrorModal(false)
          }}
      >
        <Box className="error-modal" sx={{minHeight: '60%'}}>
            <Grid container flexDirection={'column'} sx={{height: '100%'}}>
              <h2>Error</h2>
              <Box  sx={{width: '100%', overflowX: 'auto', height: '450px'}}>
                <DataGrid
                  getRowId={(row) => row['Level']}
                  rows={errorSummaries}
                  columns={columns}
                  sx={{
                    '& .MuiDataGrid-columnHeaderTitle': {
                      whiteSpace: 'normal',
                      lineHeight: 'normal',
                      fontWeight: '500 !important'
                    },
                    '& .MuiDataGrid-columnHeader': {
                      // Forced to use important since overriding inline styles
                      height: 'unset !important',
                      color: 'unset !important'
                    },
                    '& .MuiDataGrid-columnHeaders': {
                      // Forced to use important since overriding inline styles
                      maxHeight: '168px !important'
                    },
                  }}
                />
              </Box>
              <Box  sx={{width: '100%'}}>
              { errorReportPath ? (
                <Box className={'error-report-button-container'}>
                  <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                    <Grid item>
                    </Grid>
                    <Grid item>
                      <Button variant={'contained'} onClick={() => downloadReport(errorReportPath)}>
                        Download Error Report
                      </Button>
                    </Grid>
                  </Grid>
                  
                </Box>
              ) : null}
              </Box>
            </Grid>
        </Box>
      </Modal>
      <UploadActionStatus actionUuid={actionUuid} sessionId={props.uploadSession}
          title="Processing selected entities" onError={onSessionActionError} onSuccess={onSessionActionSuccess} />
      <AlertMessage message={alertMessage} onClose={() => setAlertMessage('')} />
      <List
        pageName={'Country'}
        listUrl={''}
        initData={uploadData}
        isRowSelectable={allFinished}
        selectionChanged={selectionChanged}
        canRowBeSelected={canRowBeSelected}
        editUrl={''}
        excludedColumns={['is_importable', 'progress', 'error_summaries', 'error_report', 'is_warning']}
        customOptions={customColumnOptions}
      />
        <div className="button-container" style={{marginLeft:0, width: '100%'}}>
          <Grid container direction='row' justifyContent='space-between'>
            <Grid item>
              <Button disabled={!allFinished} onClick={() => props.onBackClicked()} variant="outlined">
                Back
              </Button>
            </Grid>
            <Grid item>
              { !isReadOnly && (
                <Button variant="contained"
                    disabled={selectedEntities.length == 0}
                    onClick={handleImportClick}
                >Import</Button>
              )}
            </Grid>
          </Grid>

        </div>
    </div>
    </Scrollable>
  )
}
