import React, {useEffect, useState} from 'react';
import axios from "axios";
import {useNavigate} from "react-router-dom";
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import InputAdornment from '@mui/material/InputAdornment';
import OutlinedInput from '@mui/material/OutlinedInput';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import Button from '@mui/material/Button';
import UserInterface, {APIKeyInterface} from '../../models/user';
import Loading from "../../components/Loading";
import AlertMessage from '../../components/AlertMessage';
import AlertDialog from '../../components/AlertDialog';
import Scrollable from "../../components/Scrollable";


interface UserAPIKeysInterface {
    user: UserInterface,
    isUserProfile: boolean
}

interface UserAPIKeyCreateFormInterface {
    loading: boolean,
    handleSaveClick: (platform?: string, owner?: string, contact?: string) => void
}

interface UserAPIKeyItemInterface {
    loading: boolean,
    apiKey: APIKeyInterface,
    isUserProfile: boolean,
    handleChangeStatus: (isActive: boolean) => void,
    handleDeleteKey: () => void,
    handleAPIKeyCopied: () => void
}

interface TempAPIKeyData {
    platform?: string,
    owner?: string,
    contact?: string,
}

const USER_API_KEYS_URL = '/api/token/'

function UserAPIKeyCreateForm(props: UserAPIKeyCreateFormInterface) {
    const [platform, setPlatform] = useState('')
    const [owner, setOwner] = useState('')
    const [contact, setContact] = useState('')

    return (
        <Grid container sx={{width: '50%'}}>
            <div className='FormContainer'>
                <FormControl className='FormContent'>
                    <Grid container columnSpacing={2} rowSpacing={2}>
                        <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                            <Typography variant={'subtitle1'}>Platform</Typography>
                        </Grid>
                        <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                            <TextField
                                id="input_platform"
                                hiddenLabel={true}
                                type={"text"}
                                value={platform}
                                onChange={(e) => setPlatform(e.target.value)}
                                sx={{ width: '100%' }}
                            />
                        </Grid>
                        <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                            <Typography variant={'subtitle1'}>Owner</Typography>
                        </Grid>
                        <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                            <TextField
                                id="input_owner"
                                hiddenLabel={true}
                                type={"text"}
                                value={owner}
                                onChange={(e) => setOwner(e.target.value)}
                                sx={{ width: '100%' }}
                            />
                        </Grid>
                        <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                            <Typography variant={'subtitle1'}>Contact</Typography>
                        </Grid>
                        <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                            <TextField
                                id="input_contact"
                                hiddenLabel={true}
                                type={"text"}
                                value={contact}
                                onChange={(e) => setContact(e.target.value)}
                                sx={{ width: '100%' }}
                            />
                        </Grid>
                    </Grid>
                    <Grid container sx={{paddingTop: '1em'}} flexDirection={'row'} justifyContent={'flex-end'}>
                        <Grid item>
                            <Button
                                className='button-with-loading'
                                variant={"contained"}
                                disabled={props.loading}
                                onClick={() => props.handleSaveClick(platform, owner, contact)}
                                sx={{ width: '200px'}}>
                                <span style={{ display: 'flex' }}>
                                { props.loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Generate API Key" }</span>
                            </Button>
                        </Grid>
                    </Grid>
                </FormControl>
            </div>
        </Grid>
    )
}

function UserAPIKeyItem(props: UserAPIKeyItemInterface) {
    const [showAPIKey, setShowAPIKey] = useState(false)
    const [alertMessage, setAlertMessage] = useState('')
    const isSuperUser = (window as any).is_admin

    useEffect(() => {
        if (!props.isUserProfile) {
            setAlertMessage('')
        } else {
            if (props.apiKey.is_active) {
                setAlertMessage('This API Key is personal and please do not share it with other people. If we notice suspect behavior, your API Key can be deleted and your account suspended.')
            } else {
                setAlertMessage('In order to obtain more information or to reactivate your API KEY, please contact an administrator.')
            }
        }
    }, [props.apiKey, props.isUserProfile])

    const displayValue = (value: string) => {
        if (value) return value
        return '-'
    }

    const handleClickShowAPIKey = () => setShowAPIKey((show) => !show)

    const handleMouseDownAPIKey = (event: React.MouseEvent<HTMLButtonElement>) => {
        event.preventDefault();
    }

    const handleCopyAPIKey = () => {
        navigator.clipboard.writeText(props.apiKey.key)
        props.handleAPIKeyCopied()
    }

    return (
        <Grid container flexDirection={'column'} flexWrap={'nowrap'}>
            <Grid item md={5} xl={5} xs={12} sx={{marginBottom: '10px'}}>
                <Grid container flexDirection={'row'} justifyContent={'center'}>
                    { props.isUserProfile && alertMessage ?
                    <Alert style={{ width: '100%', textAlign: 'left' }} severity='warning'>
                        <AlertTitle>{alertMessage}</AlertTitle>
                    </Alert> : null }
                </Grid>
            </Grid>
            <Grid item md={5} xl={5} xs={12}>
                <Grid container flexDirection={'row'} justifyContent={'flex-start'}>
                    <Grid item>
                        { ((!props.apiKey.is_active && isSuperUser) || props.apiKey.is_active) && (
                            <Button
                                className='button-with-loading'
                                variant={"contained"}
                                color='error'
                                disabled={props.loading}
                                onClick={() => props.handleDeleteKey()}>
                                <span style={{ display: 'flex' }}>
                                { props.loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Delete API Key" }</span>
                            </Button>
                        )}
                    </Grid>
                </Grid>
            </Grid>
            <Grid item  md={5} xl={5} xs={12}>
                <Box sx={{ marginTop: '20px', padding: '10px', borderRadius: '6px', border: '1px solid #d0d7de'}}>
                    <Grid container flexDirection={'column'} >
                        <Grid item>
                            <Grid container flexDirection={'column'} className='api-key-container'>
                                <Grid item>
                                    <FormControl sx={{width: '100%' }} variant="outlined">
                                        <InputLabel htmlFor="outlined-adornment-password">API Key</InputLabel>
                                        <OutlinedInput
                                            id="outlined-adornment-password"
                                            className='api-key-input'
                                            type={showAPIKey ? 'text' : 'password'}
                                            defaultValue={props.apiKey.key}
                                            disabled
                                            endAdornment={
                                            <InputAdornment position="end">
                                                <IconButton
                                                    aria-label="toggle API Key"
                                                    onClick={handleClickShowAPIKey}
                                                    onMouseDown={handleMouseDownAPIKey}
                                                    edge="end"
                                                    title={showAPIKey ? 'Hide API Key' : 'Show API Key'}
                                                    >
                                                    {showAPIKey ? <VisibilityOff /> : <Visibility />}
                                                </IconButton>
                                                <IconButton
                                                    aria-label="Copy API Key"
                                                    onClick={handleCopyAPIKey}
                                                    edge="end"
                                                    title='Copy API Key'
                                                    sx={{marginLeft: '10px'}}
                                                    >
                                                    <ContentCopyIcon />
                                                </IconButton>
                                            </InputAdornment>
                                            }
                                            label="API Key"
                                        />
                                        </FormControl>
                                </Grid>
                                <Grid item sx={{marginTop: '10px'}}>
                                    <Grid container flexDirection={'row'}>
                                        <Grid item>
                                            <Typography variant={'subtitle1'}>Platform : {displayValue(props.apiKey.platform)}</Typography>
                                        </Grid>
                                    </Grid>
                                </Grid>
                                <Grid item>
                                    <Grid container flexDirection={'row'}>
                                        <Grid className={'form-label'} item>
                                            <Typography variant={'subtitle1'}>Owner : {displayValue(props.apiKey.owner)}</Typography>
                                        </Grid>
                                    </Grid>
                                </Grid>
                                <Grid item>
                                    <Grid container flexDirection={'row'}>
                                        <Grid className={'form-label'} item>
                                            <Typography variant={'subtitle1'}>Contact : {displayValue(props.apiKey.contact)}</Typography>
                                        </Grid>
                                    </Grid>
                                </Grid>
                            </Grid>
                        </Grid>
                        <Grid item>
                            <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                                <Grid item className={'form-label'}>
                                    <Typography variant={'subtitle1'}>Status : <span style={{fontWeight: 'bold'}}>{ props.apiKey.is_active ? ' Active': ' Revoked'}</span></Typography>
                                </Grid>
                                <Grid item>
                                    <div className='button-container'>
                                        { !props.isUserProfile && (
                                            <Button
                                                variant={"outlined"}
                                                color={props.apiKey.is_active ? 'warning' : 'primary'}
                                                disabled={props.loading}
                                                onClick={() => props.handleChangeStatus(!props.apiKey.is_active)}>
                                                <span style={{ display: 'flex' }}>
                                                { props.loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { props.apiKey.is_active ? 'Revoke' : 'Activate' }</span>
                                            </Button>
                                        )}
                                    </div>
                                </Grid>
                            </Grid>
                        </Grid>
                    </Grid>
                </Box>
            </Grid>
        </Grid>
        
    )
}

export default function UserAPIKeys(props: UserAPIKeysInterface) {
    const [loading, setLoading] = useState(false)
    const [actionLoading, setActionLoading] = useState(false)
    const [apiKey, setAPIKey] = useState<APIKeyInterface>(null)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [alertOpen, setAlertOpen] = useState<boolean>(false)
    const [alertLoading, setAlertLoading] = useState<boolean>(false)
    const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
    const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
    const [confirmMode, setConfirmMode] = useState<number>(0) // 1: createAPIKey, 2: deleteAPIKey
    const [tempCreateAPIKeyData, setTempCreateAPIKeyData] = useState<TempAPIKeyData>({})
    const navigate = useNavigate()

    useEffect(() => {
        doFetchAPIKeys()
    }, [])

    const doFetchAPIKeys = () => {
        setLoading(true)
        axios.get(`${USER_API_KEYS_URL}${props.user.id}/`).then(
            response => {
              setLoading(false)
              if (response.data && response.data.length) {
                let _apiKey = response.data[0] as APIKeyInterface
                setAPIKey(_apiKey)
              } else {
                setAPIKey(null)
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

    const updateAPIKey = (isActive: boolean) => {
        setActionLoading(true)
        axios.put(`${USER_API_KEYS_URL}${props.user.id}/`, {
            'is_active': isActive
        }).then(
            response => {
                setActionLoading(false)
                if (isActive) {
                    setAlertMessage('The API Key has been successfully activated!')
                } else {
                    setAlertMessage('The API Key has been successfully deactivated!')
                }
                doFetchAPIKeys()
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

    const doCreateAPIKey = (platform?: string, owner?: string, contact?: string) => {
        axios.post(`${USER_API_KEYS_URL}${props.user.id}/`, {
            'platform': platform,
            'owner': owner,
            'contact': contact
        }).then(
            response => {
                setAlertLoading(false)
                setAlertOpen(false)
                setActionLoading(false)
                setConfirmMode(0)
                setTempCreateAPIKeyData({})
                setAlertMessage('The API Key has been successfully created!')
                doFetchAPIKeys()
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

    const doDeleteAPIKey = () => {
        axios.delete(`${USER_API_KEYS_URL}${props.user.id}/`).then(
            response => {
                setAlertLoading(false)
                setAlertOpen(false)
                setConfirmMode(0)
                setActionLoading(false)
                setAlertMessage('The API Key has been successfully removed!')
                doFetchAPIKeys()
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

    const deleteAPIKey = () => {
        // set confirm to delete
        setActionLoading(true)
        setAlertDialogTitle('Are you sure you want to delete this API Key?')
        setAlertDialogDescription('Any applications or scripts using this API Key will no longer be able to access the GeoRepo API. You cannot undo this action.')
        setConfirmMode(2)
        setAlertOpen(true)
    }

    const createAPIKey = (platform?: string, owner?: string, contact?: string) => {
        // set warning
        setActionLoading(true)
        setAlertDialogTitle('Generating new API Key')
        setAlertDialogDescription('This API Key is personal and please do not share it with other people. If we notice suspect behavior, your API Key can be deleted and your account suspended.')
        setConfirmMode(1)
        setTempCreateAPIKeyData({
            'platform': platform,
            'owner': owner,
            'contact': contact
        })
        setAlertOpen(true)
    }

    const handleAlertCancel = () => {
        setAlertOpen(false)
        setActionLoading(false)
        setConfirmMode(0)
        setTempCreateAPIKeyData({})
    }

    const alertConfirmed = () => {
        setAlertLoading(true)
        if (confirmMode === 1) {
            // create API Key
            doCreateAPIKey(tempCreateAPIKeyData.platform, tempCreateAPIKeyData.owner, tempCreateAPIKeyData.contact)
        } else {
            doDeleteAPIKey()
        }
    }


    return (
        <Scrollable>
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
                <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                    <AlertMessage message={alertMessage} onClose={() => {
                        setAlertMessage('')
                    }} />
                    <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                            alertConfirmed={alertConfirmed}
                            alertLoading={alertLoading}
                            alertDialogTitle={alertDialogTitle}
                            alertDialogDescription={alertDialogDescription} />
                    { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
                    { !loading && apiKey !== null &&  (
                        <UserAPIKeyItem loading={actionLoading} apiKey={apiKey} isUserProfile={props.isUserProfile} handleChangeStatus={updateAPIKey} handleDeleteKey={deleteAPIKey} handleAPIKeyCopied={() => setAlertMessage('API Key copied to clipboard')}  />
                    )}
                    { !loading && apiKey === null &&  (
                        <UserAPIKeyCreateForm loading={actionLoading} handleSaveClick={createAPIKey} />
                    )}
                </Box>
            </Box>
        </Scrollable>
    )
}



