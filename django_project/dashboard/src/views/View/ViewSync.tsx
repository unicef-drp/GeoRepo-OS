import React, {Fragment, useCallback, useEffect, useRef, useState} from 'react';
import View from "../../models/view";
import {useAppDispatch} from "../../app/hooks";
import {useNavigate} from "react-router-dom";
import {rowsPerPageOptions} from "../../models/pagination";
import axios from "axios";
import Loading from "../../components/Loading";
import ResizeTableEvent from "../../components/ResizeTableEvent";
import {TABLE_OFFSET_HEIGHT} from "../../components/List";
import MUIDataTable, {debounceSearchRender} from "mui-datatables";
import Box from "@mui/material/Box";
import {ThemeButton} from "../../components/Elements/Buttons";
import CircularProgress from "@mui/material/CircularProgress";
import AlertMessage from "../../components/AlertMessage";


interface ViewResourceInterface {
    view: View
}

const VIEW_RESOURCE_SYNC_LIST_URL = '/api/view-resource-sync-list/'
const TRIGGER_SYNC_API_URL = '/api/sync-view/'

const COLUMNS = [
    'id',
    'uuid',
    'privacy_level',
    'vector_tile_sync_status',
    'geojson_sync_status',
    'shapefile_sync_status',
    'kml_sync_status',
    'topojson_sync_status',
    'vector_tiles_progress',
    'geojson_progress',
    'shapefile_progress',
    'kml_progress',
    'topojson_progress',
    'vector_tiles_size',
    'geojson_size',
    'shapefile_size',
    'kml_size',
    'topojson_size'
]

const DEFAULT_SHOWN_COLUMNS = [
    'privacy_level',
    'vector_tile_sync_status',
    'geojson_sync_status',
    'shapefile_sync_status',
    'kml_sync_status',
    'topojson_sync_status'
]

export default function ViewSync(props: ViewResourceInterface) {
    const [loading, setLoading] = useState<boolean>(true)
    const [data, setData] = useState<any[]>([])
    const navigate = useNavigate()
    const dispatch = useAppDispatch()
    const [allFinished, setAllFinished] = useState(true)
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const [columns, setColumns] = useState<any>([])
    const [confirmMessage, setConfirmMessage] = useState<string>('')

    const axiosSource = useRef(null)
    const newCancelToken = useCallback(() => {
      axiosSource.current = axios.CancelToken.source();
      return axiosSource.current.token;
    }, [])
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)

    const getColumnDef = () => {
      const getLabel = (columnName: string) : string => {
          columnName = columnName.replaceAll('_sync_status', '')
          return columnName.charAt(0).toUpperCase() + columnName.slice(1).replaceAll('_', ' ')
        }

        let _columns = COLUMNS.map((columnName) => {
          let _options: any = {
            name: columnName,
            label: getLabel(columnName),
            options: {
              display: DEFAULT_SHOWN_COLUMNS.includes(columnName),
              sort: false
            }
          }
          _options.options.filter = false
          return _options
        })
        for (let i=3; i < 8; i++) {
          let col = _columns[i]
          col.options.customBodyRender = (value: any, tableMeta: any, updateValue: any) => {
            let rowData = tableMeta.rowData
            if (rowData[i] === 'out_of_sync') {
              return 'Out of sync'
            } else if (rowData[i] === 'syncing' || rowData[i] === 'Running') {
              return (
                <span style={{display:'flex'}}>
                    <CircularProgress size={18} />
                    <span style={{marginLeft: '5px' }}>{`Syncing (${rowData[i+5].toFixed(1)}%)`}</span>
                </span>
              )
            } else if (rowData[i] === 'Stopped' || rowData[i] === 'Queued') {
              return rowData[i]
            } else {
              return `Synced (${rowData[i+10]})`
            }
          }
          _columns[i] = col
        }
        setColumns(_columns)
    }

    const fetchViewResource = () => {
      axios.get(
        `${VIEW_RESOURCE_SYNC_LIST_URL}${props.view.id}`
      ).then((response) => {
        setLoading(false)
        setData(response.data)
        let allStatus: string[] = []
        let products: string[] = ['vector_tile', 'geojson', 'shapefile', 'kml', 'topojson']
        //@ts-ignore
        products.forEach(function(product: string, idx: number){
          response.data.forEach(function (row: any, idxRow: number) {
            if (!allStatus.includes(row[`${product}_sync_status`])) {
              allStatus.push(row[`${product}_sync_status`])
            }
          })
        });
        if (!allStatus.includes('syncing')) {
            setAllFinished(true)
        } else {
          setAllFinished(false)
        }
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

    useEffect(() => {
      setLoading(true)
      fetchViewResource()
      getColumnDef()
    }, [])

    useEffect(() => {
    if (!allFinished) {
        if (currentInterval) {
            clearInterval(currentInterval)
            setCurrentInterval(null)
        }
        const interval = setInterval(() => {
            fetchViewResource()
        }, 5000);
        setCurrentInterval(interval)
        return () => clearInterval(interval);
    }
  }, [allFinished])

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
        fetchViewResource()
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

    const regenerateVectorTiles = () => {
      syncView(
        [props.view.id],
        ['vector_tiles']
      )
    }

    const regenerateProductData = () => {
      syncView(
        [props.view.id],
        ['products']
      )
    }

    const regenerateAll = () => {
      syncView(
        [props.view.id],
        ['vector_tiles', 'products']
      )
    }

    return (
    loading ?
      <div className={"loading-container"}><Loading/></div> :
      <div className="AdminContentMain view-sync-list main-data-list">
          <Fragment>
            <AlertMessage message={confirmMessage} onClose={() => setConfirmMessage('')} />
            <div className='AdminList' ref={ref}>
              <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                                  onResize={(clientHeight: number) => setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)}/>
              <div className='AdminTable'>
                <MUIDataTable
                  title={
                    <Box sx={{textAlign:'left'}}>
                      <ThemeButton
                        variant={'secondary'}
                        onClick={regenerateVectorTiles}
                        title={'Regenerate Vector Tiles'}
                        icon={null}
                        sx={{marginRight:'10px'}}
                      />

                      <ThemeButton
                        variant={'secondary'}
                        onClick={regenerateProductData}
                        title={'Regenerate Product Data'}
                        icon={null}
                        sx={{marginRight:'10px'}}
                      />

                      <ThemeButton
                        variant={'secondary'}
                        onClick={regenerateAll}
                        title={'Regenerate All'}
                        icon={null}
                        sx={{marginRight:'10px'}}
                      />
                    </Box>
                  }
                  data={data}
                  columns={columns}
                  options={{
                    rowsPerPageOptions: rowsPerPageOptions,
                    jumpToPage: true,
                    customSearchRender: debounceSearchRender(500),
                    selectableRows: 'none',
                    textLabels: {
                      body: {
                        noMatch: loading ?
                          <Loading/> :
                          'Sorry, there is no matching data to display',
                      },
                    },
                    filter: false,
                    tableBodyHeight: `${tableHeight}px`,
                    tableBodyMaxHeight: `${tableHeight}px`,
                  }}
                />
              </div>
            </div>
          </Fragment>
      </div>
  )
}