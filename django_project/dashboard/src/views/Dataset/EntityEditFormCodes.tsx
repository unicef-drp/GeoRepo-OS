import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import {AddButton} from "../../components/Elements/Buttons";
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import CancelIcon from '@mui/icons-material/Cancel';
import DeleteIcon from '@mui/icons-material/Delete';
import {EntityCode} from '../../models/entity'
import Select, {SelectChangeEvent} from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";

const FETCH_ID_TYPE_URL = '/api/id-type/list/'

interface EntityCodesInterface {
    codes: EntityCode[],
    onUpdate: (codes:EntityCode[]) => void;
}

interface CodeType {
    id: number,
    name: string
}

export default function EntityCodesInput(props: EntityCodesInterface) {
    const codes = props.codes;
    const [editableIdx, setEditableIdx] = useState<number>(-1)
    const [codeTypes, setCodeTypes] = useState<CodeType[]>([])
    const navigate = useNavigate()

    useEffect(() => {
      axios.get(`${FETCH_ID_TYPE_URL}`).then(
        response => {
            setCodeTypes(response.data)
        }
      ).catch((error) => {
        if (error.response) {
          if (error.response.status == 403) {
            // TODO: use better way to handle 403
            navigate('/invalid_permission')
          }
        }
      })
    }, [])

    const addNewEntityCodes = () => {
        let _data:EntityCode[] = codes.map((code) => {
            return {
                id: code.id,
                default: code.default,
                code_id: code.code_id,
                value: code.value
            }
        })
        let _new_item:EntityCode = {
            id: 0,
            default: false,
            code_id: 1,
            value: ''
        }
        _data.push(_new_item)
        props.onUpdate(_data)
    }

    const deleteEntityCodes = (deletedCode: EntityCode) => {
        let _data:EntityCode[] = codes.reduce((res, code) => {
            if (code.id !== deletedCode.id) {
                res.push({
                    id: code.id,
                    default: code.default,
                    code_id: 1,
                    value: code.value
                })
            }
            return res
        }, [] as EntityCode[])
         props.onUpdate(_data)
    }

    const onKeyPress = (e: any, editedCode: EntityCode) => {
        if(e.keyCode == 13){
            e.preventDefault()
            let _data:EntityCode[] = codes.reduce((res, code) => {
                if (code.id === editedCode.id) {
                    res.push({
                        id: editedCode.id,
                        default: editedCode.default,
                        code_id: editedCode.code_id,
                        value: e.target.value
                    })
                } else {
                    res.push(code)
                }
                return res
            }, [] as EntityCode[])
            props.onUpdate(_data)
            setEditableIdx(-1)
        } else if (e.keyCode == 27) {
            e.preventDefault()
            setEditableIdx(-1)
        }
    }

    //@ts-ignore
    const onSelectCodeType = (selectedCodeType: number, editedCode: EntityCode) => {
        let _data:EntityCode[] = codes.reduce((res, code) => {
        if (code.id === editedCode.id) {
            res.push({
                id: editedCode.id,
                default: editedCode.default,
                code_id: selectedCodeType,
                value: editedCode.value
            })
        } else {
            res.push(code)
        }
        return res
        }, [] as EntityCode[])
        props.onUpdate(_data)
    }

    const getCodeType = (codeTypeId:number) => {
        for (let i = 0; i < codeTypes.length; i++) {
            if (codeTypes[i].id === codeTypeId) {
                return codeTypes[i].name
            }
        }
    }

    return (
        <Grid container flexDirection={'row'}  sx={{alignItems: 'flex-start'}}>
            <Grid item>
                <TableContainer component={Paper} sx={{minWidth: '465px'}}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Default</TableCell>
                                <TableCell>Codes Type</TableCell>
                                <TableCell>Codes</TableCell>
                                <TableCell></TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {codes && codes.length ? codes.map((code, index) => (
                                <TableRow key={index}>
                                    <TableCell>
                                        {code.default ? 'Default': ''}
                                    </TableCell>
                                    <TableCell>
                                        {index === editableIdx ? (
                                            <Select
                                                labelId="code-type-select-label"
                                                id="code-type-select"
                                                value={code.code_id as unknown as string}
                                                onChange={(event: SelectChangeEvent) => {
                                                    onSelectCodeType(event.target.value as unknown as number, code)
                                                }}
                                            >
                                                { codeTypes.map((value, index) => {
                                                    return <MenuItem
                                                      key={index}
                                                      value={value.id}>
                                                        {value.name}
                                                    </MenuItem>
                                                })}
                                            </Select>
                                        ) : getCodeType(code.code_id)}
                                    </TableCell>
                                    <TableCell>
                                        {index === editableIdx ? (
                                            <TextField
                                                label="Code"
                                                id="standard-size-small"
                                                defaultValue={code.value}
                                                size="small"
                                                variant="standard"
                                                onKeyDown={(e: any) => onKeyPress(e, code)}
                                                autoFocus
                                            />
                                        ) : code.value}
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
                                                      disabled={code.default}
                                                    >
                                                        <EditIcon fontSize='small' />
                                                    </IconButton>
                                                )}
                                            </Grid>
                                            <Grid item>
                                                <IconButton
                                                  aria-label="delete"
                                                  title='delete'
                                                  onClick={() => deleteEntityCodes(code)}
                                                  disabled={code.default}
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
            <Grid item sx={{paddingLeft: '20px'}}>
                <AddButton text={'Add Codes'} variant={'secondary'} onClick={addNewEntityCodes}/>
            </Grid>
        </Grid>
    )
}