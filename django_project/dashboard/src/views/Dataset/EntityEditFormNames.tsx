import React, {useEffect, useState} from 'react';
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
import {EntityName} from '../../models/entity'
import {fetchLanguages, LanguageOption} from "../../utils/Requests";
import Select, {SelectChangeEvent} from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Radio from '@mui/material/Radio';
import {v4 as uuidv4} from 'uuid';


interface EntityNamesInterface {
    names: EntityName[],
    onUpdate: (names:EntityName[]) => void;
}

export default function EntityNamesInput(props: EntityNamesInterface) {
    const names = props.names;
    const [languageOptions, setLanguageOptions] = useState<[] | LanguageOption[]>([])
    const [editableIdx, setEditableIdx] = useState<number>(-1)

    useEffect(() => {
    // Get languages
    fetchLanguages().then(languages => {
      setLanguageOptions(languages)
    })
    }, [])

    //@ts-ignore
    const onSelectLanguage = (selectedLanguage: number, editedName: EntityName) => {
        let _data:EntityName[] = names.reduce((res: EntityName[], name: EntityName) => {
        if (name.uuid === editedName.uuid) {
            res.push({
                ...editedName,  language_id: selectedLanguage
            })
        } else {
            res.push(name)
        }
        return res
        }, [] as EntityName[])
        props.onUpdate(_data)
    }

        //@ts-ignore
    const onSetDefault = (editedName: EntityName) => {
        let _data:EntityName[] = names.reduce((res: EntityName[], name: EntityName) => {
            if (name.uuid === editedName.uuid) {
                res.push({
                    ...editedName, default: true
                })
            } else {
                res.push({
                    ...name, default: false
                })
            }
            return res
        }, [] as EntityName[])
        props.onUpdate(_data)
    }

    const getLanguage = (languageId:string) => {
        for (let i = 0; i < languageOptions.length; i++) {
            if (languageOptions[i].id === languageId) {
                return languageOptions[i].name
            }
        }
    }

    const addNewEntityNames = () => {
        let _data:EntityName[] = names.map((name) => {
            return {
                ...name
            }
        })
        let _new_item:EntityName = {
            id: 0,
            default: false,
            language_id: 1,
            name: '',
            uuid: uuidv4()
        }
        _data.push(_new_item)
        props.onUpdate(_data)
    }

    const deleteEntityNames = (deletedName: EntityName) => {
        let _data:EntityName[] = names.reduce((res, name) => {
            if (name.id !== deletedName.id) {
                res.push({
                    ...name, language_id: 1
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
                if (name.uuid === editedName.uuid) {
                    res.push({
                        id: editedName.id,
                        default: names.length === 1 ? true : editedName.default,
                        language_id: editedName.language_id,
                        name: e.target.value,
                        uuid: editedName.uuid
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

    return (
        <Grid container flexDirection={'row'}  sx={{alignItems: 'flex-start'}}>
            <Grid item>
                <TableContainer component={Paper} sx={{minWidth: '465px'}}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Default</TableCell>
                                <TableCell>Name</TableCell>
                                <TableCell>Language</TableCell>
                                <TableCell></TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {names && names.length ? names.map((name, index) => (
                                <TableRow key={index}>
                                    <TableCell>
                                        {index === editableIdx ? (
                                          <Radio
                                              checked={name.default}
                                              value={name.name}
                                              onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                                                    onSetDefault(name)
                                                }}
                                              name="radio-buttons"
                                              inputProps={{ 'aria-label': name.name }}
                                            />
                                        ) : name.default ? 'Default': ''}
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
                                        {index === editableIdx ? (
                                            <Select
                                                labelId="language-select-label"
                                                id="language-select"
                                                value={name.language_id as unknown as string}
                                                onChange={(event: SelectChangeEvent) => {
                                                    onSelectLanguage(event.target.value as unknown as number, name)
                                                }}
                                            >
                                                { languageOptions.map((value, index) => {
                                                    return <MenuItem
                                                      key={index}
                                                      value={value.id}>
                                                        {value.name}
                                                    </MenuItem>
                                                })}
                                            </Select>
                                        ) : getLanguage(name.language_id as unknown as string)}
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
                <AddButton text={'Add Names'} variant={'secondary'} onClick={addNewEntityNames}/>
            </Grid>
        </Grid>
    )
}