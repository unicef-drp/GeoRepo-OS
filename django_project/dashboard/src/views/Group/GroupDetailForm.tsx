import React, {useState} from 'react';
import {useNavigate} from "react-router-dom";
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import GroupInterface from '../../models/group';
import Loading from "../../components/Loading";
import AlertMessage from '../../components/AlertMessage';
import {postData} from "../../utils/Requests";
import {GroupDetailRoute} from '../routes';

interface GroupDetailGeneralInterface {
    group: GroupInterface;
    onGroupUpdated: () => void;
}

const SAVE_GROUP_DETAIL_URL = '/api/group/'

export default function GroupDetailForm(props: GroupDetailGeneralInterface) {
    const [loading, setLoading] = useState(false)
    const [name, setName] = useState<string>(props.group.name)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const navigate = useNavigate()
    const [updatedGroupId, setUpdatedGroupId] = useState(0)

    const saveGroupDetail = (id: number, name: string) => {
        setLoading(true)
        postData(
            `${SAVE_GROUP_DETAIL_URL}${id}/`,
            {
                'name': name
            }
        ).then(
            response => {
                setLoading(false)
                setUpdatedGroupId(response.data['id'])
                setAlertMessage(id === 0 ? 'Successfully creating new group!' : 'Successfully updating group!')
            }
        ).catch(error => {
            setLoading(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                alert(id === 0 ? 'Error creating new group!' : 'Error updating group!')
            }
        })
    }

    const handleSaveClick = () => {
        saveGroupDetail(props.group.id, name)
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => {
                    if (props.group.id === 0) {
                        navigate(`${GroupDetailRoute.path}?id=${updatedGroupId}&tab=0`)
                    } else {
                        props.onGroupUpdated()
                    }                    
                }} />
                <div className='FormContainer'>
                    <FormControl className='FormContent'>
                        <Grid container columnSpacing={2} rowSpacing={2}>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Name</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={loading}
                                    id="input_groupname"
                                    hiddenLabel={true}
                                    type={"text"}
                                    onChange={val => setName(val.target.value)}
                                    value={name}
                                    inputProps={{ maxLength: 150}}
                                    sx={{ width: '50%' }}
                                />
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
