import React, {Fragment, useCallback, useEffect, useRef, useState} from "react";
import {useNavigate, useSearchParams} from "react-router-dom";

import Button from '@mui/material/Button';
import FilterAlt from "@mui/icons-material/FilterAlt";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import axios from "axios";
import toLower from "lodash/toLower";

import Loading from "../../components/Loading";
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import ResizeTableEvent from "../../components/ResizeTableEvent";
import {RootState} from "../../app/store";
import {TABLE_OFFSET_HEIGHT} from "../../components/List";
import {getDefaultFilter, ReviewFilterInterface} from "./Filter"
import {modules} from "../../modules";
import {setModule} from "../../reducers/module";
import {
  setSelectedReviews,
  addSelectedReview,
  removeSelectedReview,
  resetSelectedReviews,
  updateRowsSelectedInPage
} from "../../reducers/reviewAction";
import {useAppDispatch, useAppSelector} from '../../app/hooks';
import { reviewTableRowInterface } from "../../models/review";
import {
  setAvailableFilters,
  setCurrentFilters as setInitialFilters
} from "../../reducers/reviewTable";
import Popover from "@mui/material/Popover";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import Checkbox from '@mui/material/Checkbox';
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import StatusLoadingDialog from '../../components/StatusLoadingDialog';


const checkBoxOutlinedicon = <CheckBoxOutlineBlankIcon fontSize="small" />;
const checkBoxCheckedIcon = <CheckBoxIcon fontSize="small" />;

const USER_COLUMNS = [
  'id',
  'level_0_entity',
  'upload',
  'dataset',
  'start_date',
  'revision',
  'status',
  'submitted_by',
  'module',
  'is_comparison_ready'
]

const COLUMN_NAME_LABEL = {
  'upload': 'Upload',
  'dataset': 'Dataset'
}

const FILTER_VALUES_API_URL = '/api/review-filter/values/'
const VIEW_LIST_URL = '/api/review-list/'
const SELECT_ALL_LIST_URL = '/api/review-list-select-all/'
const FilterIcon: any = FilterAlt

function ViewPopover(props: any) {
  if (props.view === null) {
    return null
  }
  return (
    <Grid container flexDirection={'column'} sx={{p: 2}}>
      <Grid item>
        <Grid container flexDirection={'row'} justifyContent={'space-between'} spacing={2}>
          <Grid item>
            <Typography sx={{pb: 1}}>Logs:</Typography>
          </Grid>
        </Grid>
      </Grid>
      <Grid item>
        <Grid item>
          <Button
            variant={'outlined'}
            onClick={() => window.open(`/api/logs/entity_upload/${props.review.id}`, '_blank')}
          >
            Logs
          </Button>
        </Grid>
      </Grid>
    </Grid>
  )
}

export default function ReviewList() {
  const initialColumns = useAppSelector((state: RootState) => state.reviewTable.currentColumns)
  const initialFilters = useAppSelector((state: RootState) => state.reviewTable.currentFilters)
  const availableFilters = useAppSelector((state: RootState) => state.reviewTable.availableFilters)
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<any[]>([])
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isBatchReview = useAppSelector((state: RootState) => state.reviewAction.isBatchReview)
  const isBatchReviewAvailable = useAppSelector((state: RootState) => state.reviewAction.isBatchReviewAvailable)
  const pendingReviews = useAppSelector((state: RootState) => state.reviewAction.pendingReviews)
  const reviewUpdatedAt = useAppSelector((state: RootState) => state.reviewAction.updatedAt)
  const [anchorEl, setAnchorEl] = React.useState<HTMLButtonElement | null>(null);
  const [selectedReview, setSelectedReview] = useState<any>(null)

  const [columns, setColumns] = useState<any>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
  const [filterValues, setFilterValues] = useState<ReviewFilterInterface>(availableFilters)
  const [currentFilters, setCurrentFilters] = useState<ReviewFilterInterface>(initialFilters)
  const axiosSource = useRef(null)
  const newCancelToken = useCallback(() => {
    axiosSource.current = axios.CancelToken.source();
    return axiosSource.current.token;
  }, [])
  const ref = useRef(null)
  const [tableHeight, setTableHeight] = useState(0)
  const [hasProcessingReview, setHasProcessingReview] = useState(false)
  const rowsSelectedInPage = useAppSelector((state: RootState) => state.reviewAction.rowsSelectedInPage)
  let selectableRowsMode: any = isBatchReview ? 'multiple' : 'none'
  const [statusDialogOpen, setStatusDialogOpen] = useState<boolean>(false)
  const [statusDialogTitle, setStatusDialogTitle] = useState<string>('Selecting all uploads')
  const [statusDialogDescription, setStatusDialogDescription] = useState<string>('Fetching all uploads that are ready for review...')

  const fetchFilterValues = async () => {
    let filters = []
    filters.push(axios.get(`${FILTER_VALUES_API_URL}upload/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}dataset/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}revision/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}status/`))
    let resultData = await Promise.all(filters)
    let filterVals = {
      'level_0_entity': [] as any,
      'upload': resultData[0].data,
      'dataset': resultData[1].data,
      'revision': resultData[2].data,
      'status': resultData[3].data,
      'search_text': ''
    }
    setFilterValues(filterVals)
    dispatch(setAvailableFilters(JSON.stringify(filterVals)))
    return filterVals
  }

  const fetchReviewList = () => {
    if (axiosSource.current) axiosSource.current.cancel()
    let cancelFetchToken = newCancelToken()
    if (!hasProcessingReview) {
      setLoading(true)
    }
    let sortBy = pagination.sortOrder.name ? pagination.sortOrder.name : ''
    let sortDirection = pagination.sortOrder.direction ? pagination.sortOrder.direction : ''
    const url = `${VIEW_LIST_URL}?` + `page=${pagination.page + 1}&page_size=${pagination.rowsPerPage}` +
      `&sort_by=${sortBy}&sort_direction=${sortDirection}`
    axios.post(
      url,
      currentFilters,
      {
        cancelToken: cancelFetchToken
      }
    ).then((response) => {
      setLoading(false)
      let _data = response.data.results as reviewTableRowInterface[]
      let _hasProcessingReview = false
      for (let i=0;i<_data.length;++i) {
        if (_data[i].status === 'Processing') {
          _hasProcessingReview = true
          break;
        }
      }
      setHasProcessingReview(_hasProcessingReview)
      setData(_data)
      setTotalCount(response.data.count)
      dispatch(updateRowsSelectedInPage(_data))
    }).catch(error => {
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

  const fetchSelectAllReviewList = () => {
    const url = `${SELECT_ALL_LIST_URL}`
    setStatusDialogOpen(true)
    axios.post(
      url,
      currentFilters
    ).then((response) => {
      setStatusDialogOpen(false)
      dispatch(setSelectedReviews([response.data, data]))
    }).catch(error => {
      console.log(error)
      setStatusDialogOpen(false)
      if (error.response) {
        if (error.response.status == 403) {
          // TODO: use better way to handle 403
          navigate('/invalid_permission')
        }
      }
    })
  }

  const getExistingFilterValue = (colName: string): string[] => {
    let values: string[] = []
    switch (colName) {
      case 'upload':
        values = currentFilters.upload
        break;
      case 'dataset':
        values = currentFilters.dataset
        break;
      case 'revision':
        values = currentFilters.revision
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
      if (filterValues.status.length > 0) {
        filterVals = filterValues
      } else {
        filterVals = await fetchFilterValues()
      }
      const getLabel = (columnName: string) : string => {
        if (columnName === 'upload') {
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
        if (['upload', 'revision', 'dataset', 'status'].includes(columnName)) {
          // set filter values in dropdown
          _options.options.filterOptions = {
            names: filterVals[columnName]
          }
          _options.options.filterList = getExistingFilterValue(columnName)
          _options.options.filter = true
        } else {
          _options.options.filter = false
        }
        if (columnName === 'status') {
          _options.options.filterType = 'dropdown'
          _options.options.sort = false
        } else if (columnName === 'upload' || columnName === 'dataset') {
          _options.options.filterType = 'custom'
          _options.options.filterOptions = {
            names: filterVals[columnName],
            fullWidth: true,
            logic(val:any, filters:any) {
              return false
            },
            display: (filterList: any, onChange: any, index: any, column: any) => (
              <div>
                <Autocomplete
                  multiple
                  id={`checkboxes-id-filter-${columnName}`}
                  options={filterVals[columnName]}
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
                    <TextField {...params} label={COLUMN_NAME_LABEL[columnName]} variant="standard" />
                  )}
                />
              </div>
            )
          }
        } else if (columnName === 'start_date') {
          _options.options.customBodyRender = (value: string) => {
              return new Date(value).toDateString()
          }
        } else if (columnName === 'level_0_entity') {
          _options.options.customBodyRender = (value: any, tableMeta: any, updateValue: any) => {
            if (isBatchReview) {
              return value
            }
            let rowData = tableMeta.rowData
            const handleClick = (e: any) => {
                e.preventDefault()
                handleRowClick(rowData)
            };
            return (
                <a href='#' onClick={handleClick}>{`${rowData[1]}`}</a>
            )
          }
        } else if (columnName === 'is_comparison_ready') {
          _options.options.filter = false
          _options.options.display = false
          _options.options.viewColumns = false
          _options.options.searchable = false
          _options.options.print = false
          _options.options.sort = false
        }
        return _options
      })
      _columns.push({
        name: '',
        options: {
          customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
            let rowData = tableMeta.rowData
            return (
              <div className="TableActionContent">
                <IconButton
                  aria-label='More Info'
                  title='More Info'
                  key={0}
                  disabled={false}
                  color='primary'
                  onClick={(event: React.MouseEvent<HTMLButtonElement>) => {
                    event.stopPropagation();
                    let obj: any = {}
                    USER_COLUMNS.forEach((element, index) => {
                      obj[element] = rowData[index];
                    });
                    setSelectedReview(obj)
                    setAnchorEl(event.currentTarget);
                  }}
                  className=''
                >
                  <MoreVertIcon/>
                </IconButton>
              </div>
            )
          },
          filter: false,
          viewColumns: false,
          print: false,
          searchable: false,
          empty: true,
          sort: false
        }
      })
      setColumns(_columns)
    }
    fetchFilterValuesData()
  }, [pagination, currentFilters, isBatchReview])

  useEffect(() => {
    fetchReviewList()
  }, [pagination, currentFilters])

  useEffect(() => {
    // reset selection if filter is changed
    dispatch(resetSelectedReviews())
  }, [currentFilters])

  useEffect(() => {
    if (data.length > 0 && hasProcessingReview) {
      const interval = setInterval(() => {
        fetchReviewList()
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [data, hasProcessingReview])


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
    let filterList = applyFilters()
    let filter = getDefaultFilter()
    type Column = {
      name: string,
      label: string,
      options: any
    }
    for (let idx in filterList) {
      let col: Column = columns[idx]
      if (!col.options.filter)
        continue
      if (filterList[idx] && filterList[idx].length) {
        const key = col.name as string
        filter[key as keyof ReviewFilterInterface] = filterList[idx]
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

  const handleCloseMoreInfo = () => {
    setAnchorEl(null);
    setSelectedReview(null)
  };

  const open = Boolean(anchorEl);
  const id = open ? 'view-popover' : undefined;

  useEffect(() => {
    let upload
    try {
      upload = searchParams.get('upload') ? [searchParams.get('upload')] : []
    } catch (error: any) {
    }
    if (upload) {
      setCurrentFilters({...currentFilters, 'upload': upload})
      dispatch(setInitialFilters(JSON.stringify({...currentFilters, 'upload': upload})))
    }
  }, [searchParams])

  useEffect(() => {
    if (reviewUpdatedAt) {
      fetchReviewList()
    }
  }, [reviewUpdatedAt])

  const canRowBeSelected = useCallback((dataIndex: number, rowData: any) => {
    if (!isBatchReviewAvailable)
      return false
    return !pendingReviews.includes(rowData['id']) && rowData['is_comparison_ready'] && rowData['status'] === 'Ready for Review'
  }, [isBatchReviewAvailable, pendingReviews])

  const handleRowClick = (rowData: string[]) => {
    if (isBatchReview) return
    let moduleName = toLower(rowData[8]).replace(' ', '_')
    if (!moduleName) {
      moduleName = modules[0]
    }
    dispatch(setModule(moduleName))
    // Go to review page
    navigate(`/${moduleName}/review_detail?id=${rowData[0]}`)
  }

  return (
    <div className="AdminContentMain review-list main-data-list" ref={ref}>
    <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                      onResize={(clientHeight: number) => setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)}/>
    {
      loading ?
        <Loading/> :
          <Fragment>
            <StatusLoadingDialog open={statusDialogOpen} title={statusDialogTitle} description={statusDialogDescription} />
            <div className='AdminList'>
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
                    isRowSelectable: (dataIndex: number, selectedRows: any) => {
                      let _res = canRowBeSelected(dataIndex, data[dataIndex])
                      return _res
                    },
                    onRowSelectionChange: (currentRowsSelected, allRowsSelected, rowsSelected) => {
                      if (currentRowsSelected.length > 1) {
                        // select all
                        // fetch available review id using current filter
                        fetchSelectAllReviewList()
                      } else if (currentRowsSelected.length === 1) {
                        let _item = data[currentRowsSelected[0]['index']]
                        // check/uncheck single
                        if (rowsSelected.indexOf(currentRowsSelected[0]['index']) > -1) {
                          // selected
                          dispatch(addSelectedReview(_item['id']))
                        } else {
                          // deselected
                          dispatch(removeSelectedReview(_item['id']))
                        }
                      } else if (currentRowsSelected.length === 0) {
                        // deselect all
                        dispatch(resetSelectedReviews())
                      }
                    },
                    onRowClick: null,
                    onTableChange: (action: string, tableState: any) => onTableChangeState(action, tableState),
                    customSearchRender: debounceSearchRender(500),
                    selectableRows: selectableRowsMode,
                    selectToolbarPlacement: 'none',
                    rowsSelected: rowsSelectedInPage,
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
                    confirmFilters: true,
                    tableBodyHeight: `${tableHeight}px`,
                    tableBodyMaxHeight: `${tableHeight}px`,
                  }}
                  components={{
                    icons: {
                      FilterIcon
                    }
                  }}
                />
              </div>
            </div>
          </Fragment>
    }
      <Popover
          id={id}
          open={open}
          anchorEl={anchorEl}
          onClose={handleCloseMoreInfo}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'left',
          }}
        >
          <ViewPopover review={selectedReview}/>
        </Popover>
    </div>
  )
}
