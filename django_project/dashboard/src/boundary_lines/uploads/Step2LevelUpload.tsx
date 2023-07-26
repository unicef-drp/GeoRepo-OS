import React, {useEffect, useState} from "react";
import FormControl from "@mui/material/FormControl";
import RadioGroup from "@mui/material/RadioGroup";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Modal from "@mui/material/Modal";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import FormLabel from "@mui/material/FormLabel";
import FormControlLabel from "@mui/material/FormControlLabel";
import Radio from "@mui/material/Radio";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from '@mui/material/MenuItem';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import '../../styles/LayerUpload.scss';
import LoadingButton from "@mui/lab/LoadingButton";
import axios from "axios";
import {postData} from "../../utils/Requests";
import {UploadInterface, IdField, IdType} from "../../models/upload";
import SaveLayerConfig, { LayerConfigInterface } from "../../views/UploadConfigs/SaveLayerConfig";
import LoadLayerConfig from "../../views/UploadConfigs/LoadLayerConfig";
import Scrollable from "../../components/Scrollable";
import Loading from "../../components/Loading";
import AttributeSelect from "../../components/Uploads/AttributeSelect"
import IdFieldFormControl from "../../components/Uploads/IdFieldFormControl";
import AddIdType, {NewIdTypeInterface} from "../../components/Uploads/AddIdType";


interface LevelUploadInterface {
    uploadData: UploadInterface,
    onBackClicked: Function,
    isReadOnly: boolean,
    updateLeveData?: Function,
    setFormIsDirty?: Function,
    canResetProgress?: boolean,
    onResetProgress?: () => void
}

const LOAD_ID_TYPE_LIST_URL = '/api/id-type/list/'


export default function Step2LevelUpload(props: LevelUploadInterface) {
    const [formLoading, setFormLoading] = useState<boolean>(true)
    const [idTypes, setIdTypes] = useState<IdType[]>([])
    const [attributes, setAttributes] = useState<string[]>([])
    const [idFields, setIdFields] = useState<IdField[]>(
      props.uploadData.id_fields || []
    )
    const [loading, setLoading] = useState<boolean>(false)
    const [boundaryTypeField, setBoundaryTypeField] =
      useState<string>(props.uploadData.boundary_type || "")
    const [showSaveConfig, setShowSaveConfig] = useState(false)
    const [saveConfigData, setSaveConfigData] = useState<UploadInterface>()
    const [showLoadConfig, setShowLoadConfig] = useState(false)
    const [showSuccessMessage, setShowSuccessMessage] = useState(false)
    const [successMessage, setSuccessMessage] = useState<string>("")
    const [showAddIdType, toggleShowAddIdType] = useState(false)
    const [newIdType, setNewIdType] = useState<NewIdTypeInterface>()
    const [enableSaveLevelButton, setEnableSaveLevelButton] = useState(false)
    const [defaultIdFieldId, setDefaultIdFieldId] = useState('')
    const [privacyLevelSelection, setPrivacyLevelSelection] =
      useState<string>(props.uploadData.privacy_level !== '' ? 'user_input':'privacy_level_field')
    const [privacyLevelField, setPrivacyLevelField] =
      useState<string>(props.uploadData.privacy_level_field || "")
    const [privacyLevel, setPrivacyLevel] =
      useState<string>(props.uploadData.privacy_level || "")

    const setIsDirty = (val:boolean) => {
      if (props.setFormIsDirty) {
        props.setFormIsDirty(val)
      }
    }

    useEffect(() => {
      // validate if all required fields have value
      let _error = validateFieldConfig()
      setEnableSaveLevelButton(_error === '')
    },
    [
      idFields, boundaryTypeField,
      privacyLevelSelection, privacyLevel, privacyLevelField
    ])

    const prepareUploadData = () => {
        const updatedUploadData = props.uploadData
        let _filtered_id_fields = idFields.filter((id_field) => {
            return id_field.idType !== null && id_field.field !== ''
        })
        updatedUploadData.id_fields = _filtered_id_fields
        updatedUploadData.boundary_type = boundaryTypeField
        updatedUploadData.privacy_level_field = privacyLevelField
        updatedUploadData.privacy_level = privacyLevel
    }

    const onSaveClick = () => {
        setLoading(true)

        prepareUploadData()
        postData((window as any).updateLayerUpload, props.uploadData).then(
          response => {
              props.updateLeveData(response.data)
              // remove isDirty once data is saved
              setIsDirty(false)
              setLoading(false)
          }
        ).catch(error => alert('Error saving level...'))
    }

    useEffect(() => {
      let fetch_apis = []
      fetch_apis.push(
        axios.get(`/api/layer-attributes/?id=${props.uploadData.id}`)
      )
      fetch_apis.push(
        axios.get(LOAD_ID_TYPE_LIST_URL)
      )
      Promise.all(fetch_apis).then((responses) => {
        setFormLoading(false)
        setAttributes(responses[0].data)
        setIdTypes(responses[1].data)
      }).catch(error => {
        setFormLoading(false)
      })
      if (idFields.length === 0) {
          setIdFields([{
              id: '1',
              field: '',
              idType: null,
              default: true
          }])
          setDefaultIdFieldId('1')
      } else {
        let _default = idFields.findIndex(idField => idField.default)
        _default = _default === -1 ? 0 : _default
        setDefaultIdFieldId(idFields[_default].id)
      }
    }, [])

    const handleIdTypeChange = (
      idFieldId: string,
      idTypeId?: string,
      field?: string) => {
        if (idTypeId === null && field === '') {
            // need to remove
            const updatedIdFields = idFields.map(idField => {
                if (idField.id === idFieldId) {
                    idField.idType = null
                    idField.field = ''
                }
                return idField
            })
            setIdFields(updatedIdFields)
        } else {
            const idType = idTypes.find(idType => idType.id == idTypeId)
            const updatedIdFields = idFields.map(idField => {
                if (idField.id === idFieldId) {
                    if (idType) {
                        idField.idType = idType
                    }
                    if (field) {
                        idField.field = field
                    }
                }
                return idField
            })
            setIdFields(updatedIdFields)
        }
        setIsDirty(true)
    }

    const addIdField = () => {
        let lastId = 0;
        for (const idField of idFields) {
            const idFieldId = parseInt(idField.id)
            if (lastId < idFieldId) {
                lastId = idFieldId
            }
        }
        lastId += 1
        setIdFields([
            ...idFields,
            {
                id: lastId + '',
                field: '',
                idType: null,
                default: false
            }
        ])
        setIsDirty(true)
    }

    const validateFieldConfig = ():string => {
      // Check Boundary Type Field
      if (boundaryTypeField === '')
        return 'Boundary Type Field'
      // Check Privacy Level Field
      if (privacyLevelField === '' && privacyLevel === '')
        return 'Privacy Level Field'
      return ''
    }

    const showSaveConfigModal = () => {
      let validateConfigErr = validateFieldConfig()
      if (validateConfigErr !== '') {
        alert('Invalid config: '+validateConfigErr+'!')
        return
      }
      prepareUploadData()
      setSaveConfigData(props.uploadData)
      setShowSaveConfig(true)
    }

    const loadConfigOnSuccess = (config: LayerConfigInterface) => {
      // apply the config to the data
      setIdFields(config.id_fields)
      setBoundaryTypeField(config.boundary_type)
      setPrivacyLevel(config.privacy_level)
      setPrivacyLevelField(config.privacy_level_field)
      setPrivacyLevelSelection(config.privacy_level !== '' ? 'user_input':'privacy_level_field')
      setShowLoadConfig(false)
      setIsDirty(true)
    }

    const saveConfigOnSuccess = () => {
      setShowSaveConfig(false)
      setSuccessMessage('Layer config has been successfully saved!')
      setShowSuccessMessage(true)
    }

    const removeIdField = (id:string) => {
      let update_id_fields = idFields.filter( idField => {
        return idField.id !== id
      })
      if (update_id_fields.length && update_id_fields.filter(t => t.default).length === 0) {
        update_id_fields[0].default = true
        setDefaultIdFieldId(update_id_fields[0].id)
      }
      setIdFields(update_id_fields)
      setIsDirty(true)
    }

    const addIdTypeOnClose = () => {
      setNewIdType(null)
      toggleShowAddIdType(false)
    }

    const addIdTypeOnSubmitted = (newIdType: NewIdTypeInterface, idType: IdType) => {
      // add new id type to list
      setIdTypes([...idTypes, idType])
      // set id type to newly added one
      setIdFields(idFields.map(idField => {
        if (idField.id === newIdType.id) {
          idField.idType = idType
        }
        return idField
      }))
      setIsDirty(true)
      addIdTypeOnClose()
    }

    const handleOnNewIdType = (idField: IdField, newValue: any) => {
      setNewIdType({
        name: newValue.replace('Add "', '').replace(/"/g,''),
        id: idField.id
      })
      toggleShowAddIdType(true)
    }

    const handlePrivacyLevelSelectionOnChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      let _value = (event.target as HTMLInputElement).value
      if (_value==='privacy_level_field') {
        setPrivacyLevel('')
      } else {
        setPrivacyLevelField('')
        setPrivacyLevel('4')
      }
      setPrivacyLevelSelection(_value)
      setIsDirty(true)
    }

    return (
        <Scrollable>
            <div className='FormContainer'>
            {
                !formLoading ? (
                  <FormControl className='FormContent' disabled={props.isReadOnly}>
                      <Grid container columnSpacing={2}>
                          <Grid item xl={9} md={9} xs={12}>
                            <Grid container className='field-container' columnSpacing={1}>
                                  <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    {privacyLevelSelection==='privacy_level_field' && (<Typography variant={'subtitle1'}>Privacy Level Field</Typography>)}
                                    {privacyLevelSelection==='user_input' && (<Typography variant={'subtitle1'}>Privacy Level</Typography>)}
                                  </Grid>
                                  <Grid item md={8} xl={8} xs={12}>
                                      <Grid container>
                                        <Grid item md={11} xl={11} xs={12}>
                                          <Grid container flexDirection={'row'} sx={{alignItems: 'center'}}>
                                            <Grid item>
                                              <FormControl sx={{width: '100%', marginBottom:  '20px'}} disabled={props.isReadOnly}>
                                                <FormLabel id="privacy-level-radio-buttons-group-label" className='form-sublabel'>Select From</FormLabel>
                                                <RadioGroup
                                                    row
                                                    aria-labelledby="privacy-level-radio-buttons-group-label"
                                                    name="privacy-level-radio-buttons-group"
                                                    value={privacyLevelSelection}
                                                    onChange={handlePrivacyLevelSelectionOnChange}
                                                  >
                                                  <FormControlLabel value="privacy_level_field" control={<Radio />} label="Fields" />
                                                  <FormControlLabel value="user_input" control={<Radio />} label="User Input" />
                                                </RadioGroup>
                                              </FormControl>
                                            </Grid>
                                            <Grid item sx={{flex: 1}}>
                                              { privacyLevelSelection==='privacy_level_field' && (<FormControl sx={{width: '100%'}}>
                                                  <AttributeSelect
                                                    id='privacy-level-field'
                                                    name={'Privacy Level Field'}
                                                    value={privacyLevelField}
                                                    attributes={attributes}
                                                    selectionChanged={(value: any) => {
                                                      setPrivacyLevelField(value as string)
                                                      setIsDirty(true)
                                                    }}
                                                    required
                                                    isReadOnly={props.isReadOnly}
                                                  />
                                              </FormControl>)}
                                              { privacyLevelSelection==='user_input' && (<FormControl sx={{width: '100%'}} disabled={props.isReadOnly}>
                                                <InputLabel id="privacy-level-select-label">Privacy Level</InputLabel>
                                                <Select
                                                  labelId="privacy-level-select-label"
                                                  id="privacy-level-select"
                                                  value={privacyLevel}
                                                  label="Privacy Level"
                                                  onChange={(event: SelectChangeEvent) => {
                                                    setPrivacyLevel(event.target.value as string)
                                                    setIsDirty(true)
                                                  }}
                                                >
                                                  <MenuItem value={'1'}>1</MenuItem>
                                                  <MenuItem value={'2'}>2</MenuItem>
                                                  <MenuItem value={'3'}>3</MenuItem>
                                                  <MenuItem value={'4'}>4</MenuItem>
                                                </Select>
                                              </FormControl>)}
                                            </Grid>
                                          </Grid>
                                        </Grid>
                                        <Grid item md={1} xs={12} textAlign="left"></Grid>
                                      </Grid>

                                  </Grid>
                            </Grid>
                            <Grid container className='field-container' columnSpacing={1}>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Boundary Type Field</Typography>
                                </Grid>
                                <Grid item md={8} xl={8} xs={12}>
                                    <Grid container>
                                        <Grid item md={11} xl={11} xs={12}>
                                        <AttributeSelect
                                            id={'boundary-type-field'}
                                            name={'Boundary Type Field'}
                                            value={boundaryTypeField}
                                            attributes={attributes}
                                            selectionChanged={(value: any) => {
                                                setBoundaryTypeField(value)
                                                setIsDirty(true)
                                            }}
                                            required
                                            isReadOnly={props.isReadOnly}
                                        />
                                        </Grid>
                                        <Grid item md={1} xs={12} textAlign="left"></Grid>
                                    </Grid>
                                </Grid>
                            </Grid>
                            <Grid container className='field-container align-start' columnSpacing={1}>
                                <Grid item className={'form-label multi-inputs'} md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Extra Id Fields</Typography>
                                </Grid>
                                <Grid item md={8} xl={8} xs={12}>
                                  <RadioGroup
                                    row
                                    aria-labelledby="id-field-radio-buttons-group-label"
                                    name="id-field-radio-buttons-group"
                                    value={defaultIdFieldId}
                                    onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                                    }}
                                  >
                                    {idFields.map((idField: IdField, index: number) => (
                                      <IdFieldFormControl idField={idField} index={index} key={idField.id}
                                        idTypes={idTypes} attributes={attributes}
                                        handleIdTypeChange={handleIdTypeChange} removeIdField={removeIdField}
                                        isReadOnly={props.isReadOnly} addIdField={addIdField}
                                        handleOnNewIdType={handleOnNewIdType} hideCheckbox={true} />
                                    ))}
                                  </RadioGroup>
                                </Grid>
                            </Grid>
                          </Grid>
                          <Grid item xl={3} md={3} xs={12}>
                              { !props.isReadOnly && (
                                <Grid container direction="row"
                                    justifyContent="flex-end"
                                    alignItems="center"
                                    spacing={2}>
                                <Grid item>
                                  <Button variant="contained" onClick={showSaveConfigModal}>Save Config</Button>
                                </Grid>
                                <Grid item>
                                  <Button variant="outlined" onClick={() => setShowLoadConfig(true)}>Load Config</Button>
                                </Grid>
                              </Grid>
                            )}
                          </Grid>
                      </Grid>
                  </FormControl>
                ) : <div className="form-loading-container"><Loading/></div>
            }
            <div className='button-container button-submit-container'>
                {loading ?
                  <LoadingButton loading loadingPosition="start"
                                startIcon={<div style={{width: 20}}/>}
                                variant="outlined">
                      Saving...
                  </LoadingButton> :
                  (<Grid container direction='row' justifyContent='space-between'>
                    <Grid item>
                      <Button onClick={() => props.onBackClicked()} variant="outlined">
                        Back
                      </Button>
                    </Grid>
                    <Grid item>
                      { props.canResetProgress && (
                        <Button onClick={props.onResetProgress} color={'warning'} variant="outlined" sx={{marginRight: '10px'}}>
                          Update Config
                        </Button>
                      )}
                      {!props.isReadOnly && (
                        <Button disabled={!enableSaveLevelButton} onClick={onSaveClick} variant="contained">
                          Save Level
                        </Button>
                      )}
                    </Grid>
                  </Grid>)
                }
            </div>
            <Modal open={showSaveConfig} onClose={() => setShowSaveConfig(false)}>
              <Box className="layer-config-modal">
                <h2>Save Config</h2>
                <SaveLayerConfig uploadData={saveConfigData}
                  languageOptions={[]}
                  handleOnBack={() => setShowSaveConfig(false)}
                  saveConfigOnSuccess={saveConfigOnSuccess} />
              </Box>
            </Modal>
            <Modal open={showLoadConfig} onClose={() => setShowLoadConfig(false)}>
              <Box className="layer-config-modal">
                <h2>Load Config</h2>
                <LoadLayerConfig level={props.uploadData.level}
                  attributes={attributes}
                  handleOnBack={() => setShowLoadConfig(false)}
                  loadOnSuccess={loadConfigOnSuccess} />
              </Box>
            </Modal>
            <AddIdType open={showAddIdType} initialIdType={newIdType} onClosed={addIdTypeOnClose} onSubmitted={addIdTypeOnSubmitted} />
            <Snackbar open={showSuccessMessage} autoHideDuration={6000}
              anchorOrigin={{vertical:'top', horizontal:'center'}}
              onClose={()=>setShowSuccessMessage(false)}>
              <Alert onClose={()=>setShowSuccessMessage(false)} severity="success" sx={{ width: '100%' }}>
                {successMessage}
              </Alert>
          </Snackbar>
        </div>
      </Scrollable>
    )
}

