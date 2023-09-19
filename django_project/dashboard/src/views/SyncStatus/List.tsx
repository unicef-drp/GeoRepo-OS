import React, {Fragment, useCallback, useEffect, useRef, useState} from "react";
import {useNavigate, useSearchParams} from "react-router-dom";

import {Button} from '@mui/material';
import FilterAlt from "@mui/icons-material/FilterAlt";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import axios from "axios";

import Loading from "../../components/Loading";
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import ResizeTableEvent from "../../components/ResizeTableEvent";
import {RootState} from "../../app/store";
import {TABLE_OFFSET_HEIGHT} from "../../components/List";
import {getDefaultFilter, ViewSyncFilterInterface} from "./Filter"
import {setSelectedViews, toggleIsBatchAction} from "../../reducers/viewSyncAction";
import {useAppDispatch, useAppSelector} from '../../app/hooks';
import {setAvailableFilters, setCurrentFilters as setInitialFilters} from "../../reducers/viewSyncTable";
import Stack from '@mui/material/Stack';
import {postData} from "../../utils/Requests";
import AlertMessage from "../../components/AlertMessage";
import AlertDialog from "../../components/AlertDialog";
import {AddButton, CancelButton, ThemeButton} from "../../components/Elements/Buttons";
import GradingIcon from "@mui/icons-material/Grading";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";


export function ViewSyncActionButtons() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const isBatchActionAvailable = useAppSelector((state: RootState) => state.viewSyncAction.isBatchActionAvailable)
  const isBatchAction = useAppSelector((state: RootState) => state.viewSyncAction.isBatchAction)
  const selectedViews = useAppSelector((state: RootState) => state.viewSyncAction.selectedViews)
  const initialFilters = useAppSelector((state: RootState) => state.viewSyncTable.currentFilters)
  const [alertOpen, setAlertOpen] = useState<boolean>(false)
  const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
  const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
  const [alertLoading, setAlertLoading] = useState<boolean>(false)
  const [confirmMessage, setConfirmMessage] = useState<string>('')
  const [syncOptions, setSyncOptions] = useState<string[]>([])

  const onToggleBatchAction = () => {
    dispatch(toggleIsBatchAction())
  }

  const alertConfirmed = () => {
    const data = {
      view_ids: selectedViews,
      sync_options: syncOptions
    }
    postData(TRIGGER_SYNC_API_URL, data).then(
        response => {
          setAlertLoading(false)
          setAlertOpen(false)
          setConfirmMessage('Successfully syncing Views. Your request will be processed in the background.')
          dispatch(setInitialFilters(JSON.stringify({...initialFilters})))
        }
      ).catch(error => {
            setAlertLoading(false)
            setAlertOpen(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                setConfirmMessage('An error occurred. Please try it again later')
            }
    })
  }

  const handleAlertCancel = () => {
    setAlertOpen(false)
  }

  const onBatchMatchTilingClick = () => {
    setSyncOptions(['tiling_config'])
    setAlertDialogTitle('Batch Match Tiling Config')
    setAlertDialogDescription(
      `Are you sure you want to match ${selectedViews.length} tiling config to their dataset?`
    )
    setAlertOpen(true)
  }

  const onBatchSyncClick = () => {
    setSyncOptions(['tiling_config', 'vector_tiles', 'products'])
    setAlertDialogTitle('Batch Synchronize')
    setAlertDialogDescription(`Are you sure you want to synchronize ${selectedViews.length} views?`)
    setAlertOpen(true)
  }

  return (
    <div style={{display:'flex', flexDirection: 'row-reverse', alignItems: 'center'}}>
      <AlertMessage message={confirmMessage} onClose={() => setConfirmMessage('')} />
      <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                 alertConfirmed={alertConfirmed}
                 alertLoading={alertLoading}
                 alertDialogTitle={alertDialogTitle}
                 alertDialogDescription={alertDialogDescription} />
      { isBatchActionAvailable && (
        <div style={{display:'flex', flexDirection: 'row', alignItems: 'center'}}>
          { !isBatchAction && (
            <ThemeButton
              icon={<GradingIcon />}
              disabled={!isBatchActionAvailable}
              title={'Batch Action'}
              variant={'secondary'}
              onClick={onToggleBatchAction}
              sx={{marginLeft:'10px'}}
            />
          )}
          { isBatchAction && (
            <Typography variant={'subtitle2'} >{selectedViews.length} selected</Typography>
          )}
          { isBatchAction && (
            <AddButton
              disabled={selectedViews.length === 0}
              text={'Match tiling config with dataset'}
              variant={'secondary'}
              useIcon={false}
              additionalClass={'MuiButtonMedium'}
              onClick={onBatchMatchTilingClick}
              sx={{marginLeft:'10px'}}
            />
          )}
          { isBatchAction && (
            <AddButton
              disabled={selectedViews.length === 0}
              text={'Synchronize All'}
              variant={'secondary'}
              useIcon={false}
              additionalClass={'MuiButtonMedium'}
              onClick={onBatchSyncClick}
              sx={{marginLeft:'10px', marginRight:'10px'}}
            />
          )}
          { isBatchAction && (
            <CancelButton onClick={onToggleBatchAction} />
          )}
        </div>
      )}
    </div>
  )
}

interface ViewSyncRowInterface {
  id: number,
  name: string,
  is_tiling_config_match: boolean,
  vector_tile_sync_status: string,
  product_sync_status: string,
  vector_tiles_progress: number,
  product_progress: number,
  permissions: string[]
}

const FILTER_VALUES_API_URL = '/api/view-sync-filter/values/'
const VIEW_LIST_URL = '/api/view-sync-list/'
const TRIGGER_SYNC_API_URL = '/api/sync-view/'
const FilterIcon: any = FilterAlt


export default function ViewSyncList() {
  const initialColumns = useAppSelector((state: RootState) => state.viewSyncTable.currentColumns)
  const initialFilters = useAppSelector((state: RootState) => state.viewSyncTable.currentFilters)
  const availableFilters = useAppSelector((state: RootState) => state.viewSyncTable.availableFilters)
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<any[]>([])
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isBatchAction = useAppSelector((state: RootState) => state.viewSyncAction.isBatchAction)
  const isBatchActionAvailable = useAppSelector((state: RootState) => state.viewSyncAction.isBatchActionAvailable)
  const [allFinished, setAllFinished] = useState(true)
  const [currentInterval, setCurrentInterval] = useState<any>(null)

  const [columns, setColumns] = useState<any>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
  const [filterValues, setFilterValues] = useState<ViewSyncFilterInterface>(availableFilters)
  const [currentFilters, setCurrentFilters] = useState<ViewSyncFilterInterface>(initialFilters)
  const axiosSource = useRef(null)
  const newCancelToken = useCallback(() => {
    axiosSource.current = axios.CancelToken.source();
    return axiosSource.current.token;
  }, [])
  const ref = useRef(null)
  const [tableHeight, setTableHeight] = useState(0)

  let selectableRowsMode: any = isBatchAction ? 'multiple' : 'none'

  const fetchFilterValues = async () => {
    let filters = []
    filters.push(axios.get(`${FILTER_VALUES_API_URL}sync_status/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}dataset/`))
    let resultData = await Promise.all(filters)
    let filterVals = {
      'sync_status': resultData[0].data,
      'dataset': resultData[1].data,
      'search_text': ''
    }
    setFilterValues(filterVals)
    dispatch(setAvailableFilters(JSON.stringify(filterVals)))
    return filterVals
  }

  const fetchViewSyncList = () => {
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
      const productSyncStatus: string[] = response.data.results.reduce((res: string[], row: ViewSyncRowInterface) => {
          if (!res.includes(row.product_sync_status)) {
              res.push(row.product_sync_status)
          }
          return res
      }, [] as string[])
      const vectorTileSyncStatus: string[] = response.data.results.reduce((res: string[], row: ViewSyncRowInterface) => {
          if (!res.includes(row.vector_tile_sync_status)) {
              res.push(row.vector_tile_sync_status)
          }
          return res
      }, [] as string[])
      if (!productSyncStatus.includes('syncing') && !vectorTileSyncStatus.includes('syncing')) {
          setAllFinished(true)
      } else {
        setAllFinished(false)
      }
      setLoading(false)
      setData(response.data.results as ViewSyncRowInterface[])
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

  const syncView = (viewIds: number[], syncOptions: string[]) => {
    axios.post(
      TRIGGER_SYNC_API_URL,
      {
        'view_ids': viewIds,
        'sync_options': syncOptions
      }
    ).then((response) => {
      setLoading(false)
      fetchViewSyncList()
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
      case 'sync_status':
        values = currentFilters.sync_status
        break;
      case 'dataset':
        values = currentFilters.dataset
        break;
      default:
        break;
    }
    return values
  }

  useEffect(() => {
    const fetchFilterValuesData = async () => {
      let filterVals: any = {}
      if (filterValues.sync_status.length > 0) {
        filterVals = filterValues
      } else {
        filterVals = await fetchFilterValues()
      }
      const getLabel = (columnName: string) : string => {
        return columnName.charAt(0).toUpperCase() + columnName.slice(1).replaceAll('_', ' ')
      }

      let _columns = ['id', 'name', 'permissions', 'vector_tiles_progress', 'product_progress'].map((columnName) => {
        let _options: any = {
          name: columnName,
          label: getLabel(columnName),
          options: {
            display: initialColumns.includes(columnName),
            sort: columnName === 'name'
          }
        }
        _options.options.filter = false
        return _options
      })

      _columns.push({
        name: 'is_tiling_config_match',
        label: 'Tiling Config',
        options: {
          customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
            let rowData = tableMeta.rowData
            return (
              <Button
                aria-label={
                  rowData[5] ? 'Tiling config matches dataset' : 'Click to update tiling config'
                }
                title={
                  rowData[5] ? 'Tiling config matches dataset' : 'Click to update tiling config'
                }
                key={0}
                disabled={!rowData[2].includes('Manage')}
                onClick={(e) => {
                  e.stopPropagation()
                  syncView([rowData[0]], ['tiling_config'])
                }}
                variant={rowData[5] ? 'outlined' : 'contained'}
              >
                {
                  rowData[5] ?
                    'Tiling config matches dataset' :
                    'Update tiling config from dataset'
                }
              </Button>
            )
          },
          filter: false
        }
      })

      _columns.push({
        name: 'vector_tile_sync_status',
        label: 'Vector Tile',
        options: {
          customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
            let rowData = tableMeta.rowData
            const disabled = () => {
              if (rowData[2].includes('Manage')) {
                if (!rowData[5]) {
                  return true
                }
                return false
              }
              return false
            }
            const getButtonText = () => {
              if (rowData[6] === 'out_of_sync') {
                return 'Vector tiles need refresh'
              } else if (rowData[6] === 'synced') {
                return 'Vector tiles are synced'
              } else if (rowData[6] === 'syncing') {
                return `Syncing (${rowData[3].toFixed(1)}%)`
              }
            }
            return (
              <Button
                aria-label={
                  rowData[6] ? 'Vector tiles are synced' : 'Click to update vector tiles'
                }
                title={
                  rowData[6] ? 'Vector tiles are synced' : 'Click to update vector tiles'
                }
                key={0}
                disabled={disabled()}
                onClick={(e) => {
                  e.stopPropagation()
                  if (rowData[6] === 'synced') {
                    return
                  }
                  syncView([rowData[0]], ['vector_tiles'])
                }}
                variant={rowData[6] === 'out_of_sync' ? 'contained': 'outlined'}
              >
                {getButtonText()}
              </Button>
            )
          },
          filter: false
        }
      })

      _columns.push({
        name: 'product_sync_status',
        label: 'Data Product',
        options: {
          customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
            let rowData = tableMeta.rowData
            const disabled = () => {
              if (rowData[2].includes('Manage')) {
                if (!rowData[5]) {
                  return true
                }
                return false
              }
              return false
            }
            const getButtonText = () => {
              if (rowData[7] === 'out_of_sync') {
                return 'Data product needs refresh'
              } else if (rowData[7] === 'synced') {
                return 'Data product is synced'
              } else if (rowData[7] === 'syncing') {
                return `Syncing (${rowData[4].toFixed(1)}%)`
              }
            }
            return (
              <Button
                aria-label={
                  rowData[7] ? 'Data products are synced' : 'Click to update data products'
                }
                title={
                  rowData[7] ? 'Data products are synced' : 'Click to update data products'
                }
                key={0}
                disabled={disabled()}
                onClick={(e) => {
                  e.stopPropagation()
                  if (rowData[7] === 'synced') {
                    return
                  }
                  syncView([rowData[0]], ['products'])
                }}
                variant={rowData[7] === 'out_of_sync' ? 'contained': 'outlined'}
              >
                {getButtonText()}
              </Button>
            )
          },
          filter: false
        }
      })

      _columns.push(
        {
          name: 'sync_status',
          label: 'Sync Status',
          options: {
            display: false,
            sort: false,
            filter: true,
            filterOptions: {
              names: filterVals['sync_status']
            },
            filterList: getExistingFilterValue('sync_status')
          }
        }
      )
      _columns.push(
        {
          name: 'dataset',
          label: 'Dataset',
          options: {
            display: false,
            sort: false,
            filter: true,
            filterOptions: {
              names: filterVals['dataset']
            },
            filterList: getExistingFilterValue('dataset')
          }
        }
      )
      _columns.push({
        name: '',
        label: 'Action',
        options: {
          customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
            let rowData = tableMeta.rowData
            return (
              <Stack spacing={2} direction="row">
                <Button
                  aria-label={'Details'}
                  title={'Details'}
                  key={0}
                  disabled={!rowData[2].includes('Manage')}
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/view_edit?id=${rowData[0]}&tab=4`)
                  }}
                  variant={'contained'}
                >
                  Details
                </Button>

                <Button
                  aria-label={'Synchronize'}
                  title={'Synchronize'}
                  key={0}
                  disabled={!rowData[2].includes('Manage') }
                  onClick={(e) => {
                    e.stopPropagation()
                    if (rowData[6] === 'synced' && rowData[7] === 'synced') {
                      return
                    }
                    syncView(
                      [rowData[0]],
                      ['tiling_config', 'vector_tiles', 'products']
                    )
                  }}
                  variant={
                    !rowData[5] || rowData[6] === 'out_of_sync' || rowData[5] === 'out_of_sync' ?
                      'contained' : 'outlined'
                  }
                >
                  Synchronize
                </Button>
              </Stack>
            )
          },
          filter: false
        }
      })

      setColumns(_columns)
    }
    fetchFilterValuesData()
  }, [pagination, currentFilters])

  // useEffect(() => {
  //   if (!allFinished) {
  //       if (currentInterval) {
  //           clearInterval(currentInterval)
  //           setCurrentInterval(null)
  //       }
  //       const interval = setInterval(() => {
  //           fetchViewSyncList()
  //       }, 10000);
  //       setCurrentInterval(interval)
  //       return () => clearInterval(interval);
  //   }
  // }, [allFinished])

  useEffect(() => {
    fetchViewSyncList()
  }, [pagination, filterValues, currentFilters, initialFilters])

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
        filter[key as keyof ViewSyncFilterInterface] = filterList[idx]
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
    let dataset
    try {
      dataset = searchParams.get('dataset') ? [searchParams.get('dataset')] : []
    } catch (error: any) {
      dataset = currentFilters['dataset']
    }
    setCurrentFilters({...currentFilters, 'dataset': dataset})
    dispatch(setInitialFilters(JSON.stringify({...currentFilters, 'dataset': dataset})))
  }, [searchParams])

  const canRowBeSelected = (dataIndex: number, rowData: any) => {
    if (!isBatchActionAvailable)
      return false
    return !((rowData.is_tiling_config_match &&
      rowData.product_sync_status === 'synced' &&
      rowData.vector_tile_sync_status === 'synced') ||
      (
        rowData.product_sync_status === 'syncing' || rowData.vector_tile_sync_status === 'syncing'
      ))
  }

  const selectionChanged = (data: any) => {
    dispatch(setSelectedViews(data))
  }

  return (
    loading ?
      <div className={"loading-container"}><Loading/></div> :
      <div className="AdminContentMain view-sync-list main-data-list">
        <Fragment>
          <Box sx={{textAlign:'right'}}>
            <ViewSyncActionButtons/>
          </Box>
          <div className='AdminList' ref={ref}>
            <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                                onResize={(clientHeight: number) => setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)}/>
            <div className='AdminTable'>
              <MUIDataTable
                title={''}
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
                  onTableChange: (action: string, tableState: any) => onTableChangeState(action, tableState),
                  customSearchRender: debounceSearchRender(500),
                  selectableRows: selectableRowsMode,
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
      </div>
  )
}
