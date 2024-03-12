import React, {useEffect, useState, useRef, useCallback} from "react";
import clsx from 'clsx';
import {TABLE_OFFSET_HEIGHT} from "../../components/List";
import Loading from "../../components/Loading";
import '../../styles/Step3.scss';
import axios from "axios";
import {useNavigate, useSearchParams} from "react-router-dom";
import Modal from '@mui/material/Modal';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import IconButton from '@mui/material/IconButton';
import Autocomplete from '@mui/material/Autocomplete';
import Checkbox from '@mui/material/Checkbox';
import TextField from '@mui/material/TextField';
import CloseIcon from '@mui/icons-material/Close';
import LoadingButton from "@mui/lab/LoadingButton";
import { DataGrid, GridColDef, GridColumnGroupingModel, GridColumnHeaderParams, GridCellParams, allGridColumnsSelector } from '@mui/x-data-grid';
import CircularProgress from '@mui/material/CircularProgress';
import {postData} from "../../utils/Requests";
import {useAppDispatch} from "../../app/hooks";
import {setPollInterval, FETCH_INTERVAL_JOB} from "../../reducers/notificationPoll";
import {ReviewListRoute} from "../../views/routes";
import Scrollable from "../../components/Scrollable";
import Step4OverlapsError from './Step4OverlapsError'
import ColumnHeaderIcon from '../../components/ColumnHeaderIcon'
import { WizardStepInterface } from "../../models/upload";
import {utcToLocalDateTimeString} from '../../utils/Helpers';
import UploadActionStatus from "../../components/UploadActionStatus";
import AlertMessage from '../../components/AlertMessage';
import LinearProgressWithLabel from "../../components/LinearProgressWithLabel";
import SyncIcon from '@mui/icons-material/Sync';
import ErrorIcon from '@mui/icons-material/Error';
import HtmlTooltip from "../../components/HtmlTooltip";
import StatusLoadingDialog from "../../components/StatusLoadingDialog";
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import FilterAlt from "@mui/icons-material/FilterAlt";
import ResizeTableEvent from "../../components/ResizeTableEvent";
import MUIDataTable, {debounceSearchRender, MUISortOptions, SelectableRows} from "mui-datatables";
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import FormControlLabel from "@mui/material/FormControlLabel";


const URL = '/api/entity-upload-status-list/'
const METADATA_URL = '/api/entity-upload-status-metadata/'
const READY_TO_REVIEW_URL = '/api/ready-to-review/'
const FilterIcon: any = FilterAlt
const checkBoxOutlinedicon = <CheckBoxOutlineBlankIcon fontSize="small" />;
const checkBoxCheckedIcon = <CheckBoxIcon fontSize="small" />;
const MAX_COUNTRIES_IN_FILTER_CHIP = 5


const columnRenderHeader = (field: string) => {
  if (field in COLUMN_DESCRIPTION) {
    return <ColumnHeaderIcon title={field} tooltipTitle={field}
      tooltipDescription={<p>{COLUMN_DESCRIPTION[field]}</p>}
    />
  }
  return <span>{field}</span>
}

const warningErrorTypes = [
  "Self Intersects",
  "Self Contacts",
  "Duplicate Nodes",
  "Gaps",
  "Upgraded Privacy Level"
]

const blockingErrorTypes = [
  "Polygon with less than 4 nodes",
  "Duplicated Geometries",
  "Feature within other features",
  "Overlaps",
  "Not Within Parent",
  "Parent Code Missing",
  "Default Code Missing",
  "Default Name Missing",
  "Duplicated Codes",
  "Invalid Privacy Level",
  "Privacy Level Missing",
  "Parent Missing"
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
  { field: 'Entity', width: 150, sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Self Intersects', width: 150, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  // hide self contacts
  // { field: 'Self Contacts', sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Duplicate Nodes', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Polygon with less than 4 nodes', width: 150, sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Overlaps', width: 120, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Gaps', width: 120, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Duplicated Geometries', width: 150, sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Feature within other features', width: 150, sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Not Within Parent', width: 170, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Parent Code Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Default Code Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Default Name Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Privacy Level Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Parent Missing', width: 160, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Duplicated Codes', width: 170, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Invalid Privacy Level', width: 180, sortable: false, filterable: false, disableColumnMenu: true , renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName},
  { field: 'Upgraded Privacy Level', width: 200, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
]

const columnGroupingModel: GridColumnGroupingModel = [
  {
    groupId: 'Geometry Validity Checks',
    description: '',
    children: [
      { field: 'Self Intersects' },
      // { field: 'Self Contacts' },
      { field: 'Duplicate Nodes' },
      { field: 'Polygon with less than 4 nodes' },
    ],
  },
  {
    groupId: 'Geometry Topology Checks',
    description: '',
    children: [
      { field: 'Overlaps' },
      { field: 'Gaps' },
      { field: 'Duplicated Geometries' },
      { field: 'Feature within other features' },
      { field: 'Not Within Parent' },
    ],
  },
  {
    groupId: 'Attributes Checks',
    description: '',
    children: [
      { field: 'Parent Code Missing' },
      { field: 'Default Code Missing' },
      { field: 'Default Name Missing' },
      { field: 'Privacy Level Missing' },
      { field: 'Parent Missing' },
      { field: 'Duplicated Codes' },
      { field: 'Invalid Privacy Level' },
      { field: 'Upgraded Privacy Level' },
    ],
  },
]

const COLUMN_DESCRIPTION: {
  [key: string]: string,
 } = {
  'Self Intersects': 'Check for self-intersects using GEOSisValidDetail with flag 1',
  'Duplicate Nodes': 'Check for duplicate nodes',
  'Polygon with less than 4 nodes': 'Check if polygon with less than 4 nodes',
  'Overlaps': 'Check for overlapping polygons smaller than (map units sqr.)',
  'Gaps': 'Checks for gaps between neighbouring polygons smaller than (map units sqr.)',
  'Duplicated Geometries': 'There are entities in the same level with same geometries',
  'Feature within other features': 'Check whether feature is within other features',
  'Not Within Parent': 'Child geometry is not within parent geometry',
  'Parent Code Missing': 'Empty/Missing Parent Id Field',
  'Default Code Missing': 'Empty/Missing Default Code/Id Field',
  'Default Name Missing': 'Empty/Missing Default Name',
  'Privacy Level Missing': 'Empty/Missing Privacy Level',
  'Parent Missing': 'Cannot find parent from upper level by its Parent Id Field',
  'Duplicated Codes': 'There is default code that is not unique',
  'Invalid Privacy Level': 'Privacy level is higher than maximum level in dataset configuration',
  'Upgraded Privacy Level': 'Privacy level has been upgraded to dataset minimum privacy level',
}

const STATUS_LIST = ['Not Completed', 'Queued', 'Processing', 'Error', 'Warning', 'Valid', 'Approved', 'Rejected', 'Stopped with Error'].sort()
const INCOMPLETE_STATUS_LIST = ['Started', 'Queued', 'Processing']
const IN_PROGRES_STATUS_LIST = ['Processing']
const COMPLETED_STATUS_LIST = ['Error', 'Warning', 'Valid', 'Approved', 'Rejected', 'Stopped with Error']

const DOWNLOAD_ERROR_REPORT_URL = '/api/entity-upload-error-download/'
const RETRIGGER_VALIDATION_URL = '/api/entity-upload-status/retrigger-validation/'

interface StatusSummaryDict {
  [Key: string]: number;
}

interface Step4FilterInterface {
  status: string[],
  search_text: string,
  countries: string[]
}


const getDefaultFilter = (): Step4FilterInterface => {
  return {
    status: [],
    search_text: '',
    countries: []
  }
}

const USER_COLUMNS = [
  'id',
  'started_at',
  'error_summaries',
  'error_report',
  'is_importable',
  'is_warning',
  'progress',
  'country',
  'status',
  'error_logs'
]

const VISIBLE_COLUMNS = [
  'country',
  'started at',
  'status'
]


export default function Step4(props: WizardStepInterface) {
  const [uploadData, setUploadData] = useState<any[]>([])
  const [errorSummaries, setErrorSummaries] = useState<any[]>([])
  const [errorReportId, setErrorReportId] = useState<number>(0)
  const [hasErrorOverlaps, setHasErrorOverlaps] = useState(false)
  const [viewOverlapId, setViewOverlapId] = useState<number>(null)
  const [allFinished, setAllFinished] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)
  const [openErrorModal, setOpenErrorModal] = useState<boolean>(false)
  const [selectedEntities, setSelectedEntities] = useState<number[]>([])
  const [selectedEntitiesInPage, setSelectedEntitiesInPage] = useState<number[]>([])
  const url = URL + `?id=${props.uploadSession}`
  const [searchParams, setSearchParams] = useSearchParams()
  const [actionUuid, setActionUuid] = useState('')
  const [alertMessage, setAlertMessage] = useState('')
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [viewOverlapError, setViewOverlapError] = useState(false)
  const [statusSummary, setStatusSummary] = useState<StatusSummaryDict>({})
  const [jobSummaryText, setJobSummaryText] = useState('-')
  const [jobSummaryProgress, setJobSummaryProgress] = useState(0)
  const [retriggerLoadingOpen, setRetriggerLoadingOpen] = useState<boolean>(false)
  const [tableColumns, setTableColumns] = useState<any>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
  const [currentFilters, setCurrentFilters] = useState<Step4FilterInterface>(getDefaultFilter())
  const [allIds, setAllIds] = useState<number[]>([])
  const axiosSource = useRef(null)
  const newCancelToken = useCallback(() => {
    axiosSource.current = axios.CancelToken.source();
    return axiosSource.current.token;
  }, [])
  const ref = useRef(null)
  const [tableHeight, setTableHeight] = useState(0)
  const [selectableRowsMode, setSelectableRowsMode] = useState<SelectableRows>('none')
  const [isCheckAll, setIsCheckAll] = useState(false)
  const [currentInterval, setCurrentInterval] = useState(null)

  const retriggerValidation = (id:number, title: string) => {
    setRetriggerLoadingOpen(true)
    axios.get(`${RETRIGGER_VALIDATION_URL}${id}/`).then(
      response => {
        setRetriggerLoadingOpen(false)
        setAlertMessage(`Successfully retrigger validation for ${title}!`)
        getStatus()
        setAllFinished(false)
        // trigger to fetch notification frequently
        dispatch(setPollInterval(FETCH_INTERVAL_JOB))
      }
    ).catch((error) => {
      setRetriggerLoadingOpen(false)
      console.log('Failed to retrigger validation ', error)
      setAlertMessage(`There is unexpected error when retrigger validation for ${title}! Please try again later or contact administrator!`)
    })
  }

  const getExistingFilterValue = (col_name: string):string[] =>  {
    let values:string[] = []
    switch (col_name) {
        case 'country':
            values = currentFilters.countries
            break;
        case 'status':
          values = currentFilters.status
          break;
        default:
          break;
    }
    return values
  }

  const fetchMetadata = () => {
    setLoading(true)
    axios.get(`${METADATA_URL}?id=${props.uploadSession}`).then(
      response =>{
        let _countries = response.data['countries']
        let _allIds = response.data['ids'] as number[]
        let _isAllFinished = response.data['is_all_finished']
        let _level_name_0 = response.data['level_name_0']
        let _isReadOnly = response.data['is_read_only']
        setAllIds(_allIds)
        let _init_columns = USER_COLUMNS
        let _columns = _init_columns.map((columnName) => {
          let _options: any = {
            name: columnName,
            label: columnName === 'country' ? _level_name_0 : columnName.charAt(0).toUpperCase() + columnName.slice(1).replaceAll('_', ' '),
            options: {
              display: VISIBLE_COLUMNS.includes(columnName),
              sort: false,
              filter: false,
              searchable: false
            }
          }
          if (columnName === 'country') {
            _options.options = {
              display: true,
              sort: false,
              searchable: false,
              filter: false
            }
          } else if (columnName === 'status') {
            _options.options = {
              display: true,
              sort: false,
              searchable: false,
              filter: true,
              filterList: _isAllFinished ? [] : ['Not Completed'],
              filterOptions: {
                fullWidth: true,
                names: STATUS_LIST,
                logic(val:any, filters:any) {
                  if (filters[0]) {
                    if (filters[0] === 'Not Completed') {
                      return !INCOMPLETE_STATUS_LIST.includes(val)
                    }
                    return val !== filters[0]
                  }
                  return false
                }
              },
              customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
                // 'id' 0,
                // 'started_at' 1,
                // 'error_summaries' 2,
                // 'error_report' 3,
                // 'is_importable' 4,
                // 'is_warning' 5,
                // 'progress' 6,
                // 'country' 7,
                // 'status' 8,
                // 'error_logs' 9
                let id = tableMeta['rowData'][0]
                let name = tableMeta['rowData'][7]
                let isImportable = tableMeta['rowData'][4]
                let isWarning = tableMeta['rowData'][5]
                let progress = tableMeta['rowData'][6] ? tableMeta['rowData'][6] : ''
                let summaries = tableMeta['rowData'][2]
                let error_report = tableMeta['rowData'][3]
                let error_logs = tableMeta['rowData'][9]
                if (IN_PROGRES_STATUS_LIST.includes(value)) {
                  return <span style={{display:'flex'}}>
                          <CircularProgress size={18} />
                          <span style={{marginLeft: '5px' }}>{value}{value === 'Processing' && progress ? ` ${progress}`:''}</span>
                        </span>
                } else if (value === 'Error' || value === 'Warning') {
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
                } else if (value === 'Stopped with Error') {
                  return (
                    <span className="error-status-container">
                      <span className="error-status-label">{value}</span>
                      {error_logs && (
                        <HtmlTooltip tooltipTitle='Error Detail' icon={<ErrorIcon fontSize="small" color="error" />}
                          tooltipDescription={<p>{error_logs}</p>}
                      />
                      )}
                      <IconButton aria-label={'Retrigger validation'} title={'Retrigger validation'}
                        onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                          e.currentTarget.disabled = true
                          retriggerValidation(id as number, name)
                        }}>
                        <SyncIcon color='info' fontSize='small' />
                    </IconButton>
                    </span>
                  )
                }
                return value
              }
            }
          }
          return _options
        })
        setTableColumns(_columns)
        if (_isReadOnly) {
          setAllFinished(true)
        } else {
          setAllFinished(_isAllFinished)
          if (!_isAllFinished) {
            setCurrentFilters({
              ...currentFilters,
              status: ['Not Completed']
            })
            props.setEditable(false)
          } else {
            props.setEditable(true)
            if (props.onCheckProgress) {
              props.onCheckProgress()
            }
          }
        }
      }
    ).catch((error) => {
      console.log('Failed to fetch metadata ', error)
      setAlertMessage(`There is unexpected error when loading the metadata! Please try again later or contact administrator!`)
    })
  }

  const getStatus = (isFromInterval: boolean = false) => {
    if (axiosSource.current) axiosSource.current.cancel()
    let cancelFetchToken = newCancelToken()
    axios.post(
        url + `&page=${pagination.page + 1}&page_size=${pagination.rowsPerPage}`,
        {
          'countries': currentFilters.countries,
          'search_text': currentFilters.search_text,
          'status': currentFilters.status
        },
        {
          cancelToken: cancelFetchToken
        }
      ).then(
      response => {
        setLoading(false)
        setTotalCount(response.data['count'])
        if (response.data && response.data['is_read_only']){
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
          if (response.data['is_all_finished']) {
            setAllFinished(true)
            if (isFromInterval) {
              // remove filter status
              if (currentFilters.status.includes('Not Completed')) {
                setCurrentFilters({...currentFilters, 'status': []})
              }
            }
          }
          setUploadData(_results.map((responseData: any) => {
            const uploadRow: any = {}
            for (let key of Object.keys(responseData)) {
                uploadRow[key] = responseData[key]
            }
            uploadRow['started at'] = utcToLocalDateTimeString(new Date(uploadRow['started at']))
            return uploadRow
          }))
          let _inPage = []
          for (let i=0; i<_results.length; i++) {
            if (selectedEntities.includes(_results[i].id)) {
              _inPage.push(i)
            }
          }
          setSelectedEntitiesInPage(_inPage)
          setStatusSummary(response.data['summary'])
        }
      }
    ).catch(error => {
      if (!axios.isCancel(error)) {
        console.log(error)
      }
    })
  }

  useEffect(() => {
    fetchMetadata()
  }, [])

  const updateTableColumnFilter = () => {
    if (currentFilters.status) {
      let _tableColumns = [...tableColumns]
      let idx = _tableColumns.findIndex((t) => t.name === 'status')
      if (idx > -1) {
        _tableColumns[idx]['options']['filterList'] = getExistingFilterValue('status')
        setTableColumns([..._tableColumns])
      }
    }
  }

  useEffect(() => {
    updateTableColumnFilter()
  }, [currentFilters])

  useEffect(() => {
    if (allFinished) {
      setSelectableRowsMode('multiple')
    } else {
      setSelectableRowsMode('none')
    }
    if (!allFinished) {
      const interval = setInterval(() => {
        getStatus(true)
      }, 5000);
      setCurrentInterval(interval)
      return () => {
        clearInterval(interval);
        setCurrentInterval(null);
      };
    } else {
      getStatus()
    }
  }, [allFinished, currentFilters, pagination])

  useEffect(() => {
    const statusFilter = searchParams.get('filter_status')
    if (statusFilter === 'All') {
      setCurrentFilters({...currentFilters, 'status': []})
      // TODO: set status filter
      // let _statusFilter = {...customColumnOptions['status']} as any
      // if ('filterList' in _statusFilter) {
      //   _statusFilter['filterList'] = []
      //   setCustomColumnOptions({
      //     ...customColumnOptions,
      //     'status': {..._statusFilter}
      //   })
      // }
    }
  }, [searchParams])

  useEffect(() => {
    let _totalJob = 0
    let _completedJob = 0
    let _summaries = []

    for (const [key, value] of Object.entries(statusSummary)) {
      _totalJob += value
      _summaries.push(`${value} ${key.toLowerCase()}`)
      if (COMPLETED_STATUS_LIST.indexOf(key) > -1) {
        _completedJob += value
      }
    }
    if (_totalJob > 0) {
      setJobSummaryText(_summaries.join(', '))
      setJobSummaryProgress(_completedJob * 100/_totalJob)
    } else {
      setJobSummaryProgress(0)
      setJobSummaryText('-')
    }
  }, [statusSummary])

  const showError = async (id: any, errorSummariesData: any[], errorPath: string, is_importable: boolean) => {
    setErrorSummaries(errorSummariesData)
    setErrorReportId(id)
    let _hasErrorOverlaps = false
    let _view_overlaps = null
    for (let summary of errorSummariesData) {
      if (summary['Overlaps'] > 0) {
        _hasErrorOverlaps = true
        _view_overlaps = id
        break
      }
    }
    // show overlaps error when there is only overlaps error and no other error
    // because current logic will remove the entities
    setHasErrorOverlaps(_hasErrorOverlaps && is_importable)
    setViewOverlapId(_view_overlaps)
    setOpenErrorModal(true)
  }

  const downloadReport = (reportPathId: number) => {
    const link = document.createElement("a");
    link.download = `error_report.csv`;
    link.href = `${DOWNLOAD_ERROR_REPORT_URL}${reportPathId}/`;
    link.click();
  }

  const handleImportClick = () => {
    setLoading(true)
    postData(
      READY_TO_REVIEW_URL,
      {
        'upload_entities': selectedEntities.join(',')
      }
    ).then((response) => {
      setLoading(false)
      if (response.status === 200) {
        let _data = response.data
        if (_data['action_uuid']) {
          setActionUuid(_data['action_uuid'])
        } else {
          console.log('response data ', _data)
          setAlertMessage('There is unexpected error when submitting selected countries!')
        }
      }
    }).catch((error) => {
      setLoading(false)
      if (error.response && error.response.data && error.response.data['detail']) {
        setAlertMessage(error.response.data['detail'])
      } else {
        setAlertMessage("Error importing data")
      }
    })
  }

  const canRowBeSelected = (dataIndex: number, rowData: any) => {
    if (props.isReadOnly || !allFinished)
      return false
    return rowData['is_importable']
  }

  const onSessionActionError = (error: string) => {
    setActionUuid('')
    // show error to User
    setAlertMessage(error)
  }

  const onSessionActionSuccess = (result?: any) => {
    setActionUuid('')
    let _defaultError = 'There is an unexpected error from importing of selected countries! Please try again or retry from previous step!'
    // check if success validation
    let _isValid = result?.is_valid
    let _error = result?.error
    if (result) {
      if (_isValid) {
        // go to next step
        // trigger to fetch notification frequently
        dispatch(setPollInterval(FETCH_INTERVAL_JOB))
        navigate(`${ReviewListRoute.path}?upload=${props.uploadSession}`)
      } else {
        _error = _error || _defaultError
        setAlertMessage(_error)
      }
    } else {
      setAlertMessage(_defaultError)
    }
  }

  const onTableInteraction = () => {
    setLoading(true)
    setUploadData([])
    // cancel any ongoing request and iterval
    if (currentInterval) {
      clearInterval(currentInterval)
      setCurrentInterval(null)
    }
    if (axiosSource.current) {
      axiosSource.current.cancel()
    }
  }

  useEffect(() => {
    if (isCheckAll) {
      setSelectedEntities([...allIds])
      let _inPage = uploadData.map((a, index) => index)
      setSelectedEntitiesInPage(_inPage)
    } else {
      setSelectedEntities([])
      setSelectedEntitiesInPage([])
    }
  }, [isCheckAll])

  const onTableChangeState = (action: string, tableState: any) => {
    switch (action) {
      case 'changePage':
        onTableInteraction()
        setPagination({
          ...pagination,
          page: tableState.page
        })
        break;
      case 'sort':
        onTableInteraction()
        setPagination({
          ...pagination,
          page: 0,
          sortOrder: tableState.sortOrder
        })
        break;
      case 'changeRowsPerPage':
        onTableInteraction()
        setPagination({
          ...pagination,
          page: 0,
          rowsPerPage: tableState.rowsPerPage
        })
        break;
      default:
    }
  }

  const handleSearchOnChange = (search_text: string) => {
    onTableInteraction()
    setPagination({
      ...pagination,
      page: 0,
      sortOrder: {}
    })
    setCurrentFilters({...currentFilters, 'search_text': search_text})
    setSelectedEntities([])
    setSelectedEntitiesInPage([])
    setIsCheckAll(false)
  }

  const handleFilterChange = (applyFilters: any) => {
    onTableInteraction()
    setPagination({
      ...pagination,
      page: 0,
      sortOrder: {}
    })
    let filterList = applyFilters()
    let filter = getDefaultFilter()
    type Column = {
      name: string,
      label: string,
      options: any
    }
    for (let idx in filterList) {
      let col: Column = tableColumns[idx]
      if (!col.options.filter)
        continue
      if (filterList[idx] && filterList[idx].length) {
        const key = col.name as string
        filter[key as keyof Step4FilterInterface] = filterList[idx]
      }
    }
    setCurrentFilters({...filter, 'search_text': currentFilters['search_text']})
    setSelectedEntities([])
    setSelectedEntitiesInPage([])
    setIsCheckAll(false)
  }

  const handleCountriesOnClear = () => {
    let _currentFilters = {...currentFilters}
    setCurrentFilters({
      ..._currentFilters,
      countries: []
    })
  }

  return (
    <Scrollable>
    <div className="Step3Container Step4Container" ref={ref}>
      <Modal open={openErrorModal} onClose={() => {
            setOpenErrorModal(false)
            setViewOverlapError(false)
          }}
      >
        <Box className="error-modal" sx={{minHeight: '60%'}}>
          { viewOverlapError && <Step4OverlapsError upload_id={viewOverlapId} onBackClicked={() => setViewOverlapError(false)} /> }
          { !viewOverlapError && (
            <Grid container flexDirection={'column'} sx={{height: '100%', flex: 1}}>
              <Grid container flexDirection={'row'} justifyContent={'flex-end'}>
                <Grid item>
                  <IconButton aria-label="close" title='close' onClick={() => {
                    setOpenErrorModal(false)
                    setViewOverlapError(false)
                  }}>
                      <CloseIcon fontSize='medium' />
                  </IconButton>
                </Grid>
              </Grid>
              <h2 className="error-modal-title">Error Report</h2>
              <Box  sx={{width: '100%', overflowX: 'auto', height: '450px'}}>
                <DataGrid
                  getRowId={(row) => row['Level']}
                  experimentalFeatures={{ columnGrouping: true }}
                  rows={errorSummaries}
                  columns={columns}
                  columnGroupingModel={columnGroupingModel}
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
              { errorReportId ? (
                <Box className={'error-report-button-container'}>
                  <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                    <Grid item>
                      {/* { hasErrorOverlaps && <Button variant={'outlined'} onClick={() => setViewOverlapError(true)}>
                        View Overlaps Error
                      </Button>} */}
                      <Button variant={'contained'} onClick={() => downloadReport(errorReportId)}>
                        Download Error Report
                      </Button>
                    </Grid>
                    <Grid item>
                    </Grid>
                  </Grid>
                  
                </Box>
              ) : null}
              </Box>
            </Grid>
          )}
        </Box>
      </Modal>
      <UploadActionStatus actionUuid={actionUuid} sessionId={props.uploadSession}
          title="Processing selected countries" onError={onSessionActionError}
          onSuccess={onSessionActionSuccess} description="Please do not close this page while background task is in progress..."/>
      <AlertMessage message={alertMessage} onClose={() => setAlertMessage('')} />
      <StatusLoadingDialog open={retriggerLoadingOpen}
            title={'Retrigger Validation'} description={'Please wait while we are submitting your request!'} />
      
      <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                                onResize={(clientHeight: number) => setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)}/>
      <div className="AdminTable" style={{width: '100%'}}>
        <MUIDataTable
            title={
              <Grid container flexDirection={'row'}>
                <Grid item>
                  <FormControlLabel control={
                    <Checkbox
                      edge="start"
                      checked={isCheckAll}
                      disableRipple
                      onChange={(event: any) =>  setIsCheckAll(event.target.checked)}
                      disabled={props.isReadOnly || loading || !allFinished}
                      indeterminate={selectedEntities.length !== allIds.length && selectedEntities.length !== 0}
                    />
                  }
                  label={`Select All (${selectedEntities.length}/${allIds.length})`} sx={{color:'#000'}} />
                </Grid>
              </Grid>
            }
            data={uploadData}
            columns={tableColumns}
            options={{
              serverSide: true,
              page: pagination.page,
              count: totalCount,
              rowsPerPage: pagination.rowsPerPage,
              rowsPerPageOptions: rowsPerPageOptions,
              sortOrder: pagination.sortOrder as MUISortOptions,
              jumpToPage: true,
              onRowClick: null,
              onTableChange: (action: string, tableState: any) => onTableChangeState(action, tableState),
              customSearchRender: debounceSearchRender(500),
              selectableRows: selectableRowsMode,
              tableBodyHeight: `${tableHeight}px`,
              tableBodyMaxHeight: `${tableHeight}px`,
              textLabels: {
                body: {
                  noMatch: loading ?
                    <Loading/> :
                    'Sorry, there is no matching data to display',
                },
              },
              onSearchChange: (searchText: string) => {
                handleSearchOnChange(searchText)
              },
              customFilterDialogFooter: (currentFilterList, applyNewFilters) => {
                return (
                  <div style={{marginTop: '40px'}}>
                    <Button variant="contained" onClick={() => handleFilterChange(applyNewFilters)}>Apply Filters</Button>
                  </div>
                );
              },
              onFilterChange: (column, filterList, type) => {
                var newFilters = () => (filterList)
                handleFilterChange(newFilters)
              },
              searchText: currentFilters.search_text,
              searchOpen: (currentFilters.search_text != null && currentFilters.search_text.length > 0),
              filter: true,
              filterType: 'multiselect',
              confirmFilters: true,
              rowsSelected: selectedEntitiesInPage,
              selectToolbarPlacement: 'none',
              selectableRowsHeader: false,
              onRowSelectionChange: (currentRowsSelected, allRowsSelected, rowsSelected) => {
                if (currentRowsSelected.length > 1) {
                  // select all
                  setSelectedEntities([...allIds])
                  let _inPage = uploadData.map((a, index) => index)
                  setSelectedEntitiesInPage(_inPage)
                } else if (currentRowsSelected.length === 1) {
                  let _item = uploadData[currentRowsSelected[0]['index']]
                  // check/uncheck single
                  if (rowsSelected.indexOf(currentRowsSelected[0]['index']) > -1) {
                    // selected
                    setSelectedEntities(
                      [...selectedEntities, _item['id']]
                    )
                    setSelectedEntitiesInPage(
                      [...selectedEntitiesInPage, currentRowsSelected[0]['index']]
                    )
                  } else {
                    // deselected
                    let _entities = [...selectedEntities]
                    _entities = _entities.filter(a => a !== _item['id'])
                    setSelectedEntities(_entities)
                    let _entitiesIndex = selectedEntitiesInPage.filter(a => a !== currentRowsSelected[0]['index'])
                    setSelectedEntitiesInPage(_entitiesIndex)
                  }
                } else if (currentRowsSelected.length === 0) {
                  setSelectedEntities([])
                  setSelectedEntitiesInPage([])
                }
              },
              isRowSelectable: (dataIndex: number, selectedRows: any) => {
                return canRowBeSelected(dataIndex, uploadData[dataIndex])
              }
            }}
            components={{
              icons: {
                FilterIcon
              }
            }}
          />
        </div>
        <div className="button-container" style={{marginLeft:0, width: '100%'}}>
          <Grid container direction='row' justifyContent='space-between'>
            <Grid item>
              <LoadingButton loading={props.isUpdatingStep} loadingPosition="start" startIcon={<div style={{width: 0}}/>} disabled={!allFinished} onClick={() => props.onBackClicked()} variant="outlined">
                Back
              </LoadingButton>
            </Grid>
            { !props.isReadOnly && (
              <Grid item sx={{minWidth: '200px'}}>
                <Grid container flexDirection={'column'}>
                  <Grid item>
                    <p className="compact">Job summary: {jobSummaryText}.</p>
                    <p className="compact">Note: you can safely disconnect your computer while processing and return later to view progress</p>
                  </Grid>
                  <Grid item>
                    <LinearProgressWithLabel value={jobSummaryProgress} />
                  </Grid>
                </Grid>
              </Grid>
            )}
            <Grid item>
              { !props.isReadOnly && (
                <Button variant="contained"
                    disabled={loading || (selectedEntities.length == 0)}
                    onClick={handleImportClick}
                >Import</Button>
              )}
              { props.isReadOnly && uploadData.length > 0 && (
                <Button variant="contained"
                  disabled={loading}
                  onClick={() => navigate(`${ReviewListRoute.path}?upload=${props.uploadSession}`)}
                >Go to Review</Button>
              )}
            </Grid>
          </Grid>

        </div>
    </div>
    </Scrollable>
  )
}
