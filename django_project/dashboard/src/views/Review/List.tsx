import React, {useEffect, useState} from "react";
import {useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import {RootState} from "../../app/store";
import { useAppSelector, useAppDispatch } from '../../app/hooks';
import {setModule} from "../../reducers/module";
import {modules} from "../../modules";
import List from "../../components/List";
import Loading from "../../components/Loading";
import {setSelectedReviews} from "../../reducers/reviewAction";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import {getDefaultFilter, ReviewFilterInterface} from "./Filter"
import {
  setAvailableFilters,
  setCurrentColumns as setInitialColumns,
  setCurrentFilters as setInitialFilters
} from "../../reducers/reviewTable";
import {RootState} from "../../app/store";


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


export interface ReviewData {
  id: number,
  revision: number,
  module: string
}

const FILTER_VALUES_API_URL = '/api/review-filter/values/'


export default function ReviewList () {
  const initialColumns = useAppSelector((state: RootState) => state.reviewTable.currentColumns)
  const initialFilters = useAppSelector((state: RootState) => state.reviewTable.currentFilters)
  const availableFilters = useAppSelector((state: RootState) => state.reviewTable.availableFilters)
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<any[]>([])
  const [customOptions, setCustomOptions] = useState<any>({})
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isBatchReviewAvailable = useAppSelector((state: RootState) => state.reviewAction.isBatchReviewAvailable)
  const isBatchReview = useAppSelector((state: RootState) => state.reviewAction.isBatchReview)
  const pendingReviews = useAppSelector((state: RootState) => state.reviewAction.pendingReviews)
  const reviewUpdatedAt = useAppSelector((state: RootState) => state.reviewAction.updatedAt)

  const [columns, setColumns] = useState<any>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
  const [filterValues, setFilterValues] = useState<ReviewFilterInterface>(availableFilters)
  const [currentFilters, setCurrentFilters] = useState<ReviewFilterInterface>(initialFilters)

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
        // update filter values if searchParams has upload filter
        // let _upload = searchParams.get('upload')
        // if (_upload) {
        //   setCustomOptions({
        //     'upload': {
        //       'filterList': [_upload]
        //     }
        //   })
          setLoading(false)
          setData(response.data.results as ReviewFilterInterface[])
          setTotalCount(response.data.count)
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
      if (filterValues.mode.length > 0  ) {
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
            sort: !['tags', 'permissions', 'status', 'mode'].includes(columnName)
          }
        }
        if (columnName == 'tags') {
          _options['options']['filterType'] = 'multiselect'
          _options['options']['filter'] = true
          _options['options']['customBodyRender'] = (value: any, tableMeta: any) => {
            return <div>
              {value.map((tag: any, index: number) => <Chip key={index} label={tag}/>)}
            </div>
          }
        }
        if (['tags', 'mode', 'dataset', 'is_default', 'min_privacy', 'max_privacy'].includes(columnName)) {
          // set filter values in dropdown
          _options.options.filterOptions = {
            names: filterVals[columnName]
          }
          _options.options.filter = true
        } else {
          _options.options.filter = false
        }
        if (['tags', 'mode', 'dataset', 'is_default', 'min_privacy', 'max_privacy'].includes(columnName)) {
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
                    setSelectedView(obj)
                    setAnchorEl(event.currentTarget);
                  }}
                  className=''
                >
                  <MoreVertIcon/>
                </IconButton>

                <IconButton
                  aria-label='Delete'
                  title='Delete'
                  key={2}
                  disabled={!rowData[12].includes('Own') || rowData[6] === 'Yes'}
                  color='error'
                  onClick={() => {
                    setSelectedView(rowData)
                    setConfirmationText(
                      `Are you sure you want to delete ${rowData[1]}?`)
                    setConfirmationOpen(true)
                  }}
                  className=''
                >
                  <DeleteIcon/>
                </IconButton>
              </div>
            )
          },
          filter: false
        }
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
        <List pageName={"Review"}
          listUrl={""}
          initData={data}
          selectionChanged={selectionChanged}
          onRowClick={handleRowClick}
          actionData={[]}
          excludedColumns={['module', 'is_comparison_ready']}
          isRowSelectable={isBatchReview}
          canRowBeSelected={canRowBeSelected}
          customOptions={customOptions}
          options={{
            'selectToolbarPlacement': 'none'
          }}
        />
      </div>
  )
}
