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
import {postData} from "../../utils/Requests";
import AlertDialog from '../../components/AlertDialog';

interface UserCreateGeneralInterface {
    onUserCreated: (newValue: number) => void
}

const ADD_USER_API = '/api/user/'

const ROLE_TYPES = [
    'Viewer',
    'Creator',
    'Admin'
]

export default function UserCreateGeneral(props: UserCreateGeneralInterface) {
    const [loading, setLoading] = useState(false)
    const [role, setRole] = useState('')
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [alertOpen, setAlertOpen] = useState<boolean>(false)
    const [alertLoading, setAlertLoading] = useState<boolean>(false)
    const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
    const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
    const navigate = useNavigate()
    //
    // useEffect(() => {
    //     if (props.user) {
    //         setRole(props.user.role)
    //     }
    // }, [props.user])

    const createUser = (role: string) => {
        setLoading(true)
        setAlertLoading(true)
        postData(
            `${ADD_USER_API}/`,
            {
                'role': role,
            }
        ).then(
            response => {
                setLoading(false)
                setAlertOpen(false)
                setAlertLoading(false)
                setAlertMessage('Successfully creating user!')
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

    const handleSaveClick = () => {
        createUser(role)
    }

    const handleAlertCancel = () => {
        setAlertOpen(false)
    }

    const alertConfirmed = () => {
        createUser(role)
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => {
                    props.onUserCreated( 2)
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
                                <Typography variant={'subtitle1'}>First Name</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    id="input_first_name"
                                    hiddenLabel={true}
                                    type={"text"}
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
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Username</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    id="input_username"
                                    hiddenLabel={true}
                                    type={"text"}
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Email</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    id="input_email"
                                    hiddenLabel={true}
                                    type={"text"}
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Password</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    id="input_password"
                                    hiddenLabel={true}
                                    type={"password"}
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
                                    value={'Viewer'}
                                    onChange={(event: SelectChangeEvent) => {
                                        setRole(event.target.value as string)
                                    }}
                                >
                                    { ROLE_TYPES.map((value, index) => {
                                        return <MenuItem key={index} value={value}>{value}</MenuItem>
                                    })}
                                </Select>
                            </Grid>
                        </Grid>
                        <Grid container columnSpacing={2} rowSpacing={2} sx={{paddingTop: '1em'}} flexDirection={'row'} justifyContent={'space-between'}>
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
    )
}