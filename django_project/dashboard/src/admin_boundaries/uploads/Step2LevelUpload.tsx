import React, {useEffect, useState} from "react";
import '../../styles/LayerUpload.scss';
import {
    Button, 
    FormControl, 
    Grid,
    Typography,
    Modal,
    Box,
    Snackbar,
    Alert,
    TextField,
    Radio,
    FormLabel
} from "@mui/material";
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import {LanguageOption, postData} from "../../utils/Requests";
import LoadingButton from "@mui/lab/LoadingButton";
import Autocomplete, { createFilterOptions } from '@mui/material/Autocomplete';
import {UploadInterface, NameField, IdField, IdType} from "../../models/upload";
import axios from "axios";
import SaveLayerConfig, { LayerConfigInterface } from "../../views/UploadConfigs/SaveLayerConfig";
import LoadLayerConfig from "../../views/UploadConfigs/LoadLayerConfig";
import Scrollable from "../../components/Scrollable";
import Loading from "../../components/Loading";
import AttributeSelect from "../../components/Uploads/AttributeSelect"
import NameFieldFormControl from "../../components/Uploads/NameFieldFormControl";
import IdFieldFormControl from "../../components/Uploads/IdFieldFormControl";
import AddIdType, {NewIdTypeInterface} from "../../components/Uploads/AddIdType";
import PrivacyLevel from "../../models/privacy";

const LOAD_ID_TYPE_LIST_URL = '/api/id-type/list/'
const LOAD_ENTITY_TYPE_LIST_URL = '/api/entity-type/list/'
const FETCH_PRIVACY_LEVEL_LABELS = '/api/permission/privacy-levels/'

interface LevelUploadInterface {
    languageOptions: LanguageOption[],
    uploadData: UploadInterface,
    onBackClicked: Function,
    isReadOnly: boolean,
    isUpdatingStep: boolean,
    updateLeveData?: Function,
    setFormIsDirty?: Function,
    canResetProgress?: boolean,
    onResetProgress?: () => void
}

const filterEntityTypeList = createFilterOptions<string>();

function Step2LevelUpload(props: LevelUploadInterface) {
    const [formLoading, setFormLoading] = useState<boolean>(true)
    const [idTypes, setIdTypes] = useState<IdType[]>([])
    const [attributes, setAttributes] = useState<string[]>([])
    const [nameFields, setNameFields] = useState<NameField[]>(
      props.uploadData.name_fields || [])
    const [idFields, setIdFields] = useState<IdField[]>(
      props.uploadData.id_fields || []
    )
    const [loading, setLoading] = useState<boolean>(false)
    const [locationTypeField, setLocationTypeField] =
      useState<string>(props.uploadData.location_type_field || "")
    const [parentIdField, setParentIdField] =
      useState<string>(props.uploadData.parent_id_field || "")
    const [sourceField, setSourceField] =
      useState<string>(props.uploadData.source_field || "")
    const [showSaveConfig, setShowSaveConfig] = useState(false)
    const [saveConfigData, setSaveConfigData] = useState<UploadInterface>()
    const [showLoadConfig, setShowLoadConfig] = useState(false)
    const [showSuccessMessage, setShowSuccessMessage] = useState(false)
    const [successMessage, setSuccessMessage] = useState<string>("")
    const [showAddIdType, toggleShowAddIdType] = useState(false)
    const [newIdType, setNewIdType] = useState<NewIdTypeInterface>()
    const [entityType, setEntityType] =
      useState<string>(props.uploadData.entity_type || "")
    const [locationTypeSelection, setLocationTypeSelection] =
      useState<string>(props.uploadData.entity_type !== '' ? 'user_input':'location_type_field')
    const [entityTypes, setEntityTypes] = useState<string[]>([])
    const [enableSaveLevelButton, setEnableSaveLevelButton] = useState(false)
    const [defaultNameFieldId, setDefaultNameFieldId] = useState('')
    const [defaultIdFieldId, setDefaultIdFieldId] = useState('')
    const [privacyLevelSelection, setPrivacyLevelSelection] =
      useState<string>(props.uploadData.privacy_level !== '' ? 'user_input':'privacy_level_field')
    const [privacyLevelField, setPrivacyLevelField] =
      useState<string>(props.uploadData.privacy_level_field || "")
    const [privacyLevel, setPrivacyLevel] =
      useState<string>(props.uploadData.privacy_level || "")
    const [privacyLevelLabels, setPrivacyLevelLabels] = useState<PrivacyLevel>({})

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
      locationTypeSelection, locationTypeField, entityType, nameFields,
      idFields, parentIdField, sourceField,
      privacyLevelSelection, privacyLevel, privacyLevelField
    ])

    const onSaveClick = () => {
        setLoading(true)

        const updatedUploadData = props.uploadData
        updatedUploadData.location_type_field = locationTypeField
        updatedUploadData.parent_id_field = parentIdField
        updatedUploadData.source_field = sourceField
        updatedUploadData.name_fields = nameFields
        for (let name_field of updatedUploadData.name_fields) {
          if (typeof name_field.selectedLanguage === 'undefined')
              name_field.selectedLanguage = ''
          if (typeof name_field.label === 'undefined')
              name_field.label = ''
        }
        updatedUploadData.id_fields = idFields
        updatedUploadData.entity_type = entityType
        updatedUploadData.privacy_level_field = privacyLevelField
        updatedUploadData.privacy_level = privacyLevel

        postData((window as any).updateLayerUpload, props.uploadData).then(
          response => {
              props.updateLeveData(response.data)
              // remove isDirty once data is saved
              setIsDirty(false)
              setLoading(false)
              // reload entity type list
              axios.get(LOAD_ENTITY_TYPE_LIST_URL).then((response) => {
                setEntityTypes(response.data)
              }).catch(error => {
                console.log(error)
              })
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
      fetch_apis.push(
        axios.get(LOAD_ENTITY_TYPE_LIST_URL)
      )
      fetch_apis.push(
        axios.get(FETCH_PRIVACY_LEVEL_LABELS)
      )
      Promise.all(fetch_apis).then((responses) => {
        setFormLoading(false)
        setAttributes(responses[0].data)
        setIdTypes(responses[1].data)
        setEntityTypes(responses[2].data)
        setPrivacyLevelLabels(responses[3].data as PrivacyLevel)
      }).catch(error => {
        setFormLoading(false)
      })

      if (nameFields.length === 0) {
          setNameFields([{
              id: '1',
              selectedLanguage: '',
              field: '',
              default: true,
              label: ''
          }])
          setDefaultNameFieldId('1')
      } else {
        let _default = nameFields.findIndex(nameField => nameField.default)
        _default = _default === -1 ? 0 : _default
        setDefaultNameFieldId(nameFields[_default].id)
      }
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

    const handleNameLanguageChange = (
      nameFieldId: string,
      languageId?: string,
      field?: string,
      label?: string) => {
        const updatedNameFields = nameFields.map((nameField, index) => {
            if (nameField.id === nameFieldId) {
                if (languageId !== null) {
                    nameField.selectedLanguage = languageId
                }
                if (field) {
                    nameField.field = field
                }
                if (label !== null) {
                  nameField.label = label
                }
                nameField.duplicateError = false
            }
            return nameField
        })
        setNameFields(updatedNameFields);
        setIsDirty(true)
    }

    const handleIdTypeChange = (
      idFieldId: string,
      idTypeId?: string,
      field?: string) => {
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
        setIsDirty(true)
    }

    const handleDefaultChange = (event: SelectChangeEvent, fields: NameField[] | IdField[]) => {
        let fieldId = event.target.value;
        setIsDirty(true)
        return fields.map((field, index) => {
            field.default = field.id === fieldId;
            return field
        })
    }

    const addNameField = () => {
        let lastId = 0;
        for (const nameField of nameFields) {
            const nameFieldId = parseInt(nameField.id)
            if (lastId < nameFieldId) {
                lastId = nameFieldId
            }
        }
        lastId += 1
        setNameFields([
            ...nameFields,
            {
                id: lastId + '',
                selectedLanguage: '',
                field: '',
                default: false,
                label: ''
            }
        ])
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
      // Check Privacy Level Field
      if (privacyLevelField === '' && privacyLevel === '')
        return 'Privacy Level Field'
      // Check Location Type Field
      if (locationTypeField === '' && entityType === '')
        return 'Location Type Field'
      // Check at least there is 1 Name Fields - Languange + Name Field selected
      if (nameFields.length === 0)
        return 'Name Fields'
      let invalidNameFields = nameFields.filter(item => !(item.field && item.selectedLanguage))
      if (invalidNameFields.length > 0)
        return 'Name Fields'
      let _noDupNames = validateNoDuplicateNameLabel()
      if (!_noDupNames) {
        return 'Duplicate Label in Name Fields'
      }
      // Check at least there is 1 Id Fields - Type + Id Field selected
      if (idFields.length === 0)
        return 'Id Field'
      let invalidIdFields = idFields.filter(item => !(item.field && item.idType))
      if (invalidIdFields.length > 0)
        return 'Id Field'
      // Check Parent Id Field
      if (props.uploadData.level !== '0') {
        if (parentIdField === '')
          return 'Parent Id Field'
      }
      // source field is optional

      return ''
    }

    const validateNoDuplicateNameLabel = () => {
      let _nameFields = [...nameFields]
      let _existing:string[] = []
      let _isValid = true
      for (let _name of _nameFields) {
        if (_name.label) {
          if (_existing.indexOf(_name.label) > -1) {
            _name.duplicateError = true
            _isValid = false
            break
          }
          _existing.push(_name.label)
        }
      }
      if (!_isValid) {
        setNameFields(_nameFields)
      }

      return _isValid
    }

    const showSaveConfigModal = () => {
      let validateConfigErr = validateFieldConfig()
      if (validateConfigErr !== '') {
        alert('Invalid config: '+validateConfigErr+'!')
        return
      }
      const updatedUploadData = props.uploadData
      updatedUploadData.location_type_field = locationTypeField
      updatedUploadData.parent_id_field = parentIdField
      updatedUploadData.source_field = sourceField
      updatedUploadData.name_fields = nameFields
      updatedUploadData.id_fields = idFields
      updatedUploadData.entity_type = entityType
      updatedUploadData.privacy_level = privacyLevel
      updatedUploadData.privacy_level_field = privacyLevelField
      setSaveConfigData(updatedUploadData)
      setShowSaveConfig(true)
    }

    const loadConfigOnSuccess = (config: LayerConfigInterface) => {
      // apply the config to the data
      setLocationTypeField(config.location_type_field)
      setParentIdField(config.parent_id_field)
      setSourceField(config.source_field)
      setNameFields(config.name_fields)
      setIdFields(config.id_fields)
      setEntityType(config.entity_type)
      setLocationTypeSelection(config.entity_type !== '' ? 'user_input':'location_type_field')
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

    const removeNameField = (id:string) => {
      let update_name_fields = nameFields.filter( nameField => {
        return nameField.id !== id
      })
      if (update_name_fields.length && update_name_fields.filter(t => t.default).length === 0) {
        update_name_fields[0].default = true
        setDefaultNameFieldId(update_name_fields[0].id)
      }
      setNameFields(update_name_fields)
      setIsDirty(true)
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

    const handleLocationTypeSelectionOnChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      let _value = (event.target as HTMLInputElement).value
      if (_value==='location_type_field')
        setEntityType('')
      else
        setLocationTypeField('')
      setLocationTypeSelection(_value)
      setIsDirty(true)
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

    const clearSourceField = () => {
      setSourceField('')
      setIsDirty(true)
    }

    const handleOnNewIdType = (idField: IdField, newValue: any) => {
      setNewIdType({
        name: newValue.replace('Add "', '').replace(/"/g,''),
        id: idField.id
      })
      toggleShowAddIdType(true)
    }

    return (
        <Scrollable>
            <div className='FormContainer'>
            {
                !formLoading ? (
                  <FormControl className='FormContent' disabled={props.isReadOnly}>
                      <Grid container columnSpacing={2}>
                          <Grid item xl={9} md={9} xs={12}>
                              <Grid container columnSpacing={1}>
                                <Grid item className={'form-label multi-inputs'} md={4} xl={4} xs={12}>
                                </Grid>
                                <Grid item md={8} xl={8} xs={12} textAlign="left">
                                  <FormLabel className='form-sublabel'>Default</FormLabel>
                                </Grid>
                            </Grid>
                              <Grid container className='field-container align-start' columnSpacing={1}>
                                  <Grid item className={'form-label multi-inputs'} md={4} xl={4} xs={12}>
                                      <Typography variant={'subtitle1'}>Name Fields</Typography>
                                  </Grid>
                                  <Grid item md={8} xl={8} xs={12}>
                                      <RadioGroup
                                        row
                                        aria-labelledby="name-field-radio-buttons-group-label"
                                        name="name-field-radio-buttons-group"
                                        value={defaultNameFieldId}
                                        onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                                          let _value = (event.target as HTMLInputElement).value
                                          setDefaultNameFieldId(_value)
                                          setNameFields(
                                            handleDefaultChange(event, nameFields) as NameField[]
                                          )
                                        }}
                                      >
                                      {nameFields.map((nameField: NameField, index: Number) => (
                                        <NameFieldFormControl nameField={nameField} index={index} key={nameField.id}
                                          languageOptions={props.languageOptions} attributes={attributes}
                                          handleNameLanguageChange={handleNameLanguageChange} removeNameField={removeNameField}
                                          isReadOnly={props.isReadOnly} addNameField={addNameField} />
                                      ))}
                                    </RadioGroup>
                                  </Grid>
                              </Grid>
                              <Grid container columnSpacing={1}>
                                <Grid item className={'form-label multi-inputs'} md={4} xl={4} xs={12}>
                                </Grid>
                                <Grid item md={8} xl={8} xs={12} textAlign="left">
                                  <FormLabel className='form-sublabel'>Default</FormLabel>
                                </Grid>
                              </Grid>
                              <Grid container className='field-container align-start' columnSpacing={1}>
                                <Grid item className={'form-label multi-inputs'} md={4} xl={4} xs={12}>
                                    <Typography variant={'subtitle1'}>Id Fields</Typography>
                                </Grid>
                                <Grid item md={8} xl={8} xs={12}>
                                  <RadioGroup
                                    row
                                    aria-labelledby="id-field-radio-buttons-group-label"
                                    name="id-field-radio-buttons-group"
                                    value={defaultIdFieldId}
                                    onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                                      let _value = (event.target as HTMLInputElement).value
                                      setDefaultIdFieldId(_value)
                                      setIdFields(
                                        handleDefaultChange(event, idFields) as IdField[]
                                      )
                                    }}
                                  >
                                    {idFields.map((idField: IdField, index: number) => (
                                      <IdFieldFormControl idField={idField} index={index} key={idField.id}
                                        idTypes={idTypes} attributes={attributes}
                                        handleIdTypeChange={handleIdTypeChange} removeIdField={removeIdField}
                                        isReadOnly={props.isReadOnly} addIdField={addIdField}
                                        handleOnNewIdType={handleOnNewIdType} />
                                    ))}
                                  </RadioGroup>
                                </Grid>
                              </Grid>
                              { parseInt(props.uploadData.level) > 0 ?
                              <Grid container className='field-container' columnSpacing={1}>
                                    <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                        <Typography variant={'subtitle1'}>Parent Id Field</Typography>
                                    </Grid>
                                    <Grid item md={8} xl={8} xs={12}>
                                      <Grid container>
                                        <Grid item md={11} xl={11} xs={12}>
                                          <AttributeSelect
                                            id={'parent-id-field'}
                                            name={'Parent Id Field'}
                                            value={parentIdField}
                                            attributes={attributes}
                                            selectionChanged={(value: any) => {
                                              setParentIdField(value as string)
                                              setIsDirty(true)
                                            }}
                                            required
                                            isReadOnly={props.isReadOnly}
                                          />
                                        </Grid>
                                        <Grid item md={1} xs={12} textAlign="left"></Grid>
                                      </Grid>
                                    </Grid>
                                </Grid> : null }
                              <Grid container className='field-container' columnSpacing={1}>
                                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                  {locationTypeSelection==='location_type_field' && (<Typography variant={'subtitle1'}>Location Type Field</Typography>)}
                                  {locationTypeSelection==='user_input' && (<Typography variant={'subtitle1'}>Location Type</Typography>)}
                                </Grid>
                                <Grid item md={8} xl={8} xs={12}>
                                    <Grid container>
                                      <Grid item md={11} xl={11} xs={12}>
                                        <Grid container flexDirection={'row'} sx={{alignItems: 'center'}}>
                                          <Grid item>
                                            <FormControl sx={{width: '100%', marginBottom:  '20px'}} disabled={props.isReadOnly}>
                                              <FormLabel id="location-type-radio-buttons-group-label" className='form-sublabel'>Select From</FormLabel>
                                              <RadioGroup
                                                  row
                                                  aria-labelledby="location-type-radio-buttons-group-label"
                                                  name="location-type-radio-buttons-group"
                                                  value={locationTypeSelection}
                                                  onChange={handleLocationTypeSelectionOnChange}
                                                >
                                                <FormControlLabel value="location_type_field" control={<Radio />} label="Fields" />
                                                <FormControlLabel value="user_input" control={<Radio />} label="User Input" />
                                              </RadioGroup>
                                            </FormControl>
                                          </Grid>
                                          <Grid item sx={{flex: 1}}>
                                            { locationTypeSelection==='location_type_field' && (<FormControl sx={{width: '100%'}}>
                                                <AttributeSelect
                                                  id='location-type-field'
                                                  name={'Location Type Field'}
                                                  value={locationTypeField}
                                                  attributes={attributes}
                                                  selectionChanged={(value: any) => {
                                                    setLocationTypeField(value as string)
                                                    setIsDirty(true)
                                                  }}
                                                  required
                                                  isReadOnly={props.isReadOnly}
                                                />
                                            </FormControl>)}
                                            { locationTypeSelection==='user_input' && (<FormControl sx={{width: '100%'}}>
                                              <Autocomplete
                                                className="location-type-search"
                                                value={entityType}
                                                onChange={(event, newValue) => {
                                                  if (newValue !== null)
                                                    setEntityType(newValue.replace('Add "', '').replace(/"/g,''))
                                                  else
                                                    setEntityType('')
                                                  setIsDirty(true)
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
                                                renderInput={(params) => <TextField {...params} label="Location Type" />}
                                                disableClearable
                                                disabled={props.isReadOnly}
                                              />
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
                                                  <MenuItem value={'1'}>{`1${privacyLevelLabels[1] ? ' - ' + privacyLevelLabels[1] : ''}`}</MenuItem>
                                                  <MenuItem value={'2'}>{`2${privacyLevelLabels[2] ? ' - ' + privacyLevelLabels[2] : ''}`}</MenuItem>
                                                  <MenuItem value={'3'}>{`3${privacyLevelLabels[3] ? ' - ' + privacyLevelLabels[3] : ''}`}</MenuItem>
                                                  <MenuItem value={'4'}>{`4${privacyLevelLabels[4] ? ' - ' + privacyLevelLabels[4] : ''}`}</MenuItem>
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
                                      <Typography variant={'subtitle1'}>Source Field</Typography>
                                  </Grid>
                                  <Grid item md={8} xl={8} xs={12}>
                                    <Grid container>
                                      <Grid item md={11} xl={11} xs={12}>
                                        <AttributeSelect
                                          id={'source-field'}
                                          name={'Source Field'}
                                          value={sourceField}
                                          attributes={attributes}
                                          selectionChanged={(value: any) => {
                                            setSourceField(value)
                                            setIsDirty(true)
                                          }}
                                          onSelectionCleared={clearSourceField}
                                          isReadOnly={props.isReadOnly}
                                        />
                                      </Grid>
                                      <Grid item md={1} xs={12} textAlign="left"></Grid>
                                    </Grid>
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
                      <LoadingButton loading={props.isUpdatingStep} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => props.onBackClicked()} variant="outlined">
                        Back
                      </LoadingButton>
                    </Grid>
                    <Grid item>
                      { props.canResetProgress && !props.isUpdatingStep && (
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
                  languageOptions={props.languageOptions}
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

export default Step2LevelUpload;
