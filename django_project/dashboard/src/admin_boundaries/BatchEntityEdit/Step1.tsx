import React, {useState, useEffect} from "react";
import '../../styles/LayerUpload.scss';
import {
    FormControl, 
    Grid,
    Typography} from "@mui/material";
import axios from "axios";
import LoadingButton from '@mui/lab/LoadingButton';
import {NameField, IdField, IdType} from "../../models/upload";
import Loading from "../../components/Loading";
import NameFieldFormControl from "../../components/Uploads/NameFieldFormControl";
import IdFieldFormControl from "../../components/Uploads/IdFieldFormControl";
import AddIdType, {NewIdTypeInterface} from "../../components/Uploads/AddIdType";
import AttributeSelect from "../../components/Uploads/AttributeSelect"
import Scrollable from '../../components/Scrollable';
import { BatchEntityEditInterface } from "../../models/upload";
import {LanguageOption, fetchLanguages} from "../../utils/Requests";
import HtmlTooltip from "../../components/HtmlTooltip";

const LOAD_ID_TYPE_LIST_URL = '/api/id-type/list/'


interface Step1Interface {
    batchEdit: BatchEntityEditInterface,
    onBackClicked: () => void,
    onClickNext: (ucodeField: string, nameFields: NameField[], idFields: IdField[], onSaved: (error?: string) => void) => void,
}

export default function Step1(props: Step1Interface) {
    const [loading, setLoading] = useState(true)
    const [saveLoading, setSaveLoading] = useState(false)
    const [idTypes, setIdTypes] = useState<IdType[]>([])
    const [attributes, setAttributes] = useState<string[]>(props.batchEdit.headers)
    const [nameFields, setNameFields] = useState<NameField[]>(
      props.batchEdit.name_fields || [])
    const [idFields, setIdFields] = useState<IdField[]>(
      props.batchEdit.id_fields || []
    )
    const [showAddIdType, toggleShowAddIdType] = useState(false)
    const [newIdType, setNewIdType] = useState<NewIdTypeInterface>()
    const [languageOptions, setLanguageOptions] = useState<[] | LanguageOption[]>([])
    const [enableSaveLevelButton, setEnableSaveLevelButton] = useState(false)
    const [ucodeField, setUcodeField] = useState<string>(props.batchEdit.ucode_field || '')

    useEffect(() => {
        // validate if all required fields have value
        let _error = validateFieldConfig()
        setEnableSaveLevelButton(_error === '')
      },
      [
        nameFields, idFields, ucodeField
      ])

    const setIsDirty = (val:boolean) => {
        
    }

    const onSaveClick = () => {
        setSaveLoading(true)
        props.onClickNext(ucodeField, nameFields, idFields, (error?: string) => {
            setSaveLoading(false)
        })
    }

    useEffect(() => {
        let fetch_apis = []
        fetch_apis.push(
          axios.get(LOAD_ID_TYPE_LIST_URL)
        )
        fetch_apis.push(
          fetchLanguages() as any
        )
        Promise.all(fetch_apis).then((responses) => {
            setLoading(false)
            setIdTypes(responses[0].data)
            setLanguageOptions(responses[1])
          }).catch(error => {
            setLoading(false)
          })
    
          if (nameFields.length === 0) {
              setNameFields([{
                  id: '1',
                  selectedLanguage: '',
                  field: '',
                  default: false,
                  label: ''
              }])
          }
          if (idFields.length === 0) {
            setIdFields([{
                id: '1',
                field: '',
                idType: null,
                default: false
            }])
        }
    }, [])

    const handleNameLanguageChange = (
        nameFieldId: string,
        languageId?: string,
        field?: string,
        label?: string,
        clearedFieldName?: string) => {
        const updatedNameFields = nameFields.map((nameField, index) => {
            if (nameField.id === nameFieldId) {
                if (languageId !== null) {
                    nameField.selectedLanguage = languageId
                } else if (clearedFieldName === 'language') {
                    nameField.selectedLanguage = ''
                }
                if (field) {
                    nameField.field = field
                } else if (clearedFieldName === 'nameField') {
                    nameField.field = ''
                }
                if (label !== null) {
                    nameField.label = label
                } else if (clearedFieldName === 'label') {
                    nameField.label = ''
                }
                nameField.duplicateError = false
            }
            return nameField
        })
        setNameFields(updatedNameFields)
        setIsDirty(true)
    }
  
    const handleIdTypeChange = (
        idFieldId: string,
        idTypeId?: string,
        field?: string,
        clearedFieldName?: string) => {
            const idType = idTypes.find(idType => idType.id == idTypeId)
            const updatedIdFields = idFields.map(idField => {
                if (idField.id === idFieldId) {
                    if (idType) {
                        idField.idType = idType
                    }
                    if (field) {
                        idField.field = field
                    } else if (clearedFieldName === 'idField') {
                        idField.field = ''
                    }
                }
                return idField
            })
            setIdFields(updatedIdFields)
            setIsDirty(true)
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
        // Check at least there is 1 name/id field selected
        if (nameFields.length === 0 && idFields.length === 0)
            return 'Empty Id Fields and Name Fields'
        let validNameFields = nameFields.filter(item => item.field && item.selectedLanguage)
        let validIdFields = idFields.filter(item => item.field && item.idType)
        if (validNameFields.length === 0 && validIdFields.length === 0)
            return 'Empty Id Fields and Name Fields'
        let _noDupNames = validateNoDuplicateNameLabel()
        if (!_noDupNames) {
            return 'Duplicate Label in Name Fields'
        }
        if (ucodeField.trim() === '')
            return 'ucode field'
        // check if all name fields are valid
        if (nameFields.length > 0) {
            let invalidNameFields = nameFields.filter(item => !(item.field && item.selectedLanguage))
            if (invalidNameFields.length > 0)
                return 'Invalid Name Field'
        }
        if (idFields.length > 0) {
            let invalidIdFields = idFields.filter(item => !(item.field && item.idType))
            if (invalidIdFields.length > 0)
                return 'Invalid Id Field'
        }
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

    const removeNameField = (id:string) => {
        let update_name_fields = nameFields.filter( nameField => {
          return nameField.id !== id
        })
        setNameFields(update_name_fields)
        setIsDirty(true)
    }
  
    const removeIdField = (id:string) => {
        let update_id_fields = idFields.filter( idField => {
            return idField.id !== id
        })
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

    return (
        <Scrollable>
            <div className="Step3Container Step4Container">
                <Grid container className='Step2' flexDirection='column' flex={1}>
                    <Grid item>
                        <div className='FormContainer'>
                            {!loading ? (
                                <FormControl className='FormContent' disabled={props.batchEdit.is_read_only || saveLoading}>
                                    <Grid container columnSpacing={2}>
                                        <Grid item xl={9} md={9} xs={12}>
                                            <Grid container columnSpacing={1}>
                                                <Grid container className='field-container' columnSpacing={1}>
                                                    <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                                        <Typography variant={'subtitle1'}>UCODE Field</Typography>
                                                    </Grid>
                                                    <Grid item md={8} xl={8} xs={12}>
                                                        <Grid container>
                                                            <Grid item md={11} xl={11} xs={12}>
                                                                <AttributeSelect
                                                                    id={'ucode-field'}
                                                                    name={'Ucode Field'}
                                                                    value={ucodeField}
                                                                    attributes={attributes}
                                                                    selectionChanged={(value: any) => {
                                                                        setUcodeField(value)
                                                                        setIsDirty(true)
                                                                    }}
                                                                    required={true}
                                                                    isReadOnly={props.batchEdit.is_read_only || saveLoading}
                                                                />
                                                            </Grid>
                                                            <Grid item md={1} xs={12} textAlign="left"></Grid>
                                                        </Grid>
                                                    </Grid>
                                                </Grid>
                                                <Grid container className='field-container align-start' columnSpacing={1}>
                                                    <Grid item className={'form-label multi-inputs'} md={4} xl={4} xs={12}>
                                                        <Typography variant={'subtitle1'}>
                                                            Name Fields
                                                            <HtmlTooltip tooltipTitle='Name Fields'
                                                                tooltipDescription={<p>Existing entity name with the same label will be overwritten.</p>}
                                                            />
                                                        </Typography>
                                                    </Grid>
                                                    <Grid item md={8} xl={8} xs={12}>
                                                        {nameFields.map((nameField: NameField, index: Number) => (
                                                            <NameFieldFormControl nameField={nameField} index={index} key={nameField.id}
                                                            languageOptions={languageOptions} attributes={attributes}
                                                            handleNameLanguageChange={handleNameLanguageChange} removeNameField={removeNameField}
                                                            isReadOnly={props.batchEdit.is_read_only || saveLoading} addNameField={addNameField} hideCheckbox={true} />
                                                        ))}
                                                    </Grid>
                                                </Grid>
                                                <Grid container className='field-container align-start' columnSpacing={1}>
                                                    <Grid item className={'form-label multi-inputs'} md={4} xl={4} xs={12}>
                                                        <Typography variant={'subtitle1'}>
                                                            Id Fields
                                                            <HtmlTooltip tooltipTitle='Id Fields'
                                                                tooltipDescription={<p>Existing entity id with the same id type will be overwritten unless it is a default code.</p>}
                                                            />
                                                        </Typography>
                                                    </Grid>
                                                    <Grid item md={8} xl={8} xs={12}>
                                                        {idFields.map((idField: IdField, index: number) => (
                                                        <IdFieldFormControl idField={idField} index={index} key={idField.id}
                                                            idTypes={idTypes} attributes={attributes}
                                                            handleIdTypeChange={handleIdTypeChange} removeIdField={removeIdField}
                                                            isReadOnly={props.batchEdit.is_read_only || saveLoading} addIdField={addIdField}
                                                            handleOnNewIdType={handleOnNewIdType} hideCheckbox={true} />
                                                        ))}
                                                    </Grid>
                                                </Grid>
                                            </Grid>
                                        </Grid>
                                        <Grid item xl={3} md={3} xs={12}></Grid>
                                    </Grid>
                                </FormControl>
                            ) : (
                                <div className="form-loading-container"><Loading/></div>
                            )}
                            
                        </div>
                        
                    </Grid>
                </Grid>
                <div className='button-container button-submit-container'>
                    <Grid container direction='row' justifyContent='space-between' spacing={1}>
                        <Grid item>
                            <LoadingButton loading={loading || saveLoading} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => props.onBackClicked()} variant="outlined">
                                Back
                            </LoadingButton>
                        </Grid>
                        <Grid item>
                            <LoadingButton loading={loading || saveLoading} disabled={!enableSaveLevelButton} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => onSaveClick()} variant="contained" sx={{width: '220px !important'}}>
                                { props.batchEdit.is_read_only ? 'Next' : 'Validate and Preview' }
                            </LoadingButton>
                        </Grid>
                    </Grid>
                </div>
                <AddIdType open={showAddIdType} initialIdType={newIdType} onClosed={addIdTypeOnClose} onSubmitted={addIdTypeOnSubmitted} />
            </div>
        </Scrollable>
    )
}
