import React, {Fragment, useCallback, useEffect, useRef, useState} from "react";
import {useNavigate, useSearchParams} from "react-router-dom";

import {Button} from '@mui/material';
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
import {setSelectedReviews} from "../../reducers/reviewAction";
import {useAppDispatch, useAppSelector} from '../../app/hooks';
import {
  setAvailableFilters,
  setCurrentColumns as setInitialColumns,
  setCurrentFilters as setInitialFilters
} from "../../reducers/reviewTable";

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

interface reviewTableRowInterface {
  id: number,
  level_0_entity: string,
  upload: string,
  dataset: string,
  start_date: string,
  revision: number,
  status: string,
  submitted_by: string,
  module: string,
  is_comparison_ready: string
}

const FILTER_VALUES_API_URL = '/api/review-filter/values/'
const VIEW_LIST_URL = '/api/review-list/'
const FilterIcon: any = FilterAlt


export default function ReviewList() {
  const initialColumns = useAppSelector((state: RootState) => state.reviewTable.currentColumns)
  const initialFilters = useAppSelector((state: RootState) => state.reviewTable.currentFilters)
  const availableFilters = useAppSelector((state: RootState) => state.reviewTable.availableFilters)
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<any[]>([])
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isBatchReviewAvailable = useAppSelector((state: RootState) => state.reviewAction.isBatchReviewAvailable)
  const pendingReviews = useAppSelector((state: RootState) => state.reviewAction.pendingReviews)
  const reviewUpdatedAt = useAppSelector((state: RootState) => state.reviewAction.updatedAt)

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

  const fetchFilterValues = async () => {
    let filters = []
    filters.push(axios.get(`${FILTER_VALUES_API_URL}level_0_entity/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}upload/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}dataset/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}revision/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}status/`))
    let resultData = await Promise.all(filters)
    let filterVals = {
      'level_0_entity': resultData[0].data,
      'upload': resultData[1].data,
      'dataset': resultData[2].data,
      'revision': resultData[3].data,
      'status': resultData[4].data,
      'search_text': ''
    }
    setFilterValues(filterVals)
    dispatch(setAvailableFilters(JSON.stringify(filterVals)))
    return filterVals
  }

  const fetchReviewList = () => {
    if (axiosSource.current) axiosSource.current.cancel()
    let cancelFetchToken = newCancelToken()
    setLoading(true)
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
      setData(response.data.results as reviewTableRowInterface[])
      setTotalCount(response.data.count)
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

  const getExistingFilterValue = (colName: string): string[] => {
    let values: string[] = []
    switch (colName) {
      case 'level_0_entity':
        values = currentFilters.level_0_entity
        break;
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
      let _init_columns = USER_COLUMNS
      let _columns = _init_columns.map((columnName) => {
        let _options: any = {
          name: columnName,
          label: columnName.charAt(0).toUpperCase() + columnName.slice(1).replaceAll('_', ' '),
          options: {
            display: initialColumns.includes(columnName),
            sort: true
          }
        }
        if (['level_0_entity', 'upload', 'revision', 'dataset', 'status'].includes(columnName)) {
          // set filter values in dropdown
          _options.options.filterOptions = {
            names: filterVals[columnName]
          }
          _options.options.filterList = getExistingFilterValue(columnName)
          _options.options.filter = true
        } else {
          _options.options.filter = false
        }
        if (columnName == 'start_date') {
          _options.options.customBodyRender = (value: string) => {
              return new Date(value).toDateString()
          }
        }
        return _options
      })
      setColumns(_columns)
      dispatch(setInitialColumns(JSON.stringify(_columns.map)))
    }
    fetchFilterValuesData()
  }, [pagination, currentFilters])

  useEffect(() => {
    fetchReviewList()
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

  useEffect(() => {
    fetchReviewList()
  }, [searchParams])

  useEffect(() => {
    if (reviewUpdatedAt) {
      fetchReviewList()
    }
  }, [reviewUpdatedAt])

  const canRowBeSelected = (dataIndex: number, rowData: any) => {
    if (!isBatchReviewAvailable)
      return false
    return !pendingReviews.includes(rowData['id']) && rowData['is_comparison_ready']
  }

  const selectionChanged = (data: any) => {
    dispatch(setSelectedReviews(data))
  }

  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    console.log(rowData)
    let moduleName = toLower(rowData[8]).replace(' ', '_')
    if (!moduleName) {
      moduleName = modules[0]
    }
    dispatch(setModule(moduleName))
    // Go to review page
    navigate(`/${moduleName}/review_detail?id=${rowData[0]}`)
  }

  return (
    loading ?
      <div className={"loading-container"}><Loading/></div> :
      <div className="AdminContentMain review-list main-data-list">
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
                  isRowSelectable: (dataIndex: number, selectedRows: any) => {
                    return canRowBeSelected(dataIndex, data[dataIndex])
                  },
                  onRowSelectionChange: (currentRowsSelected, allRowsSelected, rowsSelected) => {
                    // @ts-ignore
                    const rowDataSelected = rowsSelected.map((index) => data[index]['id'])
                    selectionChanged(rowDataSelected)
                  },
                  onRowClick: (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
                    handleRowClick(rowData, rowMeta)
                  },
                  onTableChange: (action: string, tableState: any) => onTableChangeState(action, tableState),
                  customSearchRender: debounceSearchRender(500),
                  selectableRows: 'multiple',
                  selectToolbarPlacement: 'none',
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
        </Fragment>
      </div>
  )
}
