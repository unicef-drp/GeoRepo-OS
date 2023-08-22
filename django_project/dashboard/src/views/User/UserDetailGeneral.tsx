import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import MenuItem from '@mui/material/MenuItem';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import UserInterface from '../../models/user';
import Loading from "../../components/Loading";
import AlertMessage from '../../components/AlertMessage';
import {putData} from "../../utils/Requests";
import AlertDialog from '../../components/AlertDialog';
import Scrollable from "../../components/Scrollable";

interface UserDetailGeneralInterface {
    user: UserInterface,
    isUserProfile: boolean,
    onUserUpdated: () => void
}

const FETCH_USER_DETAIL_URL = '/api/user/'

const ROLE_TYPES = [
    'Viewer',
    'Creator',
    'Admin'
]

export default function UserDetailGeneral(props: UserDetailGeneralInterface) {
    const [loading, setLoading] = useState(false)
    const [role, setRole] = useState('')
    const [firstName, setFirstName] = useState(props.user?.first_name)
    const [lastName, setLastName] = useState(props.user?.last_name)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [alertOpen, setAlertOpen] = useState<boolean>(false)
    const [alertLoading, setAlertLoading] = useState<boolean>(false)
    const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
    const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
    const navigate = useNavigate()

    useEffect(() => {
        if (props.user) {
            setRole(props.user.role)
            setFirstName(props.user.first_name)
            setLastName(props.user.last_name)
        }
    }, [props.user])

    const updateUserDetail = (role: string, isActive: boolean) => {
        setLoading(true)
        setAlertLoading(true)
        putData(
            `${FETCH_USER_DETAIL_URL}${props.user.id}/`,
            {
                'first_name': firstName,
                'last_name': lastName,
                'role': role,
                'is_active': isActive
            }
        ).then(
            response => {
                setLoading(false)
                setAlertOpen(false)
                setAlertLoading(false)
                setAlertMessage('Successfully updating user!')
            }
        ).catch(error => {
            setLoading(false)
            setAlertOpen(false)
            setAlertLoading(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                alert('Error updating user!')
            }
        })
    }

    const toggleUserStatus = () => {
        let _title = props.user.is_active ? 'Deactivate this user?' : 'Activate this user?'
        let _desc = props.user.is_active ? 'Are you sure you want to deactivate this user?' : 'Are you sure you want to activate this user?'
        setAlertDialogTitle(_title)
        setAlertDialogDescription(_desc)
        setAlertOpen(true)
    }

    const handleSaveClick = () => {
        updateUserDetail(role, props.user.is_active)
    }

    const handleAlertCancel = () => {
        setAlertOpen(false)
    }

    const alertConfirmed = () => {
        updateUserDetail(role, !props.user.is_active)
    }

    return (
        <Scrollable>
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                    <AlertMessage message={alertMessage} onClose={() => {
                        props.onUserUpdated()
                        setAlertMessage('')
                    }} />
                    <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                            alertConfirmed={alertConfirmed}
                            alertLoading={alertLoading}
                            alertDialogTitle={alertDialogTitle}
                            alertDialogDescription={alertDialogDescription} />
                    <div className='FormContainer'>
                        <FormControl className='FormContent'>
                            <Grid container columnSpacing={2} rowSpacing={2}>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Username</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <TextField
                                        disabled={true}
                                        id="input_username"
                                        hiddenLabel={true}
                                        type={"text"}
                                        value={props.user.username}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>First Name</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <TextField
                                        id="input_first_name"
                                        hiddenLabel={true}
                                        type={"text"}
                                        value={firstName}
                                        onChange={(e) => setFirstName(e.target.value)}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Last Name</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <TextField
                                        id="input_last_name"
                                        hiddenLabel={true}
                                        type={"text"}
                                        value={lastName}
                                        onChange={(e) => setLastName(e.target.value)}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Email</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <TextField
                                        disabled={true}
                                        id="input_email"
                                        hiddenLabel={true}
                                        type={"text"}
                                        value={props.user.email}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Joined Date</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <TextField
                                        disabled={true}
                                        id="input_joined_date"
                                        hiddenLabel={true}
                                        type={"date"}
                                        value={props.user.joined_date}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Status</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <TextField
                                        disabled={true}
                                        id="input_status"
                                        hiddenLabel={true}
                                        type={"text"}
                                        value={props.user.is_active ? 'Active' : 'Inactive'}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Last Login</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <TextField
                                        disabled={true}
                                        id="input_last_login"
                                        hiddenLabel={true}
                                        type={"datetime-local"}
                                        value={props.user.last_login}
                                        sx={{ width: '100%' }}
                                    />
                                </Grid>
                            </Grid>
                            <Divider variant="middle" />
                            <Grid container columnSpacing={2} rowSpacing={2} sx={{paddingTop: '1em'}}>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Role</Typography>
                                </Grid>
                                <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                    <Select
                                        labelId="roles-select-label"
                                        id="roles-select"
                                        value={role}
                                        onChange={(event: SelectChangeEvent) => {
                                            setRole(event.target.value as string)
                                        }}
                                        disabled={props.user.id === (window as any).user_id || props.isUserProfile}
                                    >
                                        { ROLE_TYPES.map((value, index) => {
                                            return <MenuItem key={index} value={value}>{value}</MenuItem>
                                        })}
                                    </Select>
                                </Grid>
                            </Grid>
                            <Grid container columnSpacing={2} rowSpacing={2} sx={{paddingTop: '1em'}} flexDirection={'row'} justifyContent={'space-between'}>
                                <Grid item>
                                    { !props.isUserProfile && 
                                        <div className='button-container'>
                                            <Button
                                                variant={"contained"}
                                                color={ props.user.is_active ? 'error' : 'primary' }
                                                disabled={loading}
                                                onClick={toggleUserStatus}>
                                                <span style={{ display: 'flex' }}>
                                                { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { props.user.is_active ? 'Deactivate' : 'Activate' }</span>
                                            </Button>
                                        </div>
                                    }
                                </Grid>
                                <Grid item>
                                    <div className='button-container'>
                                        <Button
                                            variant={"contained"}
                                            disabled={loading}
                                            onClick={handleSaveClick}>
                                            <span style={{ display: 'flex' }}>
                                            { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Save" }</span>
                                        </Button>
                                    </div>
                                </Grid>
                            </Grid>
                        </FormControl>
                    </div>
                </Box>
            </Box>
        </Scrollable>
    )
}