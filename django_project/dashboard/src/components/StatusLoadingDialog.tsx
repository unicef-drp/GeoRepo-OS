import React, {useState, useEffect} from 'react'
import Grid from '@mui/material/Grid'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import Loading from "./Loading";

interface StatusLoadingDialogInterface {
    open: boolean,
    title: string,
    description: string,
}

export default function StatusLoadingDialog(props: StatusLoadingDialogInterface) {
    const [open, setOpen] = useState<boolean>(false);

    useEffect(() => {
        setOpen(props.open)
    }, [props.open])

    return (<div>
            <Dialog
                open={open}
                aria-labelledby="alert-dialog-title"
                aria-describedby="alert-dialog-description"
                disableEscapeKeyDown
            >
                <DialogTitle id="alert-dialog-title">
                    { props.title }
                </DialogTitle>
                <DialogContent>
                    <Grid container flexDirection={'column'} spacing={1} padding={'10px'}>
                        <Grid item sx={{marginBottom: '10px'}}>
                            <Loading/>
                        </Grid>
                        <Grid item>
                            { props.description }
                        </Grid>
                    </Grid>
                </DialogContent>
            </Dialog>
        </div>);
}