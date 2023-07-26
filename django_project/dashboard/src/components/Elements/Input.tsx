import React from 'react';
import TextField from "@mui/material/TextField";
import InputAdornment from '@mui/material/InputAdornment';
import {TextFieldProps} from "@mui/material/TextField/TextField";

/** Input with icon
 * @param {JSX.Element} iconStart Start icon on the input.
 * @param {JSX.Element} iconEnd End icon on the input.
 * @param {Object} InputProps Others input props.
 * @param {Object} props Other props for Text Field.
 */
export function IconTextField({ iconStart, iconEnd, InputProps, ...props } : {
    iconStart?: JSX.Element,
    iconEnd?: JSX.Element,
    InputProps?: {},
    props?: TextFieldProps
}) {
  return (
    <TextField
      {...props}
      InputProps={{
        ...InputProps,
        startAdornment: iconStart ? (
          <InputAdornment position="start">{iconStart}</InputAdornment>
        ) : null,
        endAdornment: iconEnd ? (
          <InputAdornment position="end">{iconEnd}</InputAdornment>
        ) : null
      }}
    />
  );
}
