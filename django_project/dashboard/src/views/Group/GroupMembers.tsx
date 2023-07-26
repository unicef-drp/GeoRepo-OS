import React, { useState, useEffect } from 'react';
import axios from "axios";
import DeleteIcon from "@mui/icons-material/Delete";
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Autocomplete from '@mui/material/Autocomplete';
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Modal from '@mui/material/Modal';
import { debounce } from '@mui/material/utils';
import List, {ActionDataInterface} from "../../components/List";
import Loading from "../../components/Loading";
import {AddButton} from "../../components/Elements/Buttons";
import GroupInterface from '../../models/group';


const COLUMNS = [
    'id',
    'name',
    'username',
    'email',
    'role',
    'is_active'
]

const GROUP_MEMBERS_URL = '/api/group/'
const FETCH_ACTORS_URL = '/api/user-list/'

interface GroupMembersInterface {
    group: GroupInterface;
}

interface AddGroupMemberModalInterface {
    group: GroupInterface;
    onSave: (userId: number) => void,
    onCancel: () => void
}

interface SearchUserInterface {
    id: number;
    name: string;
    role: string;
    username: string;
}

function AddGroupMemberModal(props: AddGroupMemberModalInterface) {
    const [selectedUser, setSelectedUser] = useState<SearchUserInterface>({
        'id': 0,
        'name': '',
        'role': '',
        'username': ''
    })
    const [options, setOptions] = useState<SearchUserInterface[]>([])
    const [inputValue, setInputValue] = useState('')
    const [open, setOpen] = useState(false)
    const [updatedFilter, setUpdatedFilter] = useState(null)
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
                axios.get(`${FETCH_ACTORS_URL}?${_additional_filters}`).then(
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
        if (inputValue === '' && updatedFilter === null) {
            setOptions([])
            return undefined;
        }
        searchActors({input: inputValue}, (results: any) => {
            if (active) {
                if (results) {
                    setOptions(results.data as SearchUserInterface[])
                } else {
                    setOptions([])
                }                
            }
        })
        return () => {
            active = false
        };
    }, [inputValue, searchActors, updatedFilter])

    useEffect(() => {
        if (!open) {
            setOptions([])
        }
    }, [open])

    const saveOnClick = () => {
        props.onSave(selectedUser.id)
    }

    return (
        <Box sx={{p:3}}>
            <Grid container flexDirection={'column'} spacing={2}>
                <Grid item>
                    <Typography variant="h6" >Add User to Group</Typography>
                </Grid>
                <Grid item>
                    <Autocomplete
                        disablePortal={false}
                        id="combo-box-actor"
                        open={open}
                        onOpen={handleOpen}
                        onClose={() => setOpen(false)}
                        options={options}
                        getOptionLabel={(option) => {
                            let _name = option.name ? option.name : ''
                            _name = _name.trim()
                            let _label = _name ? _name : option.username
                            _label = `${_label} (${option.role})`
                            return _label
                        }}
                        renderInput={(params) => 
                            <TextField {...params} label={'User'}
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
                                setSelectedUser(newValue)
                            } else {
                                setSelectedUser({
                                    id: 0,
                                    name: '',
                                    role: '',
                                    username: ''
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
                </Grid>
                    <Grid item>
                        <Grid container flexDirection={'row'} justifyContent={'flex-end'} spacing={1}>
                            <Grid item>
                                <Button
                                    key={0}
                                    color={'primary'}
                                    onClick={saveOnClick}
                                    variant={'contained'}
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
        </Box>
    )
}


export default function GroupMembers(props: GroupMembersInterface) {
    const [members, setMembers] = useState<[]>([])
    const [loading, setLoading] = useState<boolean>(true)
    const [deleteButtonDisabled, setDeleteButtonDisabled] = useState<boolean>(false)
    const [showAddUserConfig, setShowAddUserConfig] = useState(false)

    const fetchGroupMembers = () => {
        setLoading(true)
        axios.get(`${GROUP_MEMBERS_URL}${props.group.id}/user/list`).then(
            response => {
              setLoading(false)
              setMembers(response.data.map((d: any)=>{
                let keys = Object.keys(d)
                for (const key of keys) {
                  if (!(COLUMNS.includes(key))) {
                    delete d[key]
                  }
                }
                return d
              }))
            }
          )
    }

    useEffect(() => {
        fetchGroupMembers()
    }, [props.group.id])


    const actionDeleteButton: ActionDataInterface = {
        field: '',
        name: 'Delete',
        color: 'error',
        icon: <DeleteIcon />,
        isDisabled: (data: any) => {
          return deleteButtonDisabled
        },
        onClick: (data: any) => {
            let userId: number = data['id']
            handleDeleteClick(props.group.id, userId)
        }
      }

    const handleDeleteClick = (groupId: number, userId: number) => {
        setDeleteButtonDisabled(true)
        axios.delete(
            `${GROUP_MEMBERS_URL}${groupId}/user/${userId}/manage/`, {}
        ).then(
            response => {
                setDeleteButtonDisabled(false)
                fetchGroupMembers()
            }
        ).catch(error => {
            setDeleteButtonDisabled(false)
            alert('Error deleting group member!')
        })
    }

    const handleAddUser = (groupId: number, userId: number) => {
        setShowAddUserConfig(false)
        setDeleteButtonDisabled(true)
        axios.post(
            `${GROUP_MEMBERS_URL}${groupId}/user/${userId}/manage/`, {}
        ).then(
            response => {
                setDeleteButtonDisabled(false)
                fetchGroupMembers()
            }
        ).catch(error => {
            setDeleteButtonDisabled(false)
            alert('Error adding new group member!')
        })
    }

    const customColumnHeaderRender = {
        'is_active': (columnMeta: any, handleToggleColumn: Function) => {
            return <span>Is Active</span>
        }
    }

    const addButtonClick = () => {
        setShowAddUserConfig(true)
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <Box sx={{textAlign:'left'}}>
                    <AddButton disabled={loading || deleteButtonDisabled} text={'Add User'} variant={'secondary'}
                        onClick={addButtonClick}/>
                </Box>
                {!loading ?
                    <List
                        pageName={''}
                        listUrl={''}
                        initData={members}
                        selectionChanged={null}
                        actionData={[actionDeleteButton]}
                        customColumnHeaderRender={customColumnHeaderRender}
                    /> : <Loading/>
                }
                <Modal open={showAddUserConfig} onClose={() => setShowAddUserConfig(false)}>
                    <Box className="add-user-modal">
                        <AddGroupMemberModal group={props.group}
                            onCancel={() => setShowAddUserConfig(false)}
                            onSave={(userId: number) => handleAddUser(props.group.id, userId)} />
                    </Box>
                </Modal>
            </Box>
        </Box>
    )

}


