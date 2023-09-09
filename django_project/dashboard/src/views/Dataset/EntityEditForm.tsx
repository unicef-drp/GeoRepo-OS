import React, {useState} from 'react';
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

const ENTITY_TYPE = [
  "Country",
  "Region",
  "District",
  "Province",
  "City",
  "Municipality"
]


export default function EntityEditForm(props: EntityDetailGeneralInterface) {
    const [loading, setLoading] = useState(false)
    const [source, setSource] = useState<string>(props.entity.source)
    const [privacyLevel, setPrivacyLevel] = useState<number>(props.entity.privacy_level)
    const [entityType, setEntityType] = useState<number>(props.entity.type)
    const [codes, setCodes] = useState<EntityCode[]>(props.entity.codes)
    const [names, setNames] = useState<EntityName[]>(props.entity.names)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const navigate = useNavigate()
    const [updatedEntityId, setUpdatedEntityId] = useState(0)

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
                setUpdatedEntityId(response.data['id'])
                setAlertMessage('Successfully update Entity!')
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
        })
    }

    const handleSaveClick = () => {
        saveEntityDetail(props.entity.id)
    }

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
                                <Typography variant={'subtitle1'}>Entity Type</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <Select
                                    labelId="entity-type-select-label"
                                    id="entity-type-select"
                                    value={entityType as unknown as string}
                                    onChange={(event: SelectChangeEvent) => {
                                        setPrivacyLevel(event.target.value as unknown as number)
                                    }}
                                >
                                    { ENTITY_TYPE.map((value, index) => {
                                        return <MenuItem key={index} value={index + 1}>{value}</MenuItem>
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
                        </Grid>
                    </FormControl>
                </div>
            </Box>
        </Box>
        </Scrollable>
    )

}
