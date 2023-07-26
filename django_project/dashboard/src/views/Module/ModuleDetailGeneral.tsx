import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import ModuleInterface from '../../models/module';
import Loading from "../../components/Loading";
import AlertMessage from '../../components/AlertMessage';
import {postData} from "../../utils/Requests";
import AlertDialog from '../../components/AlertDialog';

interface ModuleDetailGeneralInterface {
    module: ModuleInterface,
    onModuleUpdated: () => void
}

const UPDATE_MODULE_DETAIL_URL = '/api/module/detail/'


export default function ModuleDetailGeneral(props: ModuleDetailGeneralInterface) {
    const [loading, setLoading] = useState(false)
    const [description, setDescription] = useState('')
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [alertOpen, setAlertOpen] = useState<boolean>(false)
    const [alertLoading, setAlertLoading] = useState<boolean>(false)
    const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
    const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
    const navigate = useNavigate()

    const updateModuleDetail = (desc: string, isActive: boolean) => {
        setLoading(true)
        setAlertLoading(true)
        postData(
            `${UPDATE_MODULE_DETAIL_URL}${props.module.uuid}/`,
            {
                'description': desc,
                'is_active': isActive
            }
        ).then(
            response => {
                setLoading(false)
                setAlertOpen(false)
                setAlertLoading(false)
                setAlertMessage('Successfully updating module!')
            }
        ).catch(error => {
            setLoading(false)
            setAlertLoading(false)
            setAlertOpen(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                alert('Error updating module!')
            }
        })
    }

    useEffect(() => {
        if (props.module) {
            setDescription(props.module.description)
        }
    }, [props.module])

    const toggleModuleStatus = () => {
        let _title = props.module.is_active ? 'Deactivate this module?' : 'Activate this module?'
        let _desc = props.module.is_active ? 'Are you sure you want to deactivate this module?' : 'Are you sure you want to activate this module?'
        setAlertDialogTitle(_title)
        setAlertDialogDescription(_desc)
        setAlertOpen(true)
    }

    const handleSaveClick = () => {
        updateModuleDetail(description, props.module.is_active)
    }

    const handleAlertCancel = () => {
        setAlertOpen(false)
    }

    const alertConfirmed = () => {
        updateModuleDetail(description, !props.module.is_active)
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => {
                    props.onModuleUpdated()
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
                                <Typography variant={'subtitle1'}>Name</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={true}
                                    id="input_name"
                                    hiddenLabel={true}
                                    type={"text"}
                                    value={props.module.name}
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Description</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={loading || !props.module.is_active}
                                    id="input_description"
                                    hiddenLabel={true}
                                    type={"text"}
                                    onChange={val => setDescription(val.target.value)}
                                    value={description}
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
                                    value={props.module.is_active ? 'Active' : 'Inactive'}
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                        </Grid>
                        <Grid container columnSpacing={2} rowSpacing={2} sx={{paddingTop: '1em'}} flexDirection={'row'} justifyContent={'space-between'}>
                            <Grid item>
                                <div className='button-container'>
                                    <Button
                                        variant={"contained"}
                                        color={ props.module.is_active ? 'error' : 'primary' }
                                        disabled={loading}
                                        onClick={toggleModuleStatus}>
                                        <span style={{ display: 'flex' }}>
                                        { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { props.module.is_active ? 'Deactivate' : 'Activate' }</span>
                                    </Button>
                                </div>
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
    )
}