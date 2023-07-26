import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Dataset from '../../models/dataset';
import Loading from "../../components/Loading";
import AlertMessage from '../../components/AlertMessage';
import {postData} from "../../utils/Requests";
import Scrollable from '../../components/Scrollable';
import {AddButton} from "../../components/Elements/Buttons";
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import CancelIcon from '@mui/icons-material/Cancel';
import DeleteIcon from '@mui/icons-material/Delete';

const DATASET_ADMIN_LEVEL_NAMES_URL = '/api/dataset-admin-level-names/'

interface DatasetAdminLevelNamesInterface {
    dataset: Dataset
}

interface AdminLevelName {
    level: number,
    label: string
}

export default function DatasetAdminLevelNames(props: DatasetAdminLevelNamesInterface) {
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState<AdminLevelName[]>([])
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [editableIdx, setEditableIdx] = useState<number>(-1)
    const navigate = useNavigate()

    const fetchAdminLevelNames = () => {
        axios.get(`${DATASET_ADMIN_LEVEL_NAMES_URL}${props.dataset.uuid}/`).then(
            response => {
                setLoading(false)
                setData(response.data as AdminLevelName[])
            }
        )
    }

    useEffect(() => {
        if (props.dataset && props.dataset.uuid) {
            fetchAdminLevelNames()
        }
    }, [props.dataset])

    const addNewAdminLevel = () => {
        let _data:AdminLevelName[] = data.map((value) => {
            return {
                level: value.level,
                label: value.label
            }
        })
        let _new_item:AdminLevelName = {
            level: _data.length ? _data[_data.length - 1].level + 1 : 0,
            label: ''
        }
        _data.push(_new_item)
        setData(_data)
    }

    const handleSaveClick = () => {
        setLoading(true)
        postData(`${DATASET_ADMIN_LEVEL_NAMES_URL}${props.dataset.uuid}/`, data).then(
            response => {
                setLoading(false)
                setAlertMessage('Successfully saving admin level names!')
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
                alert('Error saving admin level names...')
            }
          })
    }

    const deleteAdminLevel = (adminLevelName: AdminLevelName) => {
        let _data:AdminLevelName[] = data.reduce((res, value) => {
            if (value.level !== adminLevelName.level) {
                res.push({
                    level: value.level,
                    label: value.label
                })
            }
            return res
        }, [] as AdminLevelName[])
        setData(_data)
    }

    const onKeyPress = (e: any, adminLevelName: AdminLevelName) => {
        if(e.keyCode == 13){
            e.preventDefault()
            let _data:AdminLevelName[] = data.reduce((res, value) => {
                res.push({
                    level: value.level,
                    label: value.level === adminLevelName.level ? e.target.value:value.label
                })
                return res
            }, [] as AdminLevelName[])
            setData(_data)
            setEditableIdx(-1)
        } else if (e.keyCode == 27) {
            e.preventDefault()
            setEditableIdx(-1)
        }
    }

    return (
        <Scrollable>
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => setAlertMessage('')} />
                <Grid container flexDirection={'column'} sx={{alignItems: 'center', paddingTop: '10px'}}>
                    <Grid item sx={{marginTop: '20px', display: 'flex', justifyContent: 'flex-end', width: '100%'}}>
                    </Grid>
                    <Grid item>
                        <Grid container flexDirection={'column'}  sx={{alignItems: 'flex-start'}}>
                            <Grid item>
                                <TableContainer component={Paper} sx={{minWidth: '465px'}}>
                                    <Table>
                                        <TableHead>
                                            <TableRow>
                                                <TableCell>Admin Level</TableCell>
                                                <TableCell sx={{width: '210px'}}>Label</TableCell>
                                                <TableCell></TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {data && data.length ? data.map((adminLevelName, index) => (
                                                <TableRow key={index}>
                                                    <TableCell>{adminLevelName.level}</TableCell>
                                                    <TableCell>
                                                        {index === editableIdx ? ( 
                                                            <TextField
                                                                label="Level Name"
                                                                id="standard-size-small"
                                                                defaultValue={adminLevelName.label}
                                                                size="small"
                                                                variant="standard"
                                                                onKeyDown={(e: any) => onKeyPress(e, adminLevelName)}
                                                                autoFocus
                                                            />
                                                        ) : adminLevelName.label}
                                                    </TableCell>
                                                    <TableCell>
                                                        <Grid container flexDirection={'row'} spacing={1}>
                                                            <Grid item>
                                                                { editableIdx===index ? (
                                                                    <IconButton aria-label="cancel" title='cancel' onClick={() => setEditableIdx(-1)}>
                                                                        <CancelIcon fontSize='small' />
                                                                    </IconButton>
                                                                ) : (
                                                                    <IconButton aria-label="edit" title='edit' onClick={() => setEditableIdx(index)} disabled={!props.dataset.is_active}>
                                                                        <EditIcon fontSize='small' />
                                                                    </IconButton>
                                                                )}
                                                            </Grid>
                                                            <Grid item>
                                                                <IconButton aria-label="delete" title='delete' onClick={() => deleteAdminLevel(adminLevelName)} disabled={!props.dataset.is_active}>
                                                                    <DeleteIcon fontSize='small' />
                                                                </IconButton>
                                                            </Grid>
                                                        </Grid>
                                                    </TableCell>
                                                </TableRow>
                                            )):
                                                <TableRow>
                                                    <TableCell>No Data</TableCell>
                                                </TableRow>
                                            }
                                        </TableBody>
                                    </Table>
                                </TableContainer>
                            </Grid>
                            <Grid item sx={{paddingTop: '20px'}}>
                                <AddButton text={'Add Admin Level'} variant={'secondary'} onClick={addNewAdminLevel} disabled={!props.dataset.is_active}/>
                            </Grid>
                        </Grid>
                        
                    </Grid>
                </Grid>
                <Box sx={{ textAlign: 'right', marginTop: '20px' }}>
                    <div className='button-container'>
                        <Button
                            variant={"contained"}
                            disabled={loading || !props.dataset.is_active}
                            onClick={handleSaveClick}>
                            <span style={{ display: 'flex' }}>
                            { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Save" }</span>
                        </Button>
                    </div>
                </Box>
            </Box>
        </Box>
        </Scrollable>
    )
}