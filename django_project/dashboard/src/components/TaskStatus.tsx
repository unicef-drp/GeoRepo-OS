import React, {useEffect, useState} from 'react';
import axios from "axios";
import StatusLoadingDialog from './StatusLoadingDialog';
import AlertMessage from './AlertMessage';


const CHECK_STATUS_API_URL = '/api/background-task/status/'
const TASK_FINAL_STATES = [
  'SUCCESS',
  'FAILURE',
  'REVOKED'
]

interface TaskStatusInterface {
    task_id: string;
    dialogTitle: string;
    successMessage: string;
    errorMessage: string;
    onCompleted: () => void;
}

export default function TaskStatus(props: TaskStatusInterface) {
    const { task_id, dialogTitle, successMessage, errorMessage, onCompleted } = props
    const [statusDialogOpen, setStatusDialogOpen] = useState<boolean>(false)
    const [statusDialogDescription, setStatusDialogDescription] = useState<string>('Please wait while background task is in progress...')
    const [actionMessage, setActionMessage] = useState<string>('')

    const fetchTaskStatus = () => {
        axios.get(`${CHECK_STATUS_API_URL}?task_id=${task_id}`).then(response => {
            let _status = response.data['status']
            if (TASK_FINAL_STATES.includes(_status)) {
                if (_status === 'SUCCESS') {
                    // setActionMessage('')
                    setActionMessage(successMessage)
                } else if (_status === 'FAILURE') {
                    // setActionMessage('')
                    setActionMessage(errorMessage)
                } else if (_status === 'REVOKED') {
                    setActionMessage('The task has been cancelled! Please try again later.')
                }
                onCompleted()
            }
        })
    }

    useEffect(() => {
        if (task_id) {
          setStatusDialogOpen(true)
        } else {
          setStatusDialogOpen(false)
        }
      }, [task_id])
    
    useEffect(() => {
        if (statusDialogOpen) {
            const interval = setInterval(() => {
                fetchTaskStatus()
            }, 2000);
            return () => clearInterval(interval)
        }
    }, [statusDialogOpen])

    return (
        <div>
            <AlertMessage message={actionMessage} onClose={() => setActionMessage('')} />
            <StatusLoadingDialog open={statusDialogOpen} title={dialogTitle} description={statusDialogDescription} />
        </div>
    )
}
