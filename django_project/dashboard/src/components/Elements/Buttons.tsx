import React from 'react';
import { Button } from "@mui/material";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import SaveIcon from '@mui/icons-material/Save';
import EditIcon from '@mui/icons-material/Edit';
import CancelIcon from '@mui/icons-material/Cancel';
import WarningIcon from '@mui/icons-material/Warning';
import RemoveCircleIcon from '@mui/icons-material/RemoveCircle';

interface ThemeButtonInterface {
  icon: React.ReactElement,
  title: string,
  variant?: string,
  disabled?: boolean,
  onClick?: any,
  additionalClass?: string,
  sx?: any
}
interface ButtonInterface {
  text?: string,
  variant?: string,
  disabled?: boolean,
  onClick?: any,
  useIcon?: boolean,
  additionalClass?: string
}

/** Main button
 * @param {React.ReactElement} icon Icon of the button
 * @param {string} title Title of the button
 * @param {string} variant Variant of the button
 * @param disabled
 * @param onClick
 */
export function ThemeButton({ icon, title, variant, disabled = false, onClick = null, additionalClass = null, sx = null } : ThemeButtonInterface) {
  return (
    <Button
      disabled={disabled}
      className={'ThemeButton ' + (variant ? 'MuiButton-' + variant : '') + (additionalClass ? ' ' + additionalClass : '')}
      onClick={onClick}
      sx={sx}
    >
      {icon} {title}
    </Button>
  )
}

/** Add button
 * @param {string} text Text of button.
 * @param {string} buttonProps Variant of Button.
 */
export function AddButton({ text, variant, disabled, onClick = null, useIcon = true, additionalClass = null } : ButtonInterface) {
  // @ts-ignore
  return (
    <ThemeButton icon={useIcon?<AddCircleIcon/>:null} title={text} variant={variant} disabled={disabled} onClick={onClick} additionalClass={additionalClass} />
  )
}

/** Edit button
 * @param {string} text Text of button.
 * @param {string} buttonProps Variant of Button.
 */
export function EditButton({ text, variant, onClick = null, useIcon = true } : ButtonInterface) {
  return (
    <ThemeButton icon={useIcon?<EditIcon/>:null} title={text} variant={variant} onClick={onClick}/>
  )
}

/** Save button
 * @param {string} text Text of button.
 * @param {string} buttonProps Variant of Button.
 */
export function SaveButton({ text, variant, useIcon = true } : ButtonInterface) {
  return (
    <ThemeButton icon={useIcon?<SaveIcon/>:null} title={text} variant={variant}/>
  )
}

/** Delete button
 * @param {string} text Text of button.
 * @param {string} buttonProps Variant of Button.
 */
export function DeleteButton({ text, variant, useIcon = true } : ButtonInterface) {
  return (
    <ThemeButton icon={useIcon?<RemoveCircleIcon/>:null} title={text} variant={variant} />
  )
}

/** Cancel button
 * @param {any} onClick button on click
 * @param {boolean} useIcon display icon
 */
export function CancelButton({ onClick = null, useIcon = true, text = 'Cancel' } : ButtonInterface) {
  return (
    <ThemeButton icon={useIcon?<CancelIcon/>:null} title={text} variant={'error'} onClick={onClick} />
  )
}

/** Warning button
 * @param {string} text Text of button.
 * @param {any} onClick button on click
 * @param {boolean} disabled
 * @param {boolean} useIcon display icon
 */
export function WarningButton({ text, disabled =false, onClick = null, useIcon = true, additionalClass = null } : ButtonInterface) {
  return (
    <ThemeButton icon={useIcon?<WarningIcon/>:null} title={text} variant={'warning'} disabled={disabled} onClick={onClick} additionalClass={additionalClass} />
  )
}

