import React from 'react'
import Snackbar  from '@mui/material/Snackbar'
import Alert from '@mui/material/Alert'

interface AlertMessageInterface {
    message?: string,
    onClose?: () => void
}

export default function AlertMessage(props: AlertMessageInterface) {
    return (
        <Snackbar open={props.message !== ''} autoHideDuration={props.message.toLowerCase().includes('success') ? 3000 : 6000}
            anchorOrigin={{vertical:'top', horizontal:'center'}}
            onClose={()=>props.onClose?props.onClose():null}>
            <Alert onClose={()=>props.onClose?props.onClose():null} severity={props.message.toLowerCase().includes('error') ? 'error' : 'success'}
                    sx={{ width: '100%' }}>
            {props.message}
            </Alert>
        </Snackbar>
    )
}