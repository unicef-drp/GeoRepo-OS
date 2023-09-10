import React, {useEffect, useState} from 'react';
import {useNavigate} from "react-router-dom";
import Box from '@mui/material/Box';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import EntityEditInterface from '../../models/entity';
import EntityCodesInput from './EntityEditFormCodes';
import EntityNamesInput from './EntityEditFormNames';
import Loading from "../../components/Loading";
import AlertMessage from '../../components/AlertMessage';
import {postData} from "../../utils/Requests";
import Select, {SelectChangeEvent} from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import {EntityCode, EntityName} from '../../models/entity'
import Scrollable from '../../components/Scrollable';
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import axios from "axios";
import AlertDialog from "../../components/AlertDialog";

interface EntityDetailGeneralInterface {
    entity: EntityEditInterface;
    onEntityUpdated: () => void;
}

const SAVE_ENTITY_DETAIL_URL = '/api/entity/edit/'

const PRIVACY_LEVEL = [
  1,
  2,
  3,
  4
]

const filterEntityTypeList = createFilterOptions<string>();

const LOAD_ENTITY_TYPE_LIST_URL = '/api/entity-type/list/'

export default function EntityEditForm(props: EntityDetailGeneralInterface) {
    const [loading, setLoading] = useState(false)
    const [source, setSource] = useState<string>(props.entity.source)
    const [privacyLevel, setPrivacyLevel] = useState<number>(props.entity.privacy_level)
    const [entityType, setEntityType] = useState<string>(props.entity.type)
    const [entityTypes, setEntityTypes] = useState<string[]>()
    const [codes, setCodes] = useState<EntityCode[]>(props.entity.codes)
    const [names, setNames] = useState<EntityName[]>(props.entity.names)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [alertLoading, setAlertLoading] = useState<boolean>(false)
    const [alertOpen, setAlertOpen] = useState(false)

    const navigate = useNavigate()

    const saveEntityDetail = (id: number) => {
        setLoading(true)
        postData(
            `${SAVE_ENTITY_DETAIL_URL}${id}/`,
            {
                'id': props.entity.id,
                'type': entityType,
                'privacy_level': privacyLevel,
                'source': source,
                'codes': codes,
                'names': names
            }
        ).then(
            response => {
                setLoading(false)
                setAlertMessage('Successfully update Entity!')
                setAlertOpen(false)
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
                alert('Error updating Entity!')
            }
            setAlertOpen(false)
        })
    }

    const handleSaveClick = () => {
        setAlertOpen(true)
    }

    const onConfirmationClosed = () => {
      setAlertOpen(false)
    }

    const onConfirmedAlert = ()  => {
        saveEntityDetail(props.entity.id)
    }

    useEffect(() => {
      axios.get(`${LOAD_ENTITY_TYPE_LIST_URL}?mode=all`).then(
        response => {
            setEntityTypes(response.data)
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

    return (
        <Scrollable>
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => {
                    props.onEntityUpdated()
                }} />
                <div className='FormContainer'>
                    <FormControl className='FormContent'>
                        <Grid container columnSpacing={2} rowSpacing={2}>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Source</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={loading}
                                    id="input_source"
                                    hiddenLabel={true}
                                    type={"text"}
                                    onChange={val => setSource(val.target.value)}
                                    value={source}
                                    inputProps={{ maxLength: 150}}
                                    sx={{ width: '50%' }}
                                />
                            </Grid>
                        </Grid>
                        <Grid container columnSpacing={2} rowSpacing={2}>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Entity Type</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                              <FormControl sx={{width: '50%'}}>
                                <Autocomplete
                                  className="entity-type-search"
                                  value={entityType}
                                  onChange={(event, newValue: string|null) => {
                                    if (newValue !== null)
                                      setEntityType(newValue.replace('Add "', '').replace(/"/g,''))
                                    else
                                      setEntityType('')
                                  }}
                                  filterOptions={(options, params) => {
                                    const filtered = filterEntityTypeList(options, params)
                                    if (params.inputValue !== '') {
                                      filtered.push(`Add "${params.inputValue}"`)
                                    }
                                    return filtered
                                  }}
                                  options={entityTypes}
                                  getOptionLabel={(option) => {
                                    return option
                                  }}
                                  selectOnFocus
                                  clearOnBlur
                                  handleHomeEndKeys
                                  renderOption={(props, option) => <li {...props}>{option}</li>}
                                  freeSolo
                                  renderInput={(params) => <TextField {...params} placeholder="Entity Type" />}
                                  disableClearable
                                />
                              </FormControl>
                            </Grid>
                        </Grid>
                        <Grid container columnSpacing={2} rowSpacing={2}>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Privacy Level</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <Select
                                    labelId="privacy-level-select-label"
                                    id="privacy-level-select"
                                    value={privacyLevel as unknown as string}
                                    onChange={(event: SelectChangeEvent) => {
                                        setPrivacyLevel(event.target.value as unknown as number)
                                    }}
                                >
                                    { PRIVACY_LEVEL.map((value, index) => {
                                        return <MenuItem key={index} value={value}>{value}</MenuItem>
                                    })}
                                </Select>
                            </Grid>
                        </Grid>
                        <Grid container columnSpacing={2} rowSpacing={2}>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Codes</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                              <EntityCodesInput codes={codes} onUpdate={setCodes} />
                            </Grid>
                        </Grid>
                        <Grid container columnSpacing={2} rowSpacing={2}>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Names</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                              <EntityNamesInput names={names} onUpdate={setNames} />
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
                            <Grid item>
                              <AlertDialog open={alertOpen} alertClosed={onConfirmationClosed}
                                alertConfirmed={onConfirmedAlert}
                                alertLoading={alertLoading}
                                alertDialogTitle={`Saving Entity ${names[0].name}`}
                                alertDialogDescription={'Are you sure all edits have been made?'} />
                            </Grid>
                        </Grid>
                    </FormControl>
                </div>
            </Box>
        </Box>
        </Scrollable>
    )

}
