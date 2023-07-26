import React, {useState, useEffect} from 'react'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogActions from '@mui/material/DialogActions'
import Button from '@mui/material/Button'
import LoadingButton from "@mui/lab/LoadingButton";

interface AlertDialogInterface {
    open: boolean,
    alertDialogTitle: string,
    alertDialogDescription: string,
    alertConfirmed: () => void,
    alertClosed: () => void,
    alertLoading?: boolean,
    cancelButtonText?: string,
    confirmButtonText?: string,
    confirmButtonProps?: {}
}

export default function AlertDialog(props: AlertDialogInterface) {
    const [open, setOpen] = useState<boolean>(false);

    useEffect(() => {
        setOpen(props.open)
    }, [props.open])

    const handleClose = () => {
        setOpen(false);
        props.alertClosed()
    }

    return (<div>
            <Dialog
                open={open}
                aria-labelledby="alert-dialog-title"
                aria-describedby="alert-dialog-description"
                disableEscapeKeyDown
            >
                <DialogTitle id="alert-dialog-title">
                    { props.alertDialogTitle }
                </DialogTitle>
                <DialogContent>
                    <DialogContentText id="alert-dialog-description">
                        { props.alertDialogDescription }
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button disabled={props.alertLoading} onClick={handleClose}>
                        {props.cancelButtonText ? props.cancelButtonText : `Cancel`}                        
                    </Button>
                    <LoadingButton loading={props.alertLoading} onClick={props.alertConfirmed} {...props.confirmButtonProps}>
                        {props.confirmButtonText ? props.confirmButtonText : `Confirm`}
                    </LoadingButton>
                </DialogActions>
            </Dialog>
        </div>);
}