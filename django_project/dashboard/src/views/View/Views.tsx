import React, {Fragment, useCallback, useEffect, useRef, useState} from 'react';
import {useNavigate, useSearchParams} from "react-router-dom";
import {TABLE_OFFSET_HEIGHT} from "../../components/List";
import Loading from "../../components/Loading";
import {postData} from "../../utils/Requests";
import {ViewEditRoute} from "../routes";
import AlertDialog from '../../components/AlertDialog'
import {Button, Chip} from '@mui/material';
import Grid from '@mui/material/Grid';
import DeleteIcon from "@mui/icons-material/Delete";
import MoreVertIcon from '@mui/icons-material/MoreVert';
import Popover from '@mui/material/Popover';
import Typography from '@mui/material/Typography';
import Checkbox from '@mui/material/Checkbox';
import TextField from '@mui/material/TextField';
import Autocomplete from '@mui/material/Autocomplete';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import PaginationInterface, {getDefaultPagination, rowsPerPageOptions} from "../../models/pagination";
import axios from "axios";
import IconButton from "@mui/material/IconButton";
import {getDefaultFilter, ViewsFilterInterface} from "./ViewsFilter"
import ResizeTableEvent from "../../components/ResizeTableEvent";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import FilterAlt from "@mui/icons-material/FilterAlt";

import { useAppSelector, useAppDispatch } from '../../app/hooks';
import {
  setAvailableFilters,
  setCurrentFilters as setInitialFilters
} from "../../reducers/viewTable";
import {RootState} from "../../app/store";


const checkBoxOutlinedicon = <CheckBoxOutlineBlankIcon fontSize="small" />;
const checkBoxCheckedIcon = <CheckBoxIcon fontSize="small" />;

const VIEW_LIST_URL = '/api/view-list/'
const FILTER_VALUES_API_URL = '/api/view-filter/values/'
const DELETE_VIEW_URL = '/api/delete-view'

const USER_COLUMNS = [
  'id',
  'name',
  'description',
  'tags',
  'mode',
  'dataset',
  'is_default',
  'min_privacy',
  'max_privacy',
  'layer_tiles',
  'status',
  'uuid',
  'permissions',
  'layer_preview'
]

const COLUMN_NAME_LABEL: any = {
  'dataset': 'Dataset'
}

interface ViewTableRowInterface {
  id: number,
  name: string,
  description: string,
  tags: string[],
  mode: string,
  dataset: string,
  is_default: string,
  min_privacy: number,
  max_privacy: number,
  layer_tiles: string,
  status: string,
  uuid: string,
  permissions: string[],
  layer_preview: string,
}


const copyToClipboard = (value: string) => {
  navigator.clipboard.writeText(value)
  alert('Link copied')
}

function ViewPopover(props: any) {
  if (props.view === null) {
    return null
  }
  return (
    <Grid container flexDirection={'column'} sx={{p: 2}}>
      <Grid item>
        <Typography sx={{pb: 1}}>Mode: {props.view.mode}</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{pb: 1}}>Is Default: {props.view.is_default}</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{pb: 0}}>UUID:</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{pb: 1}}>{props.view.uuid}</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{pb: 1}}>Layer Tiles:</Typography>
      </Grid>
      {props.view.layer_tiles &&
      <Grid item>
        <Grid container flexDirection={'row'} justifyContent={'space-between'} spacing={2} sx={{pb: 1}}>
          <Grid item>
            {props.view.layer_tiles && (
              <Button variant={'outlined'} onClick={() => copyToClipboard(props.view.layer_tiles)}>Copy Vector Tile URL</Button>
            )}            
          </Grid>
          <Grid item>
            {props.view.layer_preview && (
              <Button variant={'outlined'} href={props.view.layer_preview} target='_blank'>Preview</Button>
            )}
          </Grid>
        </Grid>
      </Grid>
      }
      {!props.view.layer_tiles &&
      <Grid item>
        <Typography sx={{pb: 1}}>Tiles not available yet. Go to sync tab to generate.</Typography>
      </Grid>
      }
      {props.view.layer_tiles &&
      <Grid item>
        <Grid container flexDirection={'column'}>
          <Grid item>
            <Typography sx={{pb: 1}}>Logs:</Typography>
          </Grid>
          <Grid item>
            <Button
              variant={'outlined'}
              onClick={() => window.open(`/api/logs/dataset_view/${props.view.id}`, '_blank')}
            >
              Logs
            </Button>
          </Grid>
        </Grid>
      </Grid>
      }
    </Grid>
  )
}

export default function Views() {
  const dispatch = useAppDispatch()
  const initialColumns = useAppSelector((state: RootState) => state.viewTable.currentColumns)
  const initialFilters = useAppSelector((state: RootState) => state.viewTable.currentFilters)
  const availableFilters = useAppSelector((state: RootState) => state.viewTable.availableFilters)
  const [selectedView, setSelectedView] = useState<Array<any>>(null)
  const [confirmationOpen, setConfirmationOpen] = useState<boolean>(false)
  const [confirmationText, setConfirmationText] = useState<string>('')
  const [deleteButtonDisabled, setDeleteButtonDisabled] = useState<boolean>(false)
  const navigate = useNavigate()
  const [anchorEl, setAnchorEl] = React.useState<HTMLButtonElement | null>(null);
  const [searchParams, setSearchParams] = useSearchParams()


  const [loading, setLoading] = useState(true)
  const [columns, setColumns] = useState<any>([])
  const [data, setData] = useState<ViewTableRowInterface[]>([])
  const [userPermissions, setUserPermissions] = useState<string[]>([])
  const [totalCount, setTotalCount] = useState<number>(0)
  const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
  const [filterValues, setFilterValues] = useState<ViewsFilterInterface>(availableFilters)
  const [currentFilters, setCurrentFilters] = useState<ViewsFilterInterface>(initialFilters)
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
    filters.push(axios.get(`${FILTER_VALUES_API_URL}tags/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}mode/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}dataset/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}is_default/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}min_privacy/`))
    filters.push(axios.get(`${FILTER_VALUES_API_URL}max_privacy/`))
    let resultData = await Promise.all(filters)
    let filterVals = {
      'tags': resultData[0].data,
      'mode': resultData[1].data,
      'dataset': resultData[2].data,
      'is_default': resultData[3].data,
      'min_privacy': resultData[4].data,
      'max_privacy': resultData[5].data,
      'search_text': ''
    }
    setFilterValues(filterVals)
    dispatch(setAvailableFilters(JSON.stringify(filterVals)))
    return filterVals
  }

  const fetchViewList = () => {
    if (axiosSource.current) axiosSource.current.cancel()
    let cancelFetchToken = newCancelToken()
    setLoading(true)
    let _additional_filters = ''
    let sortBy = pagination.sortOrder.name ? pagination.sortOrder.name : ''
    let sortDirection = pagination.sortOrder.direction ? pagination.sortOrder.direction : ''

    axios.post(`${VIEW_LIST_URL}?` + `page=${pagination.page + 1}&page_size=${pagination.rowsPerPage}` +
      `&sort_by=${sortBy}&sort_direction=${sortDirection}` +
      `${_additional_filters}`,
      currentFilters,
      {
        cancelToken: cancelFetchToken
      }).then(
      response => {
        setLoading(false)
        setData(response.data.results as ViewTableRowInterface[])
        setTotalCount(response.data.count)
        setUserPermissions(response.data.permissions)
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

  useEffect(() => {
    let dataset
    try {
      dataset = searchParams.get('dataset') ? [searchParams.get('dataset')] : []
    } catch (error: any) {
    }
    if (dataset) {
      setCurrentFilters({...currentFilters, 'dataset': dataset})
      dispatch(setInitialFilters(JSON.stringify({...currentFilters, 'dataset': dataset})))
    }
  }, [searchParams])

  const getExistingFilterValue = (colName: string): string[] => {
    let values: string[] = []
    switch (colName) {
      case 'tags':
        values = currentFilters.tags
        break;
      case 'mode':
        values = currentFilters.mode
        break;
      case 'dataset':
        values = currentFilters.dataset
        break;
      case 'is_default':
        values = currentFilters.is_default
        break;
      case 'min_privacy':
        values = currentFilters.min_privacy
        break;
      case 'max_privacy':
        values = currentFilters.max_privacy
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
        if (columnName === 'dataset') {
          _options.options.filter = true
          // set existing filter values
          _options.options.filterList = getExistingFilterValue(columnName)
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
        } else if (['tags', 'mode', 'is_default', 'min_privacy', 'max_privacy'].includes(columnName)) {
          // set filter values in dropdown
          _options.options.filterOptions = {
            names: filterVals[columnName]
          }
          _options.options.filter = true
          // set existing filter values
          _options.options.filterList = getExistingFilterValue(columnName)
        } else {
          _options.options.filter = false
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
                  onClick={(e) => {
                    e.stopPropagation()
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
    }
    fetchFilterValuesData()
  }, [pagination, currentFilters])

  useEffect(() => {
    fetchViewList()
  }, [pagination, currentFilters])

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
        filter[key as keyof ViewsFilterInterface] = filterList[idx]
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
    setSelectedView(null)
  };

  const open = Boolean(anchorEl);
  const id = open ? 'view-popover' : undefined;

  const handleClose = () => {
    setConfirmationOpen(false)
  }

  const handleDeleteClick = () => {
    setDeleteButtonDisabled(true)
    postData(
      `${DELETE_VIEW_URL}/${selectedView['0']}`, {}
    ).then(
      response => {
        setDeleteButtonDisabled(false)
        fetchViewList()
        setConfirmationOpen(false)
      }
    ).catch(error => {
      setDeleteButtonDisabled(false)
      alert('Error deleting view')
    })
  }

  return (
    <div className="AdminContentMain">
      <AlertDialog open={confirmationOpen} alertClosed={handleClose}
                   alertConfirmed={handleDeleteClick}
                   alertLoading={deleteButtonDisabled}
                   alertDialogTitle={'Delete view'}
                   alertDialogDescription={confirmationText}
                   confirmButtonText='Delete'
                   confirmButtonProps={{color: 'error', autoFocus: true}}
      />
      {
        loading ? <Loading label={'Fetching views'}/> :
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
                      navigate(ViewEditRoute.path + `?id=${rowData[0]}`)
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
        <ViewPopover view={selectedView}/>
      </Popover>
    </div>
  )
}