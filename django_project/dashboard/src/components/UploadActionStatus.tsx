import React, {useEffect, useState} from 'react'
import axios from "axios";
import StatusLoadingDialog from './StatusLoadingDialog';

interface UploadActionStatusInterface {
    sessionId: string;
    actionUuid: string;
    title: string;
    onSuccess: (result?: any) => void;
    onError: (error: string) => void;
}

// fetch status every 5s
const FETCH_STATUS_INTERVAL = 5 * 1000
const FETCH_ACTION_STATUS = '/api/upload-session/action/'

export default function UploadActionStatus(props: UploadActionStatusInterface) {
    const [statusDialogOpen, setStatusDialogOpen] = useState<boolean>(false)
    const [statusDialogTitle, setStatusDialogTitle] = useState<string>('')
    const [statusDialogDescription, setStatusDialogDescription] = useState<string>('')
    const [checkFinished, setCheckFinished] = useState(false)

    const fetchActionStatus = () => {
        let _url = `${FETCH_ACTION_STATUS}${props.sessionId}/status?action=${props.actionUuid}`
        axios.get(_url).then((response) => {
            if (response.data) {
                let _data = response.data
                if (_data['has_action']) {
                    let _status = _data['status'] ? _data['status'].toLowerCase() : 'none'
                    if (_status === 'done') {
                        let _result = _data['result']
                        closeActionDialog(true, '', _result)
                    } else if (_status === 'error') {
                        closeActionDialog(false, 'Error! There is unexpected error during running the task! Please try to retry from previous step or contact administrator!')
                    }
                } else {
                    closeActionDialog(false, 'Error! Could not fetch Upload Session Status! Please try to refresh this page!')
                }
            }
          }).catch((error) => {
            console.log(error)
          })
    }

    useEffect(() => {
        if (props.actionUuid) {
            setCheckFinished(false)
            setStatusDialogOpen(true)
            setStatusDialogTitle(props.title)
            setStatusDialogDescription('Please wait while background task is in progress...')
        }
    }, [props.actionUuid])

    useEffect(() => {
        if (!checkFinished && statusDialogOpen) {
            const interval = setInterval(() => {
                fetchActionStatus()
            }, FETCH_STATUS_INTERVAL);
            return () => clearInterval(interval)
        }
    }, [checkFinished, statusDialogOpen])

    const closeActionDialog = (isSuccess: boolean, error?: string, result?: any) => {
        setCheckFinished(true)
        setStatusDialogOpen(false)
        if (isSuccess) {
            props.onSuccess(result)
        } else {
            props.onError(error)
        }
    }

    return (
        <StatusLoadingDialog open={statusDialogOpen}
            title={statusDialogTitle} description={statusDialogDescription} />
    )
}

