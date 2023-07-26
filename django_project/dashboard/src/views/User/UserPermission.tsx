import React, { useEffect, useState, useRef, useCallback } from "react";
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Autocomplete from '@mui/material/Autocomplete';
import { debounce } from '@mui/material/utils';
import Button from "@mui/material/Button";
import FormControl from '@mui/material/FormControl';
import MenuItem from '@mui/material/MenuItem';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import InputLabel from '@mui/material/InputLabel';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Modal from '@mui/material/Modal';
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import TabPanel, {a11yProps} from '../../components/TabPanel';
import List, {ActionDataInterface} from "../../components/List";
import Loading from "../../components/Loading";
import UserInterface from '../../models/user';
import {AddButton} from "../../components/Elements/Buttons";
import {postData} from "../../utils/Requests";
import {capitalize} from "../../utils/Helpers";
import EmptyTabPanel from "../../components/EmptyTabPanel";
import PrivacyLevel from "../../models/privacy";


interface UserPermissionItemInterface {
    id: number,
    name: string,
    uuid: string,
    permission: string,
    privacy_level: number,
    type?: string,
    object_type: string
}

interface ObjectItemInterface {
    object_type: string,
    name: string,
    uuid: string,
}

interface UserPermissionInterface {
    user: UserInterface
}

interface PermissionListInterface {
    object_type: string,
    user: UserInterface
}

interface PermissionItemModalInterface {
    object_type: string,
    user: UserInterface,
    item?: UserPermissionItemInterface,
    onPermissionUpdated: () => void,
    onCancel: () => void
}

const FETCH_USER_PERMISSION_DETAIL = '/api/user/permission/'
const SAVE_ACTOR_URL = '/api/permission/actors/'
const FETCH_OBJECTS_URL = '/api/permission/objects/'
const ACTORS_PERMISSION_URL = '/api/permission/list/'
const FETCH_PRIVACY_LEVEL_LABELS = '/api/permission/privacy-levels/'

const MODULE_PERMISSIONS: string[] = ['Write']
const DATASET_PERMISSIONS: string[] = ['Read', 'Write', 'Manage', 'Own']
const DATASET_VIEW_PERMISSIONS: string[] = ['Read']

function PermissionItemModal(props: PermissionItemModalInterface) {
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)
    const [isEdit, setIsEdit] = useState(props.item != null)
    const [objects, setObjects] = useState<ObjectItemInterface[]>([])
    const [selectedObject, setSelectedObject] = useState<ObjectItemInterface>(null)
    const [selectedPermission, setSelectedPermission] = useState('')
    const [selectedPrivacyLevel, setSelectedPrivacyLevel] = useState(4)
    // for superadmin, can assign any permissions, so no need to fetch based on user role
    const [availablePerms, setAvailablePerms] = useState<string[]>([])
    const [inputValue, setInputValue] = React.useState('')
    const [open, setOpen] = React.useState(false)
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

    const searchObjects = React.useMemo(
        () =>
          debounce(
            (
              request: { input: string },
              callback: (results?: any) => void,
            ) => {
                let _additional_filters = `search_text=${request.input}`
                if (props.item?.uuid) {
                    _additional_filters = _additional_filters + `&uuid=${props.item.uuid}`
                }
                axios.get(`${FETCH_OBJECTS_URL}${props.object_type}/${props.user.id}/?${_additional_filters}`).then(
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
        let _list =  props.object_type === 'module' ? MODULE_PERMISSIONS :
        props.object_type === 'dataset' ? DATASET_PERMISSIONS : DATASET_VIEW_PERMISSIONS
        setAvailablePerms([..._list])
    }, [props.object_type])

    useEffect(() => {
        if (props.object_type === 'module') {
            setSelectedPermission('Write')
        } else if (props.item) {
            setSelectedPermission(props.item.permission)
            setSelectedPrivacyLevel(props.item.privacy_level)
            setSelectedObject({
                'object_type': props.object_type,
                'name': props.item.name,
                'uuid': props.item.uuid,
            })
        }
    }, [availablePerms])

    useEffect(() => {
        let active = true;
        if (!isEdit && inputValue === '' && updatedFilter === null) {
            setObjects([])
            return undefined;
        }
        searchObjects({input: inputValue}, (results: any) => {
            if (active) {
                if (results) {
                    setObjects(results.data.objects)
                } else {
                    setObjects([])
                }                
            }
        })
        return () => {
            active = false
        };
    }, [inputValue, setObjects, updatedFilter])

    useEffect(() => {
        if (!open) {
            setObjects([])
        } else {
            fetchPrivacyLevelLabels()
        }
    }, [open])

    const saveOnClick = () => {
        setLoading(true)
        let data = {
            'id': props.user.id,
            'name': '',
            'role': '',
            'permission': selectedPermission,
            'privacy_level': selectedPrivacyLevel,
            'editable': false
        }
        let _additional_filters = ''
        postData(`${SAVE_ACTOR_URL}${props.object_type}/${selectedObject.uuid}/?${_additional_filters}`, data).then(
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
                                        options={objects}
                                        getOptionLabel={(option) => {
                                            let _label = option.name ? option.name : ''
                                            return _label
                                        }}
                                        renderInput={(params) => 
                                            <TextField {...params} label={capitalize(props.object_type)}
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
                                                setSelectedObject(newValue)
                                            } else {
                                                setSelectedObject(null)
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
                                        isOptionEqualToValue={(option, value) => option.uuid === value.uuid}
                                    />
                                )}
                                { isEdit && (
                                    <TextField disabled label={capitalize(props.object_type)}
                                        value={`${props.item?.name}`}
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
                                        value={selectedPermission}
                                        label="Permission"
                                        onChange={(event: SelectChangeEvent) => {
                                            setSelectedPermission(event.target.value as string)
                                        }}
                                        disabled={props.object_type === 'module'}
                                    >
                                        { availablePerms.filter((value) => {
                                            // if selected actor is viewer, then only returns Read permission only
                                            if (props.user.role === 'Viewer') {
                                                return value === 'Read'
                                            }
                                            return true
                                        }).map((value, index) => {
                                            if (props.object_type === 'module' && value === 'Write') {
                                                return <MenuItem key={index} value={value}>{value} (Create new dataset)</MenuItem>
                                            }
                                            return <MenuItem key={index} value={value}>{value}</MenuItem>
                                        })
                                        }
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid item md={4} xs={4}>
                                {(props.object_type === 'dataset' || props.object_type === 'datasetview') && selectedPermission === 'Read' && (
                                    <FormControl sx={{width:'100%'}}>
                                        <InputLabel id="privacy-level-select-label">Privacy Level</InputLabel>
                                        <Select
                                            labelId="privacy-level-select-label"
                                            id="privacy-level-select"
                                            value={'' +selectedPrivacyLevel}
                                            label="Privacy Level"
                                            onChange={(event: SelectChangeEvent) => {
                                                setSelectedPrivacyLevel(parseInt(event.target.value as string))
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
                                    disabled={selectedObject === null || selectedPermission === ''}
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

function PermissionList(props: PermissionListInterface) {
    const [loading, setLoading] = useState<boolean>(false)
    const [excludedColumns, setExcludedColumns] = useState<string[]>([])
    const [data, setData] = useState<UserPermissionItemInterface[]>([])
    const [showAddPermissionConfig, setShowAddPermissionConfig] = useState(false)
    const [selectedItem, setSelectedItem] = useState<UserPermissionItemInterface>(null)
    const navigate = useNavigate()
    const customOptions = {
        'uuid': {
            'display': false,
            'filter': false
        },
        'object_type': {
            'display': false,
            'filter': false
        },
        'privacy_level': {
            'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
                let _privacy_label = tableMeta.rowData.length > 7 ? tableMeta.rowData[7] : ''
                return `${value}${_privacy_label ? ' - ' + _privacy_label : ''}`
            }
        }
    }

    const fetchPermissionList = () => {
        setLoading(true)
        axios.get(`${FETCH_USER_PERMISSION_DETAIL}${props.object_type}/${props.user.id}/`).then(
            response => {
              setLoading(false)
              setData(response.data)
              if (props.object_type === 'module') {
                setExcludedColumns(['privacy_level', 'type'])
              } else if (props.object_type === 'dataset') {
                setExcludedColumns(['type', 'privacy_label'])
              } else {
                setExcludedColumns(['privacy_label'])
              }
            }
          ).catch((error) => {
            if (error.response) {
              if (error.response.status == 403) {
                // TODO: use better way to handle 403
                navigate('/invalid_permission')
              }
            }
          })
    }

    useEffect(() => {
        if (props.object_type && props.user?.id) {
            fetchPermissionList()
        }
    }, [props.user, props.object_type])


    const addButtonClick = () => {
        setShowAddPermissionConfig(true)
    }

    const onPermissionItemModalClosed = () => {
        setShowAddPermissionConfig(false)
        setSelectedItem(null)
    }

    const onPermissionUpdated = () => {
        onPermissionItemModalClosed()
        fetchPermissionList()
    }

    const actionEditButton: ActionDataInterface = {
        field: '',
        name: 'Edit',
        getName: (data: any) => {
            if (props.object_type === 'datasetview' && data.type === 'Inherited') {
                return 'Inherited permissions cannot be edited'
            }
            return 'Edit'
        },
        icon: <EditIcon />,
        isDisabled: (data: any) => {
            if (props.object_type === 'datasetview' && data.type === 'Inherited') {
                return true
            }
            return false
        },
        onClick: (data: any) => {
          setSelectedItem(data)
          setShowAddPermissionConfig(true)
        }
      }

      const actionDeleteButton: ActionDataInterface = {
        field: '',
        name: 'Delete',
        getName: (data: any) => {
            if (props.object_type === 'datasetview' && data.type === 'Inherited') {
                return 'Inherited permissions cannot be removed'
            }
            return 'Delete'
        },
        color: 'error',
        icon: <DeleteIcon />,
        isDisabled: (data: any) => {
            if (props.object_type === 'datasetview' && data.type === 'Inherited') {
                return true
            }
            return false
        },
        onClick: (data: any) => {
            setLoading(true)
            let _additional_filters = ''
            axios.delete(`${ACTORS_PERMISSION_URL}${props.object_type}/${data.uuid}/identifier/${props.user.id}/?` +
                `${_additional_filters}`).then(
                response => {
                    setLoading(false)
                    fetchPermissionList()
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
      }

    return (
        <Box style={{display:'flex', flex: 1, flexDirection: 'column', flexGrow: 1, height: '100%'}}>
            {
            loading ? <Loading label={'Fetching data'}/> :
            <Grid container flexDirection={'column'} alignItems={'flex-start'} sx={{width: '100%', height: '100%', marginTop: '10px'}}>
                <Grid item>
                    { !(props.object_type === 'module' && props.user.role === 'Viewer') &&
                        <AddButton disabled={loading} text={'Add'} variant={'secondary'}
                            onClick={addButtonClick}/>
                    }
                </Grid>
                <Grid item sx={{display:'flex', flex: 1, flexDirection: 'column', flexGrow: 1, width: '100%', height: '100%'}}>
                    <List
                        pageName={'Permissions'}
                        listUrl={''}
                        initData={data as any[]}
                        selectionChanged={null}
                        customOptions={customOptions}
                        excludedColumns={excludedColumns}
                        actionData={[actionEditButton, actionDeleteButton]}
                    />
                </Grid>
            </Grid>   
          }
            <Modal open={showAddPermissionConfig} onClose={() => onPermissionItemModalClosed()}>
                <Box className="permission-modal">
                    <PermissionItemModal object_type={props.object_type}
                        user={props.user} onPermissionUpdated={onPermissionUpdated}
                        item={selectedItem} onCancel={() => onPermissionItemModalClosed()} />
                </Box>
            </Modal>
        </Box>
    )
}

export default function UserPermission(props: UserPermissionInterface) {
    const [tabSelected, setTabSelected] = useState(0)

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabSelected(newValue)
    }

    return (
        <Box style={{display:'flex', flex: 1, flexDirection: 'column', flexGrow: 1, height: '100%'}}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="Permission Tab">
                    <Tab key={0} label={'Module'} {...a11yProps(0)} />
                    <Tab key={1} label={'Dataset'} {...a11yProps(1)} />
                    <Tab key={2} label={'View'} {...a11yProps(2)} />
                </Tabs>
            </Box>
            <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel key={0} value={tabSelected} index={0} noPadding>
                    { props.user.role === 'Creator' ?           
                        <PermissionList object_type={'module'} user={props.user} /> :
                        <EmptyTabPanel text='Only creator users can manage modules' />
                    }
                </TabPanel>
                <TabPanel key={1} value={tabSelected} index={1} noPadding>
                    <PermissionList object_type={'dataset'} user={props.user} />
                </TabPanel>
                <TabPanel key={2} value={tabSelected} index={2} noPadding>
                    <PermissionList object_type={'datasetview'} user={props.user} />
                </TabPanel>
            </Grid>
        </Box>
    )

}
