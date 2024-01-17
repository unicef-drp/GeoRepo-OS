import React from "react";
import FormControlLabel from "@mui/material/FormControlLabel";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteIcon from '@mui/icons-material/Delete';
import AddCircleIcon from "@mui/icons-material/AddCircle";
import { useRadioGroup } from '@mui/material/RadioGroup';
import Radio from "@mui/material/Radio";
import { NameField } from "../../models/upload";
import AttributeSelect from "./AttributeSelect";
import { LanguageOption } from "../../utils/Requests";


interface NameFieldFormControlProps {
    nameField: NameField,
    languageOptions: LanguageOption[],
    attributes: string[],
    isReadOnly: boolean,
    index: Number,
    handleNameLanguageChange: (nameFieldId: string, languageId?: string, field?: string, label?: string) => void,
    removeNameField: (id: string) => void,
    addNameField: () => void,
    hideCheckbox?: boolean
  }
  
  export default function NameFieldFormControl(props: NameFieldFormControlProps) {
    const radioGroup = useRadioGroup();
  
    let checked = false;
  
    if (radioGroup) {
      checked = radioGroup.value === props.nameField.id;
    }
    return (
      <Grid container flexDirection={'column'}>
        <Grid container columnSpacing={1} className='field-container'>
          {!props.hideCheckbox && 
            <Grid item md={1} xs={12}>
              <FormControlLabel value={props.nameField.id} checked={checked} label='' disableTypography control={<Radio />} />
            </Grid>
          }          
          <Grid item md={3} xs={12}>
            <TextField 
              label={'Label'}
              type={"text"}
              value={props.nameField.label}
              onChange={val => props.handleNameLanguageChange(props.nameField.id, null, null, val.target.value)}
              disabled={props.isReadOnly}
              error={props.nameField.duplicateError}
              inputProps={{
                'maxLength': 10
              }}
              style={{width: '100%'}}
            />
          </Grid>
          <Grid item md={3} xs={12}>
              <AttributeSelect
                  id={'language-field-' + props.nameField.selectedLanguage}
                  name={'Language'}
                  value={props.nameField.selectedLanguage ? props.languageOptions.find(({id}) => id === props.nameField.selectedLanguage).name : '' }
                  attributes={props.languageOptions.map((languageOption: LanguageOption) => ({id: languageOption.id, label: languageOption.name}))}
                  selectionChanged={(value: any) => props.handleNameLanguageChange(props.nameField.id, value.id as string, null, null)}
                  onSelectionCleared={() => props.handleNameLanguageChange(props.nameField.id, '', null, null)}
                  isReadOnly={props.isReadOnly}
              />
          </Grid>
          <Grid item md={props.hideCheckbox?5:4} xs={12}>
            <AttributeSelect
              id={'name-field-' + props.nameField.id}
              name={'Name Field'}
              value={props.nameField.field}
              attributes={props.attributes}
              selectionChanged={(value: any) => props.handleNameLanguageChange(
                props.nameField.id, null, value as string, null)
              }
              required={!props.hideCheckbox}
              isReadOnly={props.isReadOnly}
            />
          </Grid>
          <Grid item md={1} xs={12} textAlign="left">
            { (props.index === 0 && !props.isReadOnly) ? (
              <IconButton aria-label="add" size="medium" onClick={()=>props.addNameField()}>
                <Tooltip title="Add Name Field">
                  <AddCircleIcon color="primary" />
                </Tooltip>
              </IconButton>
            ) : null }
            {(props.index as number > 0 && !props.isReadOnly) ? (
              <IconButton aria-label="delete" size="medium" onClick={()=>props.removeNameField(props.nameField.id)}>
                <Tooltip title="Delete Name Field">
                  <DeleteIcon />
                </Tooltip>
              </IconButton>
            ) : null}
          </Grid>
        </Grid>
        { props.nameField.duplicateError && (
          <Grid container columnSpacing={1}>
              <Grid item md={1} xs={12} />
              <Grid item md={11} xs={12} sx={{textAlign:'start'}}>
                <Typography color={'error'} variant='caption'>Label must not be duplicate</Typography>
              </Grid>
          </Grid>
        )}
    </Grid>
    )
  }
