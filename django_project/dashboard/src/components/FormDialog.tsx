import * as React from 'react';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';


interface FormDialogInterface {
    open: boolean;
    dialogTitle: string;
    dialogContent: string;
    inputLabel: string;
    onSubmitted: (value: string) => void;
    onClosed: () => void;
}


export default function FormDialog(props: FormDialogInterface) {
    const [textValue, setTextValue] = React.useState('')

    const handleClose = () => {
        props.onClosed()
    }

    const handleConfirm = () => {
        props.onSubmitted(textValue)
    }

    return (
        <div>
        <Dialog open={props.open} onClose={handleClose}>
            <DialogTitle>{props.dialogTitle}</DialogTitle>
            <DialogContent>
                <DialogContentText>
                    {props.dialogContent}
                </DialogContentText>
                <TextField
                    autoFocus
                    margin="dense"
                    id="dialog_text_value"
                    label={props.inputLabel}
                    type="text"
                    value={textValue}
                    onChange={(e) => setTextValue(e.target.value)}
                    fullWidth
                    inputProps={{
                        maxLength: 512
                    }}
                    variant="standard"
                />
            </DialogContent>
            <DialogActions>
            <Button onClick={handleClose}>Cancel</Button>
            <Button onClick={handleConfirm}>Confirm</Button>
            </DialogActions>
        </Dialog>
        </div>
    );
}