import React, { useEffect, useState, useRef, useCallback } from "react";
import {useNavigate} from "react-router-dom";
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import FilterAlt from '@mui/icons-material/FilterAlt';
import axios from "axios";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Button from "@mui/material/Button";
import FormControl from '@mui/material/FormControl';
import MenuItem from '@mui/material/MenuItem';
import Modal from '@mui/material/Modal';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import Autocomplete from '@mui/material/Autocomplete';
import InputLabel from '@mui/material/InputLabel';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { debounce } from '@mui/material/utils';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import TabPanel, {a11yProps} from '../../components/TabPanel';
import Loading from "../../components/Loading";
import PaginationInterface, { getDefaultPagination, rowsPerPageOptions } from '../../models/pagination';
import ResizeTableEvent from "../../components/ResizeTableEvent"
import {TABLE_OFFSET_HEIGHT} from '../../components/List'
import Scrollable from '../../components/Scrollable';
import {AddButton} from "../../components/Elements/Buttons";
import '../../styles/Permission.scss';
import {postData} from "../../utils/Requests";
import PrivacyLevel from "../../models/privacy";

interface PermissionDetailInterface{
    objectType: string,
    objectUuid: string,
    isReadOnly?: boolean
}

interface PermissionItemInterface {
    id: number,
    name: string,
    role?: string,
    permission: string,
    privacy_level: number,
    type?: string,
    editable: boolean,
    privacy_label?: string
}

interface PermissionItemModalInterface {
    item?: PermissionItemInterface,
    objectType: string,
    objectUuid: string,
    isGroup: boolean,
    onPermissionUpdated: () => void,
    onCancel: () => void
}

interface PermissionDetailTabInterface {
    objectType: string,
    objectUuid: string,
    isGroup: boolean,
    isReadOnly?: boolean
}

interface TableFilterInterface {
    search_text: string
}

interface ActorItemInterface {
    id: number,
    name: string,
    role?: string
}

const ACTORS_PERMISSION_URL = '/api/permission/list/'
// can return list of user or group
const FETCH_ACTORS_URL = '/api/permission/actors/'
const FETCH_AVAILABLE_PERMISSIONS_URL = '/api/permission/object/'
const FETCH_PRIVACY_LEVEL_LABELS = '/api/permission/privacy-levels/'

const FilterIcon: any = FilterAlt

const USER_COLUMNS = [
    'id',
    'name',
    'role',
    'permission',
    'privacy_level',
    'type',
    'editable',
    'privacy_label'
]

const GROUP_COLUMNS = [
    'id',
    'name',
    'permission',
    'privacy_level',
    'type',
    'editable',
    'privacy_label'
]

function PermissionList(props: PermissionDetailTabInterface) {
    const [loading, setLoading] = useState(true)
    const [columns, setColumns] = useState<any>([])
    const [data, setData] = useState<PermissionItemInterface[]>([])
    const [userPermissions, setUserPermissions] = useState<string[]>([])
    const [selectedItem, setSelectedItem] = useState<PermissionItemInterface>(null)
    const [totalCount, setTotalCount] = useState<number>(0)
    const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
    const [filter, setFilter] = useState<TableFilterInterface>({
        search_text: ''
    })
    const axiosSource = useRef(null)
    const newCancelToken = useCallback(() => {
        axiosSource.current = axios.CancelToken.source();
        return axiosSource.current.token;
    }, [])
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)
    const [showAddPermissionConfig, setShowAddPermissionConfig] = useState(false)
    const navigate = useNavigate()

    const fetchPermissionList = (isGroup: boolean) => {
        if (axiosSource.current) axiosSource.current.cancel()
        let cancelFetchToken = newCancelToken()
        setLoading(true)
        let _additional_filters = ''
        if (isGroup) {
            _additional_filters = _additional_filters + '&is_group=true'
        }
        for (const [key, value] of Object.entries(filter)) {
            if (value) {
                _additional_filters = _additional_filters + `&${key}=${value}`
            }
        }
        axios.get(`${ACTORS_PERMISSION_URL}${props.objectType}/${props.objectUuid}/?` +
        `page=${pagination.page+1}&page_size=${pagination.rowsPerPage}`+
            `${_additional_filters}`,
        {
            cancelToken: cancelFetchToken
        }).then(
            response => {
                setLoading(false)
                setData(response.data.results as PermissionItemInterface[])
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
        let _is_read_only = props.isReadOnly
        if (columns.length === 0) {
            let _init_columns = props.isGroup ? GROUP_COLUMNS : USER_COLUMNS
            let _columns = _init_columns.map((column_name) => {
                let _options:any = {
                    name: column_name,
                    label: column_name.charAt(0).toUpperCase() + column_name.slice(1).replaceAll('_', ' '),
                    options: {
                        display: column_name !== 'id' && column_name !== 'editable' && column_name !== 'privacy_label'
                    }
                }
                if (props.objectType === 'module' && column_name === 'privacy_level') {
                    _options['options']['display'] = false
                } else if (column_name === 'privacy_level') {
                    _options['options']['customBodyRender'] = (value: any, tableMeta: any, updateValue: any) => {
                        let _privacy_label = ''
                        if (props.isGroup) {
                            _privacy_label = tableMeta.rowData.length > 6 ? tableMeta.rowData[6] : ''
                        } else {
                            _privacy_label = tableMeta.rowData.length > 7 ? tableMeta.rowData[7] : ''
                        }
                        return `${value}${_privacy_label ? ' - ' + _privacy_label : ''}`
                    }
                }
                if (props.objectType === 'module' && column_name === 'permission') {
                    _options['options']['customBodyRender'] = (value: any, tableMeta: any, updateValue: any) => {
                        return value + ' (Create new dataset)'
                    }
                }
                if (props.objectType !== 'datasetview' && column_name === 'type') {
                    _options['options']['display'] = false
                }
                return _options
            })
            _columns.push({
                name: '',
                options: {
                    customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
                        let _is_editable = props.isGroup ? tableMeta.rowData[5] : tableMeta.rowData[6]
                        return (
                            <div className="TableActionContent">
                                {/* disabled/remove edit button for module since only option is to remove the row */}
                                {props.objectType !== 'module' && (
                                    <IconButton
                                        key={0}
                                        className='PermissionActionButton'
                                        title={props.objectType === 'datasetview' && !_is_editable ? 'Inherited permissions cannot be edited' : 'Edit'}
                                        disabled={!_is_editable || _is_read_only}
                                        color={'primary'}
                                        onClick={(e:any) => {
                                            e.stopPropagation();
                                            onEditClick(tableMeta)
                                        }}>
                                            <EditIcon />
                                    </IconButton>
                                )}
                                <IconButton
                                    key={1}
                                    className='PermissionActionButton'
                                    title={props.objectType === 'datasetview' && !_is_editable ? 'Inherited permissions cannot be removed' : 'Delete'}
                                    disabled={!_is_editable || _is_read_only}
                                    color={'error'}
                                    onClick={(e:any) => {
                                        e.stopPropagation();
                                        onDeleteClick(tableMeta)
                                    }}>
                                        <DeleteIcon />
                                </IconButton>
                            </div>
                        )
                    }
                }
            })
            setColumns(_columns)
        }
    }, [])

    useEffect(() => {
        fetchPermissionList(props.isGroup)
    }, [pagination, filter])

    const onTableChangeState = (action:string, tableState:any) => {
        switch (action) {
            case 'changePage':
                setPagination({
                    ...pagination,
                    page: tableState.page
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

    const handleSearchOnChange = (search_text: string) => {
        setPagination({
            ...pagination,
            page: 0,
            sortOrder: {}
        })
        setFilter({...filter, 'search_text':search_text})
    }

    const addButtonClick = () => {
        setShowAddPermissionConfig(true)
    }

    const onDeleteClick = (tableMeta: any) => {
        setLoading(true)
        let _additional_filters = ''
        if (props.isGroup) {
            _additional_filters = _additional_filters + '&is_group=true'
        }
        axios.delete(`${ACTORS_PERMISSION_URL}${props.objectType}/${props.objectUuid}/identifier/${tableMeta.rowData[0]}/?` +
            `${_additional_filters}`).then(
            response => {
                setLoading(false)
                fetchPermissionList(props.isGroup)
            }
        ).catch(error => {
            console.log(error)
            setLoading(false)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                } else if (error.response.data) {
                    let _error_message = 'Error saving permission!'
                    let _error = error.response.data
                    if (_error && Array.isArray(_error)) {
                        _error_message = _error[0]
                    } else if (_error && 'detail' in _error) {
                        _error_message = _error['detail']
                    }
                    alert(_error_message)
                }
            } else {
                let _error_message = 'Error when removing permission!'
                if (error && Array.isArray(error)) {
                    _error_message = error[0]
                } else if (error && 'detail' in error) {
                    _error_message = error['detail']
                }
                alert(_error_message)
            }
        })
    }

    const onEditClick = (tableMeta: any) => {
        if (props.isGroup) {
            setSelectedItem({
                'id': tableMeta.rowData[0],
                'name': tableMeta.rowData[1],
                'role': '',
                'permission': tableMeta.rowData[2],
                'privacy_level': tableMeta.rowData[3],
                'type': tableMeta.rowData[4],
                'editable': tableMeta.rowData[5],
            })
        } else {
            setSelectedItem({
                'id': tableMeta.rowData[0],
                'name': tableMeta.rowData[1],
                'role': tableMeta.rowData[2],
                'permission': tableMeta.rowData[3],
                'privacy_level': tableMeta.rowData[4],
                'type': tableMeta.rowData[5],
                'editable': tableMeta.rowData[6],
            })
        }
        setShowAddPermissionConfig(true)
    }

    const onPermissionItemModalClosed = () => {
        setShowAddPermissionConfig(false)
        setSelectedItem(null)
    }

    const onPermissionUpdated = () => {
        onPermissionItemModalClosed()
        fetchPermissionList(props.isGroup)
    }

    let addButtonTitle = props.isGroup ? 'Add Group':'Add User'
    if (props.objectType === 'datasetview') {
        addButtonTitle = props.isGroup ? 'Add External Group':'Add External User'
    }

    return (
        <Scrollable>
            <Grid container flexDirection={'column'} spacing={2} flexWrap='nowrap' sx={{flexGrow: 1, width: '100%'}}>
                <Grid item ref={ref} sx={{flexGrow:1, width: '100%'}}>
                    {!loading && <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                        onResize={(clientHeight:number) => {
                            setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)
                        }} />}
                    {loading ? <Loading/> :
                        <MUIDataTable columns={columns} data={data}
                            title={<Box sx={{textAlign:'left'}}>
                                <AddButton disabled={loading || props.isReadOnly} text={addButtonTitle} variant={'secondary'}
                                    onClick={addButtonClick}/>
                            </Box>}
                            options={{
                                serverSide: true,
                                page: pagination.page,
                                count: totalCount,
                                rowsPerPage: pagination.rowsPerPage,
                                rowsPerPageOptions: rowsPerPageOptions,
                                sortOrder: pagination.sortOrder as MUISortOptions,
                                jumpToPage: true,
                                onTableChange: (action:string, tableState:any) => onTableChangeState(action, tableState),
                                customSearchRender: debounceSearchRender(500),
                                selectableRows: 'none',
                                selectableRowsOnClick: true,
                                expandableRows: false,
                                fixedHeader: true,
                                fixedSelectColumn: false,
                                tableBodyHeight: `${tableHeight}px`,
                                tableBodyMaxHeight: `${tableHeight}px`,
                                textLabels: {
                                    body: {
                                        noMatch: loading ?
                                            <Loading /> :
                                            'Sorry, there is no matching data to display',
                                    },
                                },
                                onSearchChange: (searchText: string) => {
                                    handleSearchOnChange(searchText)
                                },
                                searchText: filter.search_text,
                                searchOpen: (filter.search_text != null && filter.search_text.length > 0),
                                filter: false,
                                sort: false
                        }}
                        components={{
                            icons: {
                                FilterIcon
                            }
                        }}/>
                    }
                    <Modal open={showAddPermissionConfig} onClose={() => onPermissionItemModalClosed()}>
                        <Box className="permission-modal">
                            <PermissionItemModal isGroup={props.isGroup} objectType={props.objectType}
                                objectUuid={props.objectUuid} onPermissionUpdated={onPermissionUpdated}
                                item={selectedItem}
                                onCancel={() => onPermissionItemModalClosed()} />
                        </Box>
                    </Modal>
                </Grid>
            </Grid>
        </Scrollable>
    )
}

function PermissionItemModal(props: PermissionItemModalInterface) {
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState<PermissionItemInterface>(props.item || {
        'id': 0,
        'name': '',
        'role': '',
        'permission': '',
        'privacy_level': 4,
        'editable': false
    })
    const [isEdit, setIsEdit] = useState(props.item && props.item.permission !== '')
    const [actorsFiltered, setActorsFiltered] = useState<ActorItemInterface[]>([])
    const [availablePerms, setAvailablePerms] = useState(props.item && props.item.permission !== '' ? [props.item.permission] : [])
    const navigate = useNavigate()
    const [inputValue, setInputValue] = useState('')
    const [open, setOpen] = useState(false)
    const [updatedFilter, setUpdatedFilter] = useState(null)
    const [privacyLevelLabels, setPrivacyLevelLabels] = useState<PrivacyLevel>({})
    const handleOpen = () => {
        if (inputValue.length > 0) {
            setOpen(true)
        } else {
            setUpdatedFilter(new Date())
            setOpen(true)
        }
    }

    const searchActors = React.useMemo(
        () =>
          debounce(
            (
              request: { input: string },
              callback: (results?: any) => void,
            ) => {
                let _additional_filters = `search_text=${request.input}`
                if (props.isGroup) {
                    _additional_filters = _additional_filters + '&is_group=true'
                }
                if (props.item && props.item.id) {
                    _additional_filters = _additional_filters + `&id=${props.item.id}`
                }
                axios.get(`${FETCH_ACTORS_URL}${props.objectType}/${props.objectUuid}/?${_additional_filters}`).then(
                    response => {
                        callback(response)
                    }
                ).catch(error => {
                    console.log(error)
                    callback(null)
                })
            },
            400,
          ),
        [],
    )

    useEffect(() => {
        let active = true;
        if (!isEdit && inputValue === '' && updatedFilter === null) {
            setActorsFiltered([])
            return undefined;
        }
        searchActors({input: inputValue}, (results: any) => {
            if (active) {
                if (results) {
                    setActorsFiltered(results.data.actors)
                    if (props.objectType === 'module') {
                        // set default for module since there is only write permission
                        setData({
                            ...data,
                            permission: 'Write'
                        })
                    }
                } else {
                    setActorsFiltered([])
                }                
            }
        })
        return () => {
            active = false
        };
    }, [inputValue, searchActors, updatedFilter])

    useEffect(() => {
        if (!open) {
            setActorsFiltered([])
        }
    }, [open])

    const fetchAvailablePermissions = () => {
        setLoading(true)
        let _additional_filters = ''
        if (props.isGroup) {
            _additional_filters = _additional_filters + '&is_group=true'
        }
        axios.get(`${FETCH_AVAILABLE_PERMISSIONS_URL}${props.objectType}/${props.objectUuid}/?${_additional_filters}`).then(
            response => {
                setLoading(false)
                setAvailablePerms(response.data.permissions)
            }
        ).catch(error => {
            setLoading(false)
            console.log(error)
        })
    }

    const fetchPrivacyLevelLabels = () => {
        axios.get(`${FETCH_PRIVACY_LEVEL_LABELS}`).then(
            response => {
                if (response.data) {
                    setPrivacyLevelLabels(response.data as PrivacyLevel)
                }
            }
        ).catch(error => {
            console.log(error)
        })
    }

    useEffect(() => {
        fetchAvailablePermissions()
        fetchPrivacyLevelLabels()
    }, [])

    const saveOnClick = () => {
        setLoading(true)
        let _additional_filters = ''
        if (props.isGroup) {
            _additional_filters = _additional_filters + '&is_group=true'
        }
        postData(`${FETCH_ACTORS_URL}${props.objectType}/${props.objectUuid}/?${_additional_filters}`,data).then(
            response => {
                setLoading(false)
                props.onPermissionUpdated()
            }
        ).catch(error => {
            setLoading(false)
            console.log(error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                } else if (error.response.data) {
                    let _error_message = 'Error saving permission!'
                    let _error = error.response.data
                    if (_error && Array.isArray(_error)) {
                        _error_message = _error[0]
                    } else if (_error && 'detail' in _error) {
                        _error_message = _error['detail']
                    }
                    alert(_error_message)
                }
            } else {
                let _error_message = 'Error saving permission!'
                if (error && Array.isArray(error)) {
                    _error_message = error[0]
                } else if (error && 'detail' in error) {
                    _error_message = error['detail']
                }
                alert(_error_message)
            }
        })
    }

    return (
        <Box sx={{p:3}}>
            { loading && ( <Loading/> )}
            { !loading && ( 
                <Grid container flexDirection={'column'} spacing={2}>
                    <Grid item>
                        <Typography variant="h6" >{ isEdit ? 'Edit Permission' : 'Add Permission' }</Typography>
                    </Grid>
                    <Grid item>
                        <Grid container flexDirection={'row'} flexGrow={1} spacing={1}>
                            <Grid item md={4} xs={4}>
                                { !isEdit && (
                                    <Autocomplete
                                        disablePortal={false}
                                        id="combo-box-actor"
                                        open={open}
                                        onOpen={handleOpen}
                                        onClose={() => setOpen(false)}
                                        options={actorsFiltered}
                                        getOptionLabel={(option) => {
                                            let _label = option.name ? option.name : ''
                                            if (!props.isGroup) {
                                                _label = `${_label} (${option.role})`
                                            }
                                            return _label
                                        }}
                                        renderInput={(params) => 
                                            <TextField {...params} label={props.isGroup?'Group':'User'}
                                            InputProps={{
                                                ...params.InputProps,
                                                style: {
                                                    paddingTop: '16.5px',
                                                    paddingBottom: '16.5px'
                                                }
                                            }} />
                                        }
                                        onChange={(event, newValue) => {
                                            if (newValue) {
                                                setData({
                                                    ...data,
                                                    id: newValue.id,
                                                    name: newValue.name,
                                                    role: newValue.role
                                                })
                                            } else {
                                                setData({
                                                    ...data,
                                                    id: 0,
                                                    name: '',
                                                    role: ''
                                                })
                                            }            
                                        }}
                                        onInputChange={(event, newInputValue) => {
                                            setInputValue(newInputValue);
                                            if (newInputValue.length > 0) {
                                                setOpen(true);
                                            } else {
                                                setOpen(false);
                                            }
                                        }}
                                        filterOptions={(x) => x}
                                        isOptionEqualToValue={(option, value) => option.id === value.id}
                                    />
                                )}
                                { isEdit && (
                                    <TextField disabled label={props.isGroup?'Group':'User'}
                                        value={`${props.item.name} ${!props.isGroup ? '(' + props.item.role + ')':''}`}
                                        fullWidth
                                    />
                                )}
                            </Grid>
                            <Grid item md={4} xs={4}>
                                <FormControl sx={{width:'100%'}}>
                                    <InputLabel id="permission-select-label">Permission</InputLabel>
                                    <Select
                                        labelId="permission-select-label"
                                        id="permission-select"
                                        value={data.permission}
                                        label="Permission"
                                        onChange={(event: SelectChangeEvent) => {
                                            setData({
                                                ...data,
                                                permission: event.target.value as string
                                            })
                                        }}
                                        disabled={props.objectType === 'module'}
                                    >
                                        { availablePerms.filter((value) => {
                                            // if selected actor is viewer, then only returns Read permission only
                                            if (!props.isGroup && data.role === 'Viewer') {
                                                return value === 'Read'
                                            }
                                            return true
                                        }).map((value, index) => {
                                            if (props.objectType === 'module' && value === 'Write') {
                                                return <MenuItem key={index} value={value}>{value} (Create new dataset)</MenuItem>
                                            }
                                            return <MenuItem key={index} value={value}>{value}</MenuItem>
                                        })
                                        }
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid item md={4} xs={4}>
                                {(props.objectType === 'dataset' || props.objectType === 'datasetview') && data.permission === 'Read' && (
                                    <FormControl sx={{width:'100%'}}>
                                        <InputLabel id="privacy-level-select-label">Privacy Level</InputLabel>
                                        <Select
                                            labelId="privacy-level-select-label"
                                            id="privacy-level-select"
                                            value={'' +data.privacy_level}
                                            label="Privacy Level"
                                            onChange={(event: SelectChangeEvent) => {
                                                setData({
                                                    ...data,
                                                    privacy_level: parseInt(event.target.value as string)
                                                })
                                            }}
                                        >
                                            <MenuItem value={1}>{`1${privacyLevelLabels[1] ? ' - ' + privacyLevelLabels[1] : ''}`}</MenuItem>
                                            <MenuItem value={2}>{`2${privacyLevelLabels[2] ? ' - ' + privacyLevelLabels[2] : ''}`}</MenuItem>
                                            <MenuItem value={3}>{`3${privacyLevelLabels[3] ? ' - ' + privacyLevelLabels[3] : ''}`}</MenuItem>
                                            <MenuItem value={4}>{`4${privacyLevelLabels[4] ? ' - ' + privacyLevelLabels[4] : ''}`}</MenuItem>
                                        </Select>
                                    </FormControl>
                                )}
                            </Grid>
                        </Grid>
                    </Grid>
                    <Grid item>
                        <Grid container flexDirection={'row'} justifyContent={'flex-end'} spacing={1}>
                            <Grid item>
                                <Button
                                    key={0}
                                    color={'primary'}
                                    onClick={saveOnClick}
                                    variant={'contained'}
                                    disabled={data.id === 0 || data.permission === ''}
                                    sx={{minWidth: '82px'}}>Save
                                </Button>
                            </Grid>
                            <Grid item>
                                <Button
                                    key={0}
                                    onClick={props.onCancel}
                                    variant={'outlined'}
                                    sx={{minWidth: '82px'}}>Cancel
                                </Button>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
             )}
        </Box>
    )
}

export default function PermissionDetail(props: PermissionDetailInterface) {
    const [tabSelected, setTabSelected] = useState(0)

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabSelected(newValue)
    }

    return (
        <Box style={{display:'flex', flex: 1, flexDirection: 'column', flexGrow: 1, height: '100%'}}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="Permission Tab">
                    <Tab key={0} label={'User'} {...a11yProps(0)} />
                    <Tab key={1} label={'Group'} {...a11yProps(1)} disabled={props.objectType==='module'} />
                </Tabs>
            </Box>
            <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel key={0} value={tabSelected} index={0} noPadding>
                    <PermissionList objectType={props.objectType} objectUuid={props.objectUuid} isGroup={false} isReadOnly={props.isReadOnly} />
                </TabPanel>
                <TabPanel key={1} value={tabSelected} index={1} noPadding>
                    <PermissionList objectType={props.objectType} objectUuid={props.objectUuid} isGroup={true} isReadOnly={props.isReadOnly} />
                </TabPanel>
            </Grid>
        </Box>
    )
}

