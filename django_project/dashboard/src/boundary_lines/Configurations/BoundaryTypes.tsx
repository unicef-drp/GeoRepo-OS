import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import {v4 as uuidv4} from 'uuid';
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

const DATASET_BOUNDARY_TYPES_URL = '/api/boundary-lines/boundary-types/'

interface BoundaryTypesInterface {
    dataset: Dataset,
    isReadOnly?: boolean
}

interface BoundaryType {
    id: string,
    label: string,
    type_id: number,
    value: string,
    total_entities: number
}

export default function BoundaryTypes(props: BoundaryTypesInterface) {
    const [loading, setLoading] = useState(true)
    const [data, setData] = useState<BoundaryType[]>([])
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [editableIdxLabel, setEditableIdxLabel] = useState<number>(-1)
    const [editableIdxValue, setEditableIdxValue] = useState<number>(-1)
    const navigate = useNavigate()

    const fetchBoundaryTypes = () => {
        axios.get(`${DATASET_BOUNDARY_TYPES_URL}${props.dataset.uuid}/`).then(
            response => {
                setLoading(false)
                setData(response.data as BoundaryType[])
            }
        )
    }

    useEffect(() => {
        if (props.dataset && props.dataset.uuid) {
            fetchBoundaryTypes()
        }
    }, [props.dataset])

    const addNewBoundaryType = () => {
        let _data:BoundaryType[] = data.map((value) => {
            return {
                id: value.id,
                label: value.label,
                type_id: value.type_id,
                value: value.value,
                total_entities: value.total_entities
            }
        })
        let _new_item:BoundaryType = {
            id: uuidv4().toString(),
            type_id: 0,
            label: '',
            value: '',
            total_entities: 0
        }
        _data.push(_new_item)
        setData(_data)
    }

    const handleSaveClick = () => {
        setLoading(true)
        postData(`${DATASET_BOUNDARY_TYPES_URL}${props.dataset.uuid}/`, data).then(
            response => {
                setLoading(false)
                setAlertMessage('Successfully saving boundary types!')
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
                alert('Error saving boundary types...')
            }
          })
    }

    const deleteBoundaryType = (boundaryType: BoundaryType) => {
        let _data:BoundaryType[] = data.reduce((res, value) => {
            if (value.id !== boundaryType.id) {
                res.push({
                    id: value.id,
                    label: value.label,
                    type_id: value.type_id,
                    value: value.value,
                    total_entities: value.total_entities
                })
            }
            return res
        }, [] as BoundaryType[])
        setData(_data)
    }

    const onKeyPressLabel = (e: any, boundaryType: BoundaryType) => {
        if(e.keyCode == 13){
            e.preventDefault()
            let _data:BoundaryType[] = data.reduce((res, value) => {
                res.push({
                    id: value.id,
                    label: value.id===boundaryType.id?e.target.value:value.label,
                    type_id: value.type_id,
                    value: value.value,
                    total_entities: value.total_entities
                })
                return res
            }, [] as BoundaryType[])
            setData(_data)
            setEditableIdxLabel(-1)
        } else if (e.keyCode == 27) {
            e.preventDefault()
            setEditableIdxLabel(-1)
        }
    }

    const onKeyPressValue = (e: any, boundaryType: BoundaryType) => {
        if(e.keyCode == 13){
            e.preventDefault()
            let _data:BoundaryType[] = data.reduce((res, value) => {
                res.push({
                    id: value.id,
                    label: value.label,
                    type_id: value.type_id,
                    value: value.id===boundaryType.id?e.target.value:value.value,
                    total_entities: value.total_entities
                })
                return res
            }, [] as BoundaryType[])
            setData(_data)
            setEditableIdxValue(-1)
        } else if (e.keyCode == 27) {
            e.preventDefault()
            setEditableIdxValue(-1)
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
                                                <TableCell>Label</TableCell>
                                                <TableCell>Value</TableCell>
                                                <TableCell>Total Lines</TableCell>
                                                <TableCell></TableCell>
                                            </TableRow>
                                        </TableHead>
                                        <TableBody>
                                            {data && data.length ? data.map((boundaryType, index) => (
                                                <TableRow key={index}>
                                                    <TableCell>
                                                        {index === editableIdxLabel ? ( 
                                                            <Grid container flexDirection={'row'} spacing={1} alignItems={'center'}>
                                                                <Grid item>
                                                                    <TextField
                                                                        label="Label"
                                                                        id="standard-size-small"
                                                                        defaultValue={boundaryType.label}
                                                                        size="small"
                                                                        variant="standard"
                                                                        onKeyDown={(e: any) => onKeyPressLabel(e, boundaryType)}
                                                                        autoFocus
                                                                        disabled={props.isReadOnly}
                                                                    />
                                                                </Grid>
                                                                <Grid item>
                                                                    <IconButton aria-label="cancel" title='cancel' onClick={() => setEditableIdxLabel(-1)} disabled={props.isReadOnly}>
                                                                        <CancelIcon fontSize='small' />
                                                                    </IconButton>
                                                                </Grid>
                                                            </Grid>
                                                        ) : (
                                                            <Grid container flexDirection={'row'} spacing={1} alignItems={'center'}>
                                                                <Grid item>{boundaryType.label}</Grid>
                                                                <Grid item>
                                                                    <IconButton aria-label="edit" title='edit' onClick={() => setEditableIdxLabel(index)} disabled={props.isReadOnly}>
                                                                        <EditIcon fontSize='small' />
                                                                    </IconButton>
                                                                </Grid>
                                                            </Grid>
                                                        )}
                                                    </TableCell>
                                                    <TableCell>
                                                        {index === editableIdxValue ? ( 
                                                            <Grid container flexDirection={'row'} spacing={1} alignItems={'center'}>
                                                                <Grid item>
                                                                    <TextField
                                                                        label="Value"
                                                                        id="standard-size-small"
                                                                        defaultValue={boundaryType.value}
                                                                        size="small"
                                                                        variant="standard"
                                                                        onKeyDown={(e: any) => onKeyPressValue(e, boundaryType)}
                                                                        autoFocus
                                                                        disabled={props.isReadOnly}
                                                                    />
                                                                </Grid>
                                                                <Grid item>
                                                                    <IconButton aria-label="cancel" title='cancel' onClick={() => setEditableIdxValue(-1)} disabled={props.isReadOnly}>
                                                                        <CancelIcon fontSize='small' />
                                                                    </IconButton>
                                                                </Grid>
                                                            </Grid>
                                                        ) : (
                                                            <Grid container flexDirection={'row'} spacing={1} alignItems={'center'}>
                                                                <Grid item>{boundaryType.value}</Grid>
                                                                <Grid item>
                                                                    <IconButton aria-label="edit" title='edit' onClick={() => setEditableIdxValue(index)} disabled={props.isReadOnly}>
                                                                        <EditIcon fontSize='small' />
                                                                    </IconButton>
                                                                </Grid>
                                                            </Grid>
                                                        )}
                                                    </TableCell>
                                                    <TableCell>
                                                        <Grid container flexDirection={'row'} spacing={1}>
                                                            <Grid item>
                                                                {boundaryType.total_entities}
                                                            </Grid>
                                                        </Grid>
                                                    </TableCell>
                                                    <TableCell>
                                                        <Grid container flexDirection={'row'} spacing={1}>
                                                            <Grid item>
                                                                { boundaryType.total_entities === 0 && (
                                                                <IconButton aria-label="delete" title='delete' onClick={() => deleteBoundaryType(boundaryType)} disabled={props.isReadOnly}>
                                                                    <DeleteIcon fontSize='small' />
                                                                </IconButton>
                                                                )}
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
                                <AddButton text={'Add Boundary Type'} variant={'secondary'} onClick={addNewBoundaryType} disabled={props.isReadOnly} />
                            </Grid>
                        </Grid>
                        
                    </Grid>
                </Grid>
                <Box sx={{ textAlign: 'right', marginTop: '20px' }}>
                    <div className='button-container'>
                        <Button
                            variant={"contained"}
                            disabled={loading || props.isReadOnly}
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

