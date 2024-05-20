import React, {useState, useEffect, useRef, useCallback} from "react";
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
import FilterAlt from "@mui/icons-material/FilterAlt";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import Checkbox from '@mui/material/Checkbox';
import TextField from '@mui/material/TextField';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import Autocomplete from '@mui/material/Autocomplete';
import Scrollable from '../../components/Scrollable';
import {TABLE_OFFSET_HEIGHT} from "../../components/List";
import LinearProgressWithLabel from "../../components/LinearProgressWithLabel";
import { BatchEntityEditInterface } from "../../models/upload";
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import ResizeTableEvent from "../../components/ResizeTableEvent";

interface Step2Interface {
    batchEdit: BatchEntityEditInterface,
    onStartToImportClicked: () => void,
    onBackClicked?: () => void,
    onClickNext?: () => void,
}

const checkBoxOutlinedicon = <CheckBoxOutlineBlankIcon fontSize="small" />;
const checkBoxCheckedIcon = <CheckBoxIcon fontSize="small" />;
const FINAL_STATUS_LIST = ['DONE', 'ERROR', 'CANCELLED']
const LOAD_RESULT_BATCH_ENTITY_EDIT_URL = '/api/batch-entity-edit/result/'
interface Step2FilterInterface {
    status: string[],
    search_text: string,
    country: string[],
    level: string[]
}
const getDefaultFilter = (): Step2FilterInterface => {
    return {
        status: [],
        search_text: '',
        country: [],
        level: []
    }
}
const USER_COLUMNS = [
    'id',
    'country',
    'level',
    'ucode',
    'default_name',
    'default_code',
    'status',
    'errors'
]
const STATUS_LIST = ['OK', 'SUCCESS', 'ERROR']
const FilterIcon: any = FilterAlt
const MAX_ITEM_IN_FILTER_CHIP = 5

export default function Step2(props: Step2Interface) {
    const [loading, setLoading] = useState(true)
    const [alertTitle, setAlertTitle] = useState('')
    const [alertMessage, setAlertMessage] = useState('')
    const [alertSeverity, setAlertSeverity] = useState<AlertColor>('success')
    const [resultData, setResultData] = useState<any[]>([])
    const [tableColumns, setTableColumns] = useState<any>([])
    const [totalCount, setTotalCount] = useState<number>(0)
    const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
    const [currentFilters, setCurrentFilters] = useState<Step2FilterInterface>(getDefaultFilter())
    const axiosSource = useRef(null)
    const newCancelToken = useCallback(() => {
        axiosSource.current = axios.CancelToken.source();
        return axiosSource.current.token;
    }, [])
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)

    const fetchResultData = () => {
        if (axiosSource.current) axiosSource.current.cancel()
        let cancelFetchToken = newCancelToken()
        let _preview = props.batchEdit.status === 'PENDING' && props.batchEdit.has_preview
        let _url = LOAD_RESULT_BATCH_ENTITY_EDIT_URL + `?batch_edit_id=${props.batchEdit.id}&preview=${_preview ? 'true':'false'}&page=${pagination.page + 1}&page_size=${pagination.rowsPerPage}`
        if (currentFilters.country.length > 0) {
            _url = _url + `&country=${currentFilters.country.join(',')}`
        }
        if (currentFilters.level.length > 0) {
            _url = _url + `&level=${currentFilters.level.join(',')}`
        }
        if (currentFilters.status.length > 0) {
            _url = _url + `&status=${currentFilters.status.join(',')}`
        }
        if (currentFilters.search_text) {
            _url = _url + `&search_text=${currentFilters.search_text}`
        }
        axios.get(
            _url,
            {
                cancelToken: cancelFetchToken
            }
        ).then(response => {
            if (tableColumns.length === 0) {
                setTableColumns(generateTableColumns(props.batchEdit, response.data['countries'], ["0", "1", "2", "3", "4", "5"]))
            } else {
                setTableColumns(updateFilterList())
            }
            setResultData(response.data['results'])
            setTotalCount(response.data['count'])
            setLoading(false)
        }).catch(error => {
            setLoading(false)
            if (!axios.isCancel(error)) {
                console.log(error)
                let _message = 'Unable to fetch batch edit result!'
                if (error.response) {
                    if ('detail' in error.response.data) {
                        _message = error.response.data.detail
                    }
                }
                alert(_message)
            }            
        })
    }

    const getExistingFilterValue = (col_name: string):string[] =>  {
        let values:string[] = []
        switch (col_name) {
            case 'country':
                values = currentFilters.country
                break;
            case 'status':
              values = currentFilters.status
              break;
            case 'level':
                values = currentFilters.level
                break;
            default:
              break;
        }
        return values
      }

    const generateTableColumns = (batchEdit: BatchEntityEditInterface, countryList: string[], levelList: string[]) => {
        let _init_columns = []
        for (let i = 0; i < USER_COLUMNS.length; ++i) {
            _init_columns.push(USER_COLUMNS[i])
            if (USER_COLUMNS[i] === 'default_code') {
                // add new codes and names
                if (batchEdit.id_fields && batchEdit.id_fields.length > 0) {
                    for (let id_field of batchEdit.id_fields) {
                        _init_columns.push(id_field.field)
                    }
                }
                if (batchEdit.name_fields && batchEdit.name_fields.length > 0) {
                    for (let name_field of batchEdit.name_fields) {
                        _init_columns.push(name_field.field)
                    }
                }
            }
        }
        let _columns = _init_columns.map((columnName) => {
            let _options: any = {
                name: columnName,
                label: USER_COLUMNS.indexOf(columnName) > -1 ? columnName.charAt(0).toUpperCase() + columnName.slice(1).replaceAll('_', ' ') : columnName,
                options: {
                    display: columnName !== 'id',
                    sort: false,
                    filter: false,
                    searchable: false
                }
            }
            if (columnName === 'country' || columnName === 'level') {
                _options['options']['filter'] = true
                _options['options']['filterType'] = 'custom'
                _options['options']['filterList'] = getExistingFilterValue(columnName)
                let _filtervals = columnName === 'country' ? countryList : levelList
                _options['options']['filterOptions'] = {
                    fullWidth: true,
                    names: _filtervals,
                    logic(val:any, filters:any) {
                      return false
                    },
                    display: (filterList: any, onChange: any, index: any, column: any) => (
                        <div>
                            <Autocomplete
                                multiple
                                id={`checkboxes-id-filter-${columnName}`}
                                options={_filtervals}
                                disableCloseOnSelect
                                value={filterList[index]}
                                onChange={(event: any, newValue: any | null) => {
                                    filterList[index] = newValue
                                    onChange(filterList[index], index, column)
                                }}
                                getOptionLabel={(option) => `${option}`}
                                renderOption={(props, option, { selected }) => (
                                    <li {...props}>
                                    <Checkbox
                                        icon={checkBoxOutlinedicon}
                                        checkedIcon={checkBoxCheckedIcon}
                                        style={{ marginRight: 8 }}
                                        checked={selected}
                                    />
                                    {option}
                                    </li>
                                )}
                                renderInput={(params) => (
                                    <TextField {...params} label={_options['label']} variant="standard" />
                                )}
                            />
                        </div>
                    )
                }
                let _singleLabel = _options['label']
                let _pluralLabel = columnName === 'country' ? 'Countries': 'Levels'
                _options['options']['customFilterListOptions'] = {
                    render: (items:any) => {
                        let result:string[] = []
                        if (items.length === 1) {
                            result.push(`${_singleLabel}: ${items[0]}`)
                        } else if (items.length <= MAX_ITEM_IN_FILTER_CHIP) {
                            result.push(`${_pluralLabel}: ${items.join(', ')}`)
                        } else {
                            let _items = items.slice(0, MAX_ITEM_IN_FILTER_CHIP)
                            result.push(`${_pluralLabel}: ${_items.join(', ')}, and ${items.length - MAX_ITEM_IN_FILTER_CHIP} more`)
                        }                                    
                        return result
                    },
                    update: (filterList:any, filterPos:any, index:any) => {
                        filterList[index] = []
                        handleChipOnClear(columnName)
                        return filterList;
                    }
                }
            } else if (columnName === 'status') {
                _options['options']['filter'] = true
                _options['options']['filterList'] = getExistingFilterValue(columnName)
                _options['options']['filterOptions'] = {
                    fullWidth: true,
                    names: STATUS_LIST,
                }
                _options['options']['customBodyRender'] = (value: any, tableMeta: any, updateValue: any) => {
                    if (value === 'ERROR') {
                        return <span className="text-error">{value}</span>
                    }
                    return <span className="text-success">{value}</span>
                }
            }
            return _options
        })
        return _columns
    }

    const updateFilterList = () => {
        let _columns = [...tableColumns]
        for (let columnOptions of _columns) {
            let columnName = columnOptions['name']
            if (columnName === 'country' || columnName === 'level' || columnName === 'status') {
                columnOptions['options']['filterList'] = getExistingFilterValue(columnName)
            }
        }
        return _columns
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
    }, [props.batchEdit.status, currentFilters, pagination])

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

    const onTableInteraction = () => {
        setResultData([])
        if (axiosSource.current) {
          axiosSource.current.cancel()
        }
    }

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
            filter[key as keyof Step2FilterInterface] = filterList[idx]
          }
        }
        setCurrentFilters({...filter, 'search_text': currentFilters['search_text']})
    }
    
    const handleChipOnClear = (fieldName: string) => {
        let _currentFilters = {...currentFilters}
        if (fieldName === 'country') {
            setCurrentFilters({
                ..._currentFilters,
                country: []
            })
        } else if (fieldName === 'level') {
            setCurrentFilters({
                ..._currentFilters,
                level: []
            })
        }        
    }

    return (
        <Scrollable>
            <div className="Step3Container Step4Container Step2BatchEdit" ref={ref}>
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
                            <Grid item sx={{height: '100%'}}>
                                <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                                    onResize={(clientHeight: number) => {
                                        setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT - 40 - 148)
                                    }}/>
                                <div className="AdminTable" style={{width: '100%'}}>
                                { FINAL_STATUS_LIST.includes(props.batchEdit.status) || props.batchEdit.has_preview ? 
                                    <MUIDataTable
                                        title=''
                                        data={resultData}
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
                                            selectableRows: 'none',
                                            tableBodyHeight: `${tableHeight}px`,
                                            tableBodyMaxHeight: `${tableHeight}px`,
                                            textLabels: {
                                                body: {
                                                    noMatch: 'Sorry, there is no matching data to display',
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
                                            selectToolbarPlacement: 'none',
                                            selectableRowsHeader: false,
                                        }}
                                        components={{
                                            icons: {
                                                FilterIcon
                                            }
                                        }}
                                    />
                                    : null
                                }
                                </div>
                            </Grid>
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
