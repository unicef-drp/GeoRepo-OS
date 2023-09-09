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
import Loading from "../../components/Loading";
import AlertMessage from '../../components/AlertMessage';
import {postData} from "../../utils/Requests";
import Scrollable from '../../components/Scrollable';
import {AddButton} from "../../components/Elements/Buttons";
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import CancelIcon from '@mui/icons-material/Cancel';
import DeleteIcon from '@mui/icons-material/Delete';
import EntityEditInterface , {EntityName} from '../../models/entity'
import {updateMenu} from "../../reducers/breadcrumbMenu";
import Select, {SelectChangeEvent} from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";


interface EntityNamesInterface {
    names: EntityName[],
    onUpdate: (names:EntityName[]) => void;
}

interface NameType {
    id: number,
    name: string
}

export default function EntityNamesInput(props: EntityNamesInterface) {
    const [loading, setLoading] = useState(true)
    const names = props.names;
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [editableIdx, setEditableIdx] = useState<number>(-1)
    const navigate = useNavigate()

    const addNewEntityNames = () => {
        let _data:EntityName[] = names.map((name) => {
            return {
                id: name.id,
                default: name.default,
                language_id: name.language_id,
                name: name.name
            }
        })
        let _new_item:EntityName = {
            id: 0,
            default: false,
            language_id: 1,
            name: ''
        }
        _data.push(_new_item)
        props.onUpdate(_data)
    }

    const deleteEntityNames = (deletedName: EntityName) => {
        let _data:EntityName[] = names.reduce((res, name) => {
            if (name.id !== deletedName.id) {
                res.push({
                    id: name.id,
                    default: name.default,
                    language_id: 1,
                    name: name.name
                })
            }
            return res
        }, [] as EntityName[])
         props.onUpdate(_data)
    }

    const onKeyPress = (e: any, editedName: EntityName) => {
        if(e.keyCode == 13){
            e.preventDefault()
            let _data:EntityName[] = names.reduce((res, name) => {
                if (name.id === editedName.id) {
                    res.push({
                        id: editedName.id,
                        default: editedName.default,
                        language_id: editedName.language_id,
                        name: e.target.value
                    })
                } else {
                    res.push(name)
                }
                return res
            }, [] as EntityName[])
            props.onUpdate(_data)
            setEditableIdx(-1)
        } else if (e.keyCode == 27) {
            e.preventDefault()
            setEditableIdx(-1)
        }
    }

    //@ts-ignore
    const onSelectNameType = (selectedNameType: number, editedName: EntityName) => {
        let _data:EntityName[] = names.reduce((res, name) => {
        if (name.id === editedName.id) {
            res.push({
                id: editedName.id,
                default: editedName.default,
                language_id: selectedNameType,
                name: editedName.name
            })
        } else {
            res.push(name)
        }
        return res
        }, [] as EntityName[])
        props.onUpdate(_data)
    }

    return (
        <Grid container flexDirection={'row'}  sx={{alignItems: 'flex-start'}}>
            <Grid item>
                <TableContainer component={Paper} sx={{minWidth: '465px'}}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell sx={{width: '210px'}}>Default</TableCell>
                                <TableCell sx={{width: '210px'}}>Names</TableCell>
                                <TableCell></TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {names && names.length ? names.map((name, index) => (
                                <TableRow key={index}>
                                    <TableCell>
                                        {name.default ? 'Default': ''}
                                    </TableCell>
                                    <TableCell>
                                        {index === editableIdx ? (
                                            <TextField
                                                label="Name"
                                                id="standard-size-small"
                                                defaultValue={name.name}
                                                size="small"
                                                variant="standard"
                                                onKeyDown={(e: any) => onKeyPress(e, name)}
                                                autoFocus
                                            />
                                        ) : name.name}
                                    </TableCell>
                                    <TableCell>
                                        <Grid container flexDirection={'row'} spacing={1}>
                                            <Grid item>
                                                { editableIdx===index ? (
                                                    <IconButton aria-label="cancel" title='cancel' onClick={() => setEditableIdx(-1)}>
                                                        <CancelIcon fontSize='small' />
                                                    </IconButton>
                                                ) : (
                                                    <IconButton
                                                      aria-label="edit"
                                                      title='edit'
                                                      onClick={() => setEditableIdx(index)}
                                                      disabled={name.default}
                                                    >
                                                        <EditIcon fontSize='small' />
                                                    </IconButton>
                                                )}
                                            </Grid>
                                            <Grid item>
                                                <IconButton
                                                  aria-label="delete"
                                                  title='delete'
                                                  onClick={() => deleteEntityNames(name)}
                                                  disabled={name.default}
                                                >
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
                <AddButton text={'Add Names'} variant={'secondary'} onClick={addNewEntityNames}/>
            </Grid>
        </Grid>
    )
}