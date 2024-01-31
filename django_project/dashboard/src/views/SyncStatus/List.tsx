import React, {Fragment, useCallback, useEffect, useRef, useState} from "react";
import {useNavigate, useSearchParams} from "react-router-dom";

import {Button} from '@mui/material';
import IconButton from '@mui/material/IconButton';
import FilterAlt from "@mui/icons-material/FilterAlt";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import axios from "axios";

import Loading from "../../components/Loading";
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import ResizeTableEvent from "../../components/ResizeTableEvent";
import {RootState} from "../../app/store";
import {TABLE_OFFSET_HEIGHT} from "../../components/List";
import {
  getDefaultFilter,
  ViewSyncFilterInterface,
  TILING_CONFIG_STATUS_FILTER,
  SIMPLIFICATION_STATUS_FILTER,
  VECTOR_TILE_SYNC_STATUS_FILTER
} from "../../models/syncStatus"
import {
  setSelectedViews,
  toggleIsBatchAction,
  onBatchActionSubmitted,
  addSelectedView,
  removeSelectedView,
  updateRowsSelectedInPage,
  resetSelectedViews
} from "../../reducers/viewSyncAction";
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
import Grid from "@mui/material/Grid";
import '../../styles/ViewSync.scss';
import LinearProgress from '@mui/material/LinearProgress';
import SyncIcon from '@mui/icons-material/Sync';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import SyncProblemIcon from '@mui/icons-material/SyncProblem';
import { DatasetDetailItemInterface } from "../../models/dataset";


export function ViewSyncActionButtons() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const isBatchActionAvailable = useAppSelector((state: RootState) => state.viewSyncAction.isBatchActionAvailable)
  const isBatchAction = useAppSelector((state: RootState) => state.viewSyncAction.isBatchAction)
  const selectedViews = useAppSelector((state: RootState) => state.viewSyncAction.selectedViews)
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
    onToggleBatchAction()
    setAlertLoading(true)
    const data = {
      view_ids: selectedViews,
      sync_options: syncOptions
    }
    postData(TRIGGER_SYNC_API_URL, data).then(
        response => {
          setAlertLoading(false)
          setConfirmMessage('Successfully syncing Views. Your request will be processed in the background.')
          dispatch(onBatchActionSubmitted())
          setAlertOpen(false)
        }
      ).catch(error => {
            onToggleBatchAction()
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
      `Are you sure you want to match ${selectedViews.length} tiling config with their dataset? 
      This would also override your view's custom tiling config.`
    )
    setAlertOpen(true)
  }

  const onBatchSyncClick = () => {
    setSyncOptions(['vector_tiles'])
    setAlertDialogTitle('Batch Synchronize')
    setAlertDialogDescription(
      `Are you sure you want to synchronize ${selectedViews.length} views?
      Both Vector Tiles and Data Products will be synchronized.`
    )
    setAlertOpen(true)
  }

  return (
    <div style={{display:'flex', flexDirection: 'row', alignItems: 'center'}}>
      <AlertMessage message={confirmMessage} onClose={() => setConfirmMessage('')} />
      <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                 alertConfirmed={alertConfirmed}
                 alertLoading={alertLoading}
                 alertDialogTitle={alertDialogTitle}
                 alertDialogDescription={alertDialogDescription} />
      <div style={{display:'flex', flexDirection: 'row', alignItems: 'center', flex: '1'}}>
      </div>
      <div style={{display:'flex', flexDirection: 'row', justifyContent: 'flex-end', flex: '1'}}>
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
                text={'Match Tiling Config with Dataset'}
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
    </div>
  )
}

interface ViewSyncRowInterface {
  id: number,
  name: string,
  is_tiling_config_match: boolean,
  simplification_status: string,
  vector_tile_sync_status: string,
  simplification_progress: number,
  vector_tiles_progress: number,
  permissions: string[]
}

const VIEW_LIST_URL = '/api/view-sync-list/'
const TRIGGER_SYNC_API_URL = '/api/sync-view/'
const FilterIcon: any = FilterAlt
const SELECT_ALL_LIST_URL = '/api/view-sync-list-select-all/'

const getQueued = () => {
  return (
    <span className='sync-status-desc-container'>
      <HourglassEmptyIcon color='info' fontSize='small' />
      <span className='sync-status-desc'>{'Queued but not running yet'}</span>
    </span>
  )
}
const getSyncing = (progress: number) => {
  return (
    <span className='running-status'>
        <span className='sync-status-desc-container'>
          <SyncIcon color='info' fontSize='small' />
          <span className='sync-status-desc'>{`Actively being processed`}</span>                      
        </span>
        <LinearProgress variant="determinate" value={progress} />
    </span>
  )
}
const getSynced = (text: string) => {
  return (
    <span className='sync-status-desc-container'>
      <CheckCircleIcon color='success' fontSize='small' />
      <span className='sync-status-desc'>{text}</span>
    </span>
  )
}
const getOutOfSync = (text: string, syncButtonText: string, syncButtonDisabled: boolean, syncButtonOnClick: any) => {
  return (
    <span className='sync-status-desc-container'>
      <SyncProblemIcon color='warning' fontSize='small' />
      <span className='sync-status-desc'>{text}</span>
      { !syncButtonDisabled &&
      <IconButton aria-label={syncButtonText} title={syncButtonText} onClick={syncButtonOnClick} disabled={syncButtonDisabled}>
          <SyncIcon color='info' fontSize='small' />
      </IconButton>
      }
    </span>
  )
}
const getError = (syncButtonText: string, syncButtonDisabled: boolean, syncButtonOnClick: any) => {
  return (
    <span className='sync-status-desc-container'>
      <ErrorIcon color='error' fontSize='small' />
      <span className='sync-status-desc'>{`Terminated unexpectedly`}</span>
      { !syncButtonDisabled &&
      <IconButton aria-label={syncButtonText} title={syncButtonText} onClick={syncButtonOnClick} disabled={syncButtonDisabled}>
          <SyncIcon color='info' fontSize='small' />
      </IconButton>
      }
    </span>
  )
}


export default function ViewSyncList(props: DatasetDetailItemInterface) {
  const initialColumns = useAppSelector((state: RootState) => state.viewSyncTable.currentColumns)
  const initialFilters = useAppSelector((state: RootState) => state.viewSyncTable.currentFilters)
  const syncStatusUpdatedAt = useAppSelector((state: RootState) => state.viewSyncAction.updatedAt)
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<any[]>([])
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isBatchAction = useAppSelector((state: RootState) => state.viewSyncAction.isBatchAction)
  const isBatchActionAvailable = useAppSelector((state: RootState) => state.viewSyncAction.isBatchActionAvailable)
  const [allFinished, setAllFinished] = useState(true)
  const [currentInterval, setCurrentInterval] = useState<any>(null)
  const [confirmMessage, setConfirmMessage] = useState<string>('')

  const [columns, setColumns] = useState<any>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
  const [currentFilters, setCurrentFilters] = useState<ViewSyncFilterInterface>(initialFilters)
  const axiosSource = useRef(null)
  const newCancelToken = useCallback(() => {
    axiosSource.current = axios.CancelToken.source();
    return axiosSource.current.token;
  }, [])
  const ref = useRef(null)
  const [tableHeight, setTableHeight] = useState(0)
  const fetchViewSyncListFuncRef = useRef(null)
  const rowsSelectedInPage = useAppSelector((state: RootState) => state.viewSyncAction.rowsSelectedInPage)

  let selectableRowsMode: any = isBatchAction ? 'multiple' : 'none'

  const fetchViewSyncList = (interval: boolean = false) => {
    if (axiosSource.current) axiosSource.current.cancel()
    let cancelFetchToken = newCancelToken()
    if (!interval) {
      setLoading(true)
    }
    let sortBy = pagination.sortOrder.name ? pagination.sortOrder.name : ''
    let sortDirection = pagination.sortOrder.direction ? pagination.sortOrder.direction : ''
    const datasetId = searchParams.get('id')
    const url = `${VIEW_LIST_URL}${datasetId}?` + `page=${pagination.page + 1}&page_size=${pagination.rowsPerPage}` +
      `&sort_by=${sortBy}&sort_direction=${sortDirection}`
    axios.post(
      url,
      currentFilters,
      {
        cancelToken: cancelFetchToken
      }
    ).then((response) => {
      setLoading(false)
      const simplificationSyncStatus: string[] = response.data.results.reduce((res: string[], row: ViewSyncRowInterface) => {
          if (!res.includes(row.simplification_status)) {
              res.push(row.simplification_status)
          }
          return res
      }, [] as string[])
      const vectorTileSyncStatus: string[] = response.data.results.reduce((res: string[], row: ViewSyncRowInterface) => {
          if (!res.includes(row.vector_tile_sync_status)) {
              res.push(row.vector_tile_sync_status)
          }
          return res
      }, [] as string[])
      if (!simplificationSyncStatus.includes('syncing') && !vectorTileSyncStatus.includes('syncing')) {
          setAllFinished(true)
          props.onSyncStatusShouldBeUpdated()
      } else {
        setAllFinished(false)
      }
      setTotalCount(response.data.count)
      setData(response.data.results as ViewSyncRowInterface[])
      dispatch(updateRowsSelectedInPage(response.data.results))
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
  // store ref of fetchViewSyncList
  fetchViewSyncListFuncRef.current = fetchViewSyncList

  const syncView = (viewIds: number[], syncOptions: string[]) => {
    axios.post(
      TRIGGER_SYNC_API_URL,
      {
        'view_ids': viewIds,
        'sync_options': syncOptions
      }
    ).then((response) => {
      setLoading(false)
      setConfirmMessage('Successfully submitting data regeneration. Your request will be processed in the background.')
      if (fetchViewSyncListFuncRef.current) {
        fetchViewSyncListFuncRef.current(true)
      }
      props.onSyncStatusShouldBeUpdated()
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
      case 'is_tiling_config_match':
        values = currentFilters.is_tiling_config_match  
        break;
      case 'simplification_status':
        values = currentFilters.simplification_status
        break;
      case 'vector_tile_sync_status':
        values = currentFilters.vector_tile_sync_status
        break;
      default:
        break;
    }
    return values
  }

  useEffect(() => {
    // if (data.length > 0 && columns.length === 0) {
      // const fetchFilterValuesData = async () => {
        const getLabel = (columnName: string) : string => {
          return columnName.charAt(0).toUpperCase() + columnName.slice(1).replaceAll('_', ' ')
        }
  
        let _columns = ['id', 'name', 'permissions', 'simplification_progress', 'vector_tiles_progress'].map((columnName) => {
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
                <span>{rowData[5] ? 'Tiling config matches dataset' : 'View uses custom tiling config'}</span>
              )
            },
            filter: true,
            filterOptions: {
              fullWidth: true,
              names: TILING_CONFIG_STATUS_FILTER
            },
            filterList: getExistingFilterValue('is_tiling_config_match'),
            sort: false
          }
        })

        _columns.push({
          name: 'simplification_status',
          label: 'Simplification',
          options: {
            customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
              let rowData = tableMeta.rowData
              let _status = rowData[6]
              let _progress = rowData[3] as number

              if (_status === 'out_of_sync') {
                return (
                  getOutOfSync('Out of Sync', 'Click to trigger simplification', !rowData[2].includes('Manage'), (e: any) => {
                    e.stopPropagation()
                    syncView([rowData[0]], ['simplify'])
                  })
                )
              } else if (_status === 'synced') {
                return getSynced('Done')
              } else if (_status === 'syncing') {
                return getSyncing(_progress)
              } else if (_status === 'error') {
                return (
                  getError('Click to retrigger simplification', !rowData[2].includes('Manage'), (e: any) => {
                    e.stopPropagation()
                    syncView([rowData[0]], ['simplify'])
                  })
                )
              }
              return (
                <span>{_status}</span>
              )
            },
            filter: true,
            filterOptions: {
              fullWidth: true,
              names: SIMPLIFICATION_STATUS_FILTER
            },
            filterList: getExistingFilterValue('simplification_status'),
            sort: false,
            customFilterListOptions: {
              render: (v: any) => `Simplification Status: ${v}`
            }
          }
        })
  
        _columns.push({
          name: 'vector_tile_sync_status',
          label: 'Vector Tile',
          options: {
            customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
              let rowData = tableMeta.rowData
              let _status = rowData[7]
              let _progress = rowData[4] as number
              let _simplificationStatus = rowData[6]
              if (_status === 'out_of_sync') {
                if (_simplificationStatus !== 'synced') {
                  return (
                    getOutOfSync('Vector tiles need refresh', 'Please trigger simplification before regenerate vector tiles!', true, () => {})
                  )
                }
                return (
                  getOutOfSync('Vector tiles need refresh', 'Click to update vector tiles', !rowData[2].includes('Manage'), (e: any) => {
                    e.stopPropagation()
                    syncView([rowData[0]], ['vector_tiles'])
                  })
                )
              } else if (_status === 'synced') {
                return getSynced('Vector tiles are synced')
              } else if (_status === 'syncing') {
                return getSyncing(_progress)
              } else if (_status === 'Queued') {
                return getQueued()
              } else if (_status === 'error') {
                if (_simplificationStatus !== 'synced') {
                  return (
                    getOutOfSync('Vector tiles need refresh', 'Please trigger simplification before regenerate vector tiles!', true, () => {})
                  )
                }
                return (
                  getError('Click to retrigger vector tiles generation', !rowData[2].includes('Manage'), (e: any) => {
                    e.stopPropagation()
                    syncView([rowData[0]], ['vector_tiles'])
                  })
                )
              }
              return (
                <span>{_status}</span>
              )
            },
            filter: true,
            filterOptions: {
              fullWidth: true,
              names: VECTOR_TILE_SYNC_STATUS_FILTER
            },
            filterList: getExistingFilterValue('vector_tile_sync_status'),
            sort: false,
            customFilterListOptions: {
              render: (v: any) => `Vector Tile Sync Status: ${v}`
            }
          }
        })

        _columns.push({
          name: '',
          label: 'Action',
          options: {
            customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
              let rowData = tableMeta.rowData
              let _simplificationStatus = rowData[6]
              let _syncButtonDisabled = rowData[7] === 'synced'|| rowData[7] === 'syncing'
              let _syncInQueued = rowData[7] === 'Queued'
              const getSyncText = () => {
                if (_syncButtonDisabled) {
                  return 'Vector Tile and Data Products are synchronized'
                }
                if (_simplificationStatus !== 'synced') return 'Please trigger simplification before regenerate vector tiles!'
                if (_syncInQueued) return 'Waiting in the queue'
                return 'Synchronize'
              }
              return (
                <Stack spacing={2} direction="row">
                  <Button
                    aria-label={'Details'}
                    title={'Details'}
                    disabled={!rowData[2].includes('Manage')}
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate(`/view_edit?id=${rowData[0]}&tab=5`)
                    }}
                    variant={'contained'}
                  >
                    Details
                  </Button>
  
                  <Button
                    aria-label={'Synchronize'}
                    title={getSyncText()}
                    disabled={!rowData[2].includes('Manage') || _syncButtonDisabled || _simplificationStatus !== 'synced' || _syncInQueued }
                    onClick={(e) => {
                      e.stopPropagation()
                      if (_syncButtonDisabled || _simplificationStatus !== 'synced' || _syncInQueued) {
                        return
                      }
                      syncView(
                        [rowData[0]],
                        ['vector_tiles']
                      )
                    }}
                    variant={
                      rowData[7] === 'out_of_sync' ? 'contained' : 'outlined'
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
      // }
      // fetchFilterValuesData()
    // }
  }, [data, pagination, currentFilters])

  useEffect(() => {
    if (!allFinished) {
        if (currentInterval) {
            clearInterval(currentInterval)
            setCurrentInterval(null)
        }
        const interval = setInterval(() => {
            fetchViewSyncList(true)
        }, 5000);
        setCurrentInterval(interval)
        return () => clearInterval(interval);
    }
  }, [allFinished])

  useEffect(() => {
    if (currentInterval) {
      clearInterval(currentInterval)
      setCurrentInterval(null)
      setAllFinished(true)
    }
    fetchViewSyncList()
  }, [pagination, currentFilters, initialFilters, searchParams])

  useEffect(() => {
    if (syncStatusUpdatedAt) {
      if (currentInterval) {
        clearInterval(currentInterval)
        setCurrentInterval(null)
        setAllFinished(true)
      }
      fetchViewSyncList(true)
    }
  }, [syncStatusUpdatedAt])

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

  const canRowBeSelected = (dataIndex: number, rowData: any) => {
    if (!isBatchActionAvailable)
      return false
    return !((rowData.is_tiling_config_match &&
      rowData.vector_tile_sync_status === 'synced') ||
      (
        rowData.vector_tile_sync_status === 'syncing'
      ))
  }


  const fetchSelectAllViewList = () => {
    const datasetId = searchParams.get('id')
    const url = `${SELECT_ALL_LIST_URL}${datasetId}`
    // setStatusDialogOpen(true)
    axios.post(
      url,
      currentFilters
    ).then((response) => {
      // setStatusDialogOpen(false)
      dispatch(setSelectedViews([response.data, data]))
    }).catch(error => {
      console.log(error)
      // setStatusDialogOpen(false)
      if (error.response) {
        if (error.response.status == 403) {
          // TODO: use better way to handle 403
          navigate('/invalid_permission')
        }
      }
    })
  }

  return (
    loading ?
      <div className={"loading-container"}><Loading/></div> :
      <div className="AdminContentMain view-sync-list main-data-list">
        <AlertMessage message={confirmMessage} onClose={() => setConfirmMessage('')} />
        <Fragment>
          <Box sx={{textAlign:'right'}}>
            <ViewSyncActionButtons/>
          </Box>
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
                    if (currentRowsSelected.length > 1) {
                      // select all
                      fetchSelectAllViewList()
                    } else if (currentRowsSelected.length === 1) {
                      // check/uncheck single item
                      let _item = data[currentRowsSelected[0]['index']]
                      if (rowsSelected.indexOf(currentRowsSelected[0]['index']) > -1) {
                        // selected
                        dispatch(addSelectedView(_item['id']))
                      } else {
                        // deselected
                        dispatch(removeSelectedView(_item['id']))
                      }
                    } else if (currentRowsSelected.length === 0) {
                      // deselect all
                      dispatch(resetSelectedViews())
                    }
                  },
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
                  selectableRowsHeader: false
                }}
                components={{
                  icons: {
                    FilterIcon
                  }
                }}
              />
            </div>
          </div>
          <Box>
            <Grid container flexDirection={'column'} alignItems={'flex-start'} sx={{marginTop: '10px'}}>
              <Grid item>
                Match Tiling Config with Dataset will also override view's custom tiling config.
              </Grid>
              <Grid item>
                Synchronize and Synchronize All will regenerate vector tiles and data products.
              </Grid>
            </Grid>
          </Box>
        </Fragment>
      </div>
  )
}
