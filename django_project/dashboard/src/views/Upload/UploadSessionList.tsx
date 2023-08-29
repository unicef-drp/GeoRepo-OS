import React, {Fragment, useCallback, useEffect, useRef, useState} from "react";
import List, {ActionDataInterface, TABLE_OFFSET_HEIGHT} from "../../components/List";
import toLower from "lodash/toLower";
import cloneDeep from "lodash/cloneDeep";
import {useNavigate} from "react-router-dom";
import DeleteIcon from "@mui/icons-material/Delete";
import FactCheckIcon from '@mui/icons-material/FactCheck';
import IconButton from '@mui/material/IconButton';
import {setModule} from "../../reducers/module";
import {modules} from "../../modules";
import {ReviewListRoute} from "../routes";
import {fetchData, postData} from "../../utils/Requests";
import Loading from "../../components/Loading";
import AlertDialog from '../../components/AlertDialog'
import ResizeTableEvent from "../../components/ResizeTableEvent";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import {Button, Chip} from "@mui/material";
import FilterAlt from "@mui/icons-material/FilterAlt";
import {useAppDispatch, useAppSelector} from '../../app/hooks';
import {
  setAvailableFilters,
  setCurrentFilters as setInitialFilters
} from "../../reducers/uploadTable";
import {RootState} from "../../app/store";
import axios from "axios";
import {getDefaultFilter, UploadFilterInterface} from "./UploadFilter";

const READ_ONLY_SESSION_STATUSES = ['Canceled', 'Done', 'Reviewing']
const DELETE_UPLOAD_SESSION_URL = '/api/delete-upload-session'

interface UploadSessionInterface {
  id: number,
  level_0_entity: string,
  dataset: string,
  type: string,
  upload_date: Date,
  uploaded_by: string,
  status: string
}

const USER_COLUMNS = [
  'id',
  'level_0_entity',
  'dataset',
  'type',
  'uploaded_by',
  'status'
]

const FILTER_VALUES_API_URL = '/api/upload-session-filter/values/'
const UPLOAD_SESSION_LIST_URL = '/api/upload-sessions/'

export default function UploadSessionList() {
  const dispatch = useAppDispatch()
  const initialColumns = useAppSelector((state: RootState) => state.uploadTable.currentColumns)
  const initialFilters = useAppSelector((state: RootState) => state.uploadTable.currentFilters)
  const availableFilters = useAppSelector((state: RootState) => state.uploadTable.availableFilters)
  const [selectedSession, setSelectedSession] = useState<any>(null)
  const [confirmationOpen, setConfirmationOpen] = useState<boolean>(false)
  const [confirmationText, setConfirmationText] = useState<string>('')
  const [deleteButtonDisabled, setDeleteButtonDisabled] = useState<boolean>(false)
  const navigate = useNavigate()
  
  const [loading, setLoading] = useState<boolean>(true)
  const [columns, setColumns] = useState([])
  const [allData, setAllData] = useState<any[]>()
  const [data, setData] = useState<UploadSessionInterface[]>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
  const [filterValues, setFilterValues] = useState<UploadFilterInterface>(availableFilters)
  const [currentFilters, setCurrentFilters] = useState<UploadFilterInterface>(initialFilters)
  const axiosSource = useRef(null)
  const newCancelToken = useCallback(() => {
    axiosSource.current = axios.CancelToken.source();
    return axiosSource.current.token;
  }, [])
  const ref = useRef(null)
  const [tableHeight, setTableHeight] = useState(0)

  const FilterIcon: any = FilterAlt

  const fetchFilterValues = async () => {
    let filters = []
    filters.push(axios.get(`${FILTER_VALUES_API_URL}id/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}level_0_entity/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}dataset/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}type/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}uploaded_by/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}status/`))
    let resultData = await Promise.all(filters)
    let filterVals = {
      'id': resultData[0].data,
      'level_0_entity': resultData[1].data,
      'dataset': resultData[2].data,
      'type': resultData[3].data,
      'uploaded_by': resultData[4].data,
      'status': resultData[5].data,
      'search_text': ''
    }
    setFilterValues(filterVals)
    dispatch(setAvailableFilters(JSON.stringify(filterVals)))
    return filterVals
  }
  
  const fetchUploadList = () => {
    if (axiosSource.current) axiosSource.current.cancel()
    let cancelFetchToken = newCancelToken()
    setLoading(true)
    let _additional_filters = ''
    let sortBy = pagination.sortOrder.name ? pagination.sortOrder.name : ''
    let sortDirection = pagination.sortOrder.direction ? pagination.sortOrder.direction : ''

    axios.post(`${UPLOAD_SESSION_LIST_URL}?` + `page=${pagination.page + 1}&page_size=${pagination.rowsPerPage}` +
      `&sort_by=${sortBy}&sort_direction=${sortDirection}` +
      `${_additional_filters}`,
      currentFilters,
      {
        cancelToken: cancelFetchToken
      }).then(
      response => {
        setAllData(cloneDeep(response.data.results))
        let _sessionData = response.data.results.map((responseData: any) => {
          delete responseData['form']
          return responseData
        })
        setLoading(false)
        setData(_sessionData as UploadSessionInterface[])
        setTotalCount(response.data.count)
      }
    ).catch(error => {
      if (!axios.isCancel(error)) {
        console.log(error)
        setLoading(false)
        if (error.response) {
          if (error.response.status == 403) {
            // TODO: use better way to handle 403
            navigate('/invalid_permission')
          }
        }
      }
    })
  }
  
  const getExistingFilterValue = (colName: string): string[] => {
    let values: string[] = []
    switch (colName) {
      case 'id':
        values = currentFilters.id
        break;
      case 'level_0_entity':
        values = currentFilters.level_0_entity
        break;
      case 'dataset':
        values = currentFilters.dataset
        break;
      case 'type':
        values = currentFilters.type
        break;
      case 'uploaded_by':
        values = currentFilters.uploaded_by
        break;
      case 'status':
        values = currentFilters.status
        break;
      default:
        break;
    }
    return values
  }

  useEffect(() => {
    const fetchFilterValuesData = async () => {
      let filterVals: any = {}
      if (filterValues.status.length > 0  ) {
        filterVals = filterValues
      } else {
        filterVals = await fetchFilterValues()
      }

      const getLabel = (columnName: string) : string => {
        if (columnName === 'id') {
          return 'Upload ID'
        }
        return columnName.charAt(0).toUpperCase() + columnName.slice(1).replaceAll('_', ' ')
      }

      let _init_columns = USER_COLUMNS
      let _columns = _init_columns.map((columnName) => {
        let _options: any = {
          name: columnName,
          label: getLabel(columnName),
          options: {
            display: initialColumns.includes(columnName),
            sort: true
          }
        }
        if (columnName != 'upload_date') {
          // set filter values in dropdown
          _options.options.filterOptions = {
            names: filterVals[columnName]
          }
          _options.options.filter = true
        } else {
          _options.options.filter = false
        }
        if (columnName != 'upload_date') {
          // set existing filter values
          _options.options.filterList = getExistingFilterValue(columnName)
        }
        return _options
      })
      _columns.push({
        name: '',
        options: {
          customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
            let rowData = tableMeta.rowData
            const deleteLabel = () => {
              if (rowData[5] === 'Done') {
                return 'Cannot removed processed upload'
              } else if (rowData[5] === 'Processing') {
                return 'Cannot removed ongoing upload'
              }
              return 'Delete'
            }
            return (
              <div className="TableActionContent">
                <IconButton
                  aria-label={rowData[5] !== 'Reviewing' ? 'Review is not available' : 'Review'}
                  title={rowData[5] !== 'Reviewing' ? 'Review is not available' : 'Review'}
                  key={0}
                  disabled={rowData[5] !== 'Reviewing'}
                  color='primary'
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`${ReviewListRoute.path}?upload=${rowData[0]}`)
                  }}
                  className=''
                >
                  <FactCheckIcon />
                </IconButton>

                <IconButton
                  aria-label= {deleteLabel()}
                  title={deleteLabel()}
                  key={1}
                  disabled={['Done', 'Processing'].includes(rowData[5])}
                  color='error'
                  onClick={(e) => {
                    e.stopPropagation()
                    setSelectedSession(rowData)
                    setConfirmationText(
                      `Are you sure you want to delete Upload #${rowData[0]}?`)
                    setConfirmationOpen(true)
                  }}
                  className=''
                >
                  <DeleteIcon />
                </IconButton>
              </div>
            )
          },
          filter: false
        }
      })
      setColumns(_columns)
    }
    fetchFilterValuesData()
  }, [pagination, currentFilters])

  useEffect(() => {
    fetchUploadList()
  }, [pagination, filterValues, currentFilters])

  const onTableChangeState = (action: string, tableState: any) => {
    switch (action) {
      case 'changePage':
        setPagination({
          ...pagination,
          page: tableState.page
        })
        break;
      case 'sort':
        setPagination({
          ...pagination,
          page: 0,
          sortOrder: tableState.sortOrder
        })
        break;
      case 'changeRowsPerPage':
        setPagination({
          ...pagination,
          page: 0,
          rowsPerPage: tableState.rowsPerPage
        })
        break;
      default:
    }
  }

  const handleFilterSubmit = (applyFilters: any) => {
    type Column = {
      name: string,
      label: string,
      options: any
    }
    let filterList: string[][] = applyFilters()
    let filter = getDefaultFilter()

    for (let idx in filterList) {
      let col: Column = columns[idx]
      if (!col.options.filter)
        continue
      if (filterList[idx] && filterList[idx].length) {
        const key = col.name as string
        filter[key as keyof UploadFilterInterface] = filterList[idx] as any
      }
    }
    setCurrentFilters({...filter, 'search_text': currentFilters['search_text']})
    dispatch(setInitialFilters(JSON.stringify({...filter, 'search_text': currentFilters['search_text']})))
  }

  const handleSearchOnChange = (search_text: string) => {
    setPagination({
      ...pagination,
      page: 0,
      sortOrder: {}
    })
    setCurrentFilters({...currentFilters, 'search_text': search_text})
    dispatch(setInitialFilters(JSON.stringify({...currentFilters, 'search_text': search_text})))
  }

  const handleDeleteClick = () => {
    setDeleteButtonDisabled(true)
    postData(
      `${DELETE_UPLOAD_SESSION_URL}/${selectedSession[0]}`, {}
    ).then(
      response => {
        setDeleteButtonDisabled(false)
        fetchUploadList()
        setConfirmationOpen(false)
      }
    ).catch(error => {
      setDeleteButtonDisabled(false)
      alert('Error deleting upload session')
    })
  }

  const handleClose = () => {
    setConfirmationOpen(false)
  }

  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    const row = allData.find(sessionData => sessionData.id === rowData[0])
    let moduleName = toLower(row.type.replace(' ', '_'))
    if (!moduleName) {
      moduleName = modules[0]
    }
    dispatch(setModule(moduleName))
    navigate(`/${moduleName}/upload_wizard/${row.form}`)
  }

  return (
    <div className="AdminContentMain main-data-list">
      <AlertDialog open={confirmationOpen} alertClosed={handleClose}
          alertConfirmed={handleDeleteClick}
          alertLoading={deleteButtonDisabled}
          alertDialogTitle={'Delete upload session'}
          alertDialogDescription={confirmationText}
          confirmButtonText='Delete'
          confirmButtonProps={{color: 'error', autoFocus: true}}
      />
    {loading ? <Loading/> :
       <Fragment>
          <div className='AdminList' ref={ref}>
            <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                              onResize={(clientHeight: number) => setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)}/>
            <div className='AdminTable'>
              <MUIDataTable
                title=''
                data={data}
                columns={columns}
                options={{
                  serverSide: true,
                  page: pagination.page,
                  count: totalCount,
                  rowsPerPage: pagination.rowsPerPage,
                  rowsPerPageOptions: rowsPerPageOptions,
                  sortOrder: pagination.sortOrder as MUISortOptions,
                  jumpToPage: true,
                  onRowClick: (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
                    handleRowClick(rowData, rowMeta)
                  },
                  onTableChange: (action: string, tableState: any) => onTableChangeState(action, tableState),
                  customSearchRender: debounceSearchRender(500),
                  selectableRows: 'none',
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
                        <Button variant="contained" onClick={() => handleFilterSubmit(applyNewFilters)}>Apply
                          Filters</Button>
                      </div>
                    );
                  },
                  onFilterChange: (column, filterList, type) => {
                    var newFilters = () => (filterList)
                    handleFilterSubmit(newFilters)
                  },
                  searchText: currentFilters.search_text,
                  searchOpen: (currentFilters.search_text != null && currentFilters.search_text.length > 0),
                  filter: true,
                  filterType: 'multiselect',
                  confirmFilters: true
                }}
                components={{
                  icons: {
                    FilterIcon
                  }
                }}
              />
            </div>
          </div>
        </Fragment>}
    </div>
  )
}
