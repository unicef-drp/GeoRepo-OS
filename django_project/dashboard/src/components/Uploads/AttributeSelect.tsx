import React from "react";
import FormControl from "@mui/material/FormControl";
import TextField from "@mui/material/TextField";
import Autocomplete from '@mui/material/Autocomplete';
import BackspaceOutlinedIcon from '@mui/icons-material/BackspaceOutlined';

interface AttributeInterface {
    id: string,
    label: string
}

interface AttributeSelectInterface {
    id: string,
    name: string,
    value: string,
    attributes: string[] | AttributeInterface[],
    required?: boolean,
    onSelectionCleared?: () => void,
    isReadOnly?: boolean,
    selectionChanged?: (value: any) => void
}

export default function AttributeSelect(props: AttributeSelectInterface) {
    return (
        <FormControl sx={{width: '100%'}}>
            <Autocomplete
              id={props.id}
              className="attribute-select-with-search"
              value={props.value || null}
              onChange={(event, newValue) => {
                let _val = newValue === null ? '' : newValue
                if (props.selectionChanged) props.selectionChanged(_val)
              }}
              options={props.attributes}
              getOptionLabel={(option: any) => {
                  if (typeof option === 'string') {
                      return option
                  }
                  if (option.label) {
                      return option.label
                  }
                  return '-'
              }}
              selectOnFocus
              clearOnBlur
              handleHomeEndKeys
              renderOption={(props, option:string|AttributeInterface) => <li {...props}>{typeof option === 'string' ? option : option.label}</li>}
              renderInput={(params) => <TextField {...params} label={props.name} />}
              disableClearable={props.required}
              clearIcon={
                <BackspaceOutlinedIcon fontSize="medium" />
              }
              disabled={props.isReadOnly}
            />
        </FormControl>
      )
  }
