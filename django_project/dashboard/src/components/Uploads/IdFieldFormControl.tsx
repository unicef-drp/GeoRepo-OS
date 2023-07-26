import React from "react";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import Autocomplete, { createFilterOptions } from '@mui/material/Autocomplete';
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import DeleteIcon from '@mui/icons-material/Delete';
import AddCircleIcon from "@mui/icons-material/AddCircle";
import { useRadioGroup } from '@mui/material/RadioGroup';
import Radio from "@mui/material/Radio";
import TextField from "@mui/material/TextField";
import { IdField, IdType } from "../../models/upload";
import AttributeSelect from "./AttributeSelect";

const filterIdTypeList = createFilterOptions<IdType>();

interface IdFieldFormControlProps {
    idField: IdField,
    idTypes: IdType[],
    attributes: string[],
    isReadOnly: boolean,
    index: number,
    handleIdTypeChange: (idFieldId: string, idTypeId?: string, field?: string) => void,
    removeIdField: (id: string) => void,
    addIdField: () => void,
    handleOnNewIdType: (idField: IdField, newValue: any) => void,
    hideCheckbox?: boolean
}
  
export default function IdFieldFormControl(props: IdFieldFormControlProps) {
    const radioGroup = useRadioGroup();

    let checked = false;

    if (radioGroup) {
        checked = radioGroup.value === props.idField.id;
    }
    return (
    <Grid container columnSpacing={1} className='field-container'>
        { !props.hideCheckbox &&
            <Grid item md={1} xs={12}>
                <FormControlLabel value={props.idField.id} checked={checked} label='' disableTypography control={<Radio />} />
            </Grid>
        }
        <Grid item md={5} xs={12}>
            <FormControl sx={{width: '100%'}} disabled={props.isReadOnly}>
                <Autocomplete
                    className="id-type-search"
                    value={props.idField.idType}
                    onChange={(event, newValue) => {
                        if (typeof newValue === 'string') {
                            // timeout to avoid instant validation of the dialog's form.
                            setTimeout(() => {
                                props.handleOnNewIdType(props.idField, newValue)
                            });
                        } else {
                            if (newValue && newValue.id && newValue.id !== '-99') {
                                props.handleIdTypeChange(props.idField.id, newValue.id, null)
                            } else if (newValue && newValue.id && newValue.id === '-99') {
                                // handle open popup
                                props.handleOnNewIdType(props.idField, newValue.name)
                            }
                        }
                    }}
                    filterOptions={(options, params) => {
                        const filtered = filterIdTypeList(options, params)
                        if (params.inputValue !== '') {
                            filtered.push({
                                name: `Add "${params.inputValue}"`,
                                id: '-99'
                            })
                        }
                        return filtered
                    }}
                    options={props.idTypes}
                    getOptionLabel={(option) => {
                        if (typeof option === 'string') {
                            // if it's a user input free text
                            return option
                        }
                        return option.name
                    }}
                    selectOnFocus
                    clearOnBlur
                    handleHomeEndKeys
                    renderOption={(props, option) => <li {...props}>{option.name}</li>}
                    freeSolo
                    renderInput={(params) => <TextField {...params} label="Type" />}
                    disabled={props.isReadOnly}
                />
            </FormControl>
        </Grid>
        <Grid item md={props.hideCheckbox?6:5} xs={12}>
            <AttributeSelect
                id={'id-field-' + props.idField.id}
                name={'Id Field'}
                value={props.idField.field}
                attributes={props.attributes}
                selectionChanged={(value: any) => props.handleIdTypeChange(
                    props.idField.id, null, value as string)
                }
                required={!props.hideCheckbox}
                isReadOnly={props.isReadOnly}
            />
        </Grid>
        <Grid item md={1} xs={12} textAlign="left">
            { (props.index === 0 && !props.isReadOnly) ? (
            <IconButton aria-label="add" size="medium" onClick={()=>props.addIdField()}>
                <Tooltip title="Add Id Field">
                <AddCircleIcon color="primary" />
                </Tooltip>
            </IconButton>
            ) : null }
            {(props.index > 0 && !props.isReadOnly) ? (
            <IconButton aria-label="delete" size="medium" onClick={()=>props.removeIdField(props.idField.id)}>
                <Tooltip title="Delete Id Field">
                <DeleteIcon />
                </Tooltip>
            </IconButton>
            ) : null}
        </Grid>
    </Grid>
    )
}
