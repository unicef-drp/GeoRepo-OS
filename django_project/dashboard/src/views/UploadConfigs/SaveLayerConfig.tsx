import React, {useEffect, useState} from "react";
import '../../styles/LayerUploadConfig.scss';
import {
    Button,
    Grid,
    TextField,
    Typography
} from "@mui/material";
import LoadingButton from "@mui/lab/LoadingButton";
import {LanguageOption, postData} from "../../utils/Requests";
import {NameField, IdField, UploadInterface} from "../../models/upload";

const SAVE_CONFIG_URL = '/api/layer-config/save/'

export interface LayerConfigInterface {
    name: string,
    level: string,
    dataset_id: number,
    layer_upload_session: number,
    created_by: number,
    created_date: string,
    location_type_field?: string,
    parent_id_field?: string,
    source_field?: string,
    name_fields?: NameField[],
    id_fields?: IdField[],
    entity_type: string,
    boundary_type?: string,
    privacy_level_field?: string,
    privacy_level?: string
}

interface LayerSaveConfigInterface {
    uploadData: UploadInterface,
    languageOptions: LanguageOption[],
    handleOnBack: Function,
    saveConfigOnSuccess: Function
}

function FieldMapping(props: any) {
    return (
      <div>
        {
          props.fieldMapping.map((value: string, index: number) => (
            <div key={index}>{value}</div>
          ))
        }
      </div>
    )
  }

export default function SaveLayerConfig(props: LayerSaveConfigInterface) {
    const [loading, setLoading] = useState(false)
    const [configData, setConfigData] = useState<LayerConfigInterface>()
    const [fieldMapping, setFieldMapping] = useState<string[]>([])
    const [nameError, setNameError] = useState(false)

    useEffect(() => {
        if (props.uploadData === null)
            return
        setConfigData({
            ...configData,
            name: '',
            level: props.uploadData.level,
            layer_upload_session: props.uploadData.layer_upload_session,
            location_type_field: props.uploadData.location_type_field,
            parent_id_field: props.uploadData.parent_id_field,
            source_field: props.uploadData.source_field,
            name_fields: props.uploadData.name_fields,
            id_fields: props.uploadData.id_fields,
            entity_type: props.uploadData.entity_type,
            boundary_type: props.uploadData.boundary_type,
            privacy_level_field: props.uploadData.privacy_level_field,
            privacy_level: props.uploadData.privacy_level
        })
        let field_mapping = []
        if (props.uploadData.parent_id_field !== '')
            field_mapping.push('parent_id_field = ' + props.uploadData.parent_id_field)
        if (props.uploadData.source_field !== '')
            field_mapping.push('source_id_field = ' + props.uploadData.source_field)
        if (props.uploadData.privacy_level_field !== '')
            field_mapping.push('privacy_level_field = ' + props.uploadData.privacy_level_field)
        if (props.uploadData.privacy_level !== '')
            field_mapping.push('privacy_level = \'' + props.uploadData.privacy_level + '\'')
        if (props.uploadData.location_type_field !== '')
            field_mapping.push('location_type_field = ' + props.uploadData.location_type_field)
        if (props.uploadData.entity_type !== '')
            field_mapping.push('location_type = \'' + props.uploadData.entity_type + '\'')
        for (let name_field of props.uploadData.name_fields) {
            let language = props.languageOptions.filter(item => item.id === name_field.selectedLanguage)
                                                .map(item => item.name)
            let name_field_value = name_field['field']
            if (name_field['default'])
                name_field_value += ' (default)'
            let _label = name_field.label ? ` - ${name_field.label}` : ''
            let _lang = language.length ? ` (${language[0]})` : ''
            field_mapping.push(
                    'name_field'+ _label + _lang + ' = ' +
                    name_field_value
                )
        }
        for (let id_field of props.uploadData.id_fields) {
            let id_field_value = id_field['field']
            if (id_field['default'])
                id_field_value += ' (default)'
            field_mapping.push(
                'id_field (' + id_field['idType']['name'] + ') = ' +
                id_field_value
            )
        }
        if (props.uploadData.boundary_type !== '')
            field_mapping.push('boundary_type_field = ' + props.uploadData.boundary_type)
        setFieldMapping(field_mapping)
      }, [props.uploadData])

    const onSaveClick = () => {
        // validate mandatory for the name
        if (configData.name == '') {
            setNameError(true)
            return;
        }
        setNameError(false)
        setLoading(true)
        postData(SAVE_CONFIG_URL, configData).then(
            response => {
                setLoading(false)
                props.saveConfigOnSuccess();
            }
          ).catch(error => alert('Error saving level...'))
    }

    const onCancelClick = () => {
        props.handleOnBack();
    }

    const onNameChange = (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
        setConfigData({
            ...configData, 
            name: e.target.value
        })
    }

    return (<div className='layer-config-container'>
        <div id='layer-config-form'>
            <Grid container columnSpacing={1}>
                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                    <Typography variant={'subtitle1'}>Config Name</Typography>
                </Grid>
                <Grid item md={8} xl={8} xs={12}>
                    <TextField
                        disabled={loading}
                        id='input-config-name'
                        required
                        type={'text'}
                        onChange={onNameChange}
                        defaultValue=''
                        sx={{ width: '60%' }}
                        inputProps={{maxLength: 255}}
                        placeholder='Config Name'
                        error={nameError}
                        helperText={nameError?'Name is required.':''}
                    />
                </Grid>
            </Grid>
            <Grid container columnSpacing={1}>
                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                    <Typography variant={'subtitle1'}>Level</Typography>
                </Grid>
                <Grid item md={8} xl={8} xs={12}>
                    <Typography variant={'subtitle1'}>{'Level ' + props.uploadData.level}</Typography>
                </Grid>
            </Grid>
            <Grid container columnSpacing={1}>
                <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                    <Typography variant={'subtitle1'}>Field Mapping</Typography>
                </Grid>
                <Grid item md={8} xl={8} xs={12}>
                    <div>
                      <pre><FieldMapping fieldMapping={fieldMapping}/></pre>
                    </div>
                </Grid>
            </Grid>
        </div>
        <div className='button-submit-container'>
            {loading ?
              <LoadingButton loading loadingPosition='start'
                             startIcon={<div style={{width: 20}}/>}
                             variant='outlined'>
                  Saving...
              </LoadingButton> :
              <Grid container direction='row' 
                justifyContent='flex-end' 
                alignItems='center'
                spacing={2}>
                    <Grid item>
                        <Button onClick={onSaveClick} variant='contained'>
                            Save Config
                        </Button>
                    </Grid>
                    <Grid item>
                        <Button onClick={onCancelClick} variant='outlined'>
                            Cancel
                        </Button>
                    </Grid>
              </Grid>
            }
        </div>
    </div>)
}