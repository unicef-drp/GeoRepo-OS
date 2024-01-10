import React, {useEffect, useRef, useState} from 'react';
import axios from "axios";
import '../../styles/UploadWizard.scss';
import '../../styles/RDU.styles.scss';
import {
  Alert,
  AlertTitle,
  Grid,
  
  Box
} from "@mui/material";
import LoadingButton from '@mui/lab/LoadingButton';
import Dropzone, { ILayoutProps } from "react-dropzone-uploader";
import Scrollable from '../../components/Scrollable';
import { BatchEntityEditInterface } from "../../models/upload";

const ALLOWABLE_FILE_TYPES = [
    '.xlsx',
    '.xls',
    '.csv'
]


interface Step0Interface {
    batchEdit: BatchEntityEditInterface,
    onClickNext?: () => void,
}

export default function Step0(props: Step0Interface) {
    const [loading, setLoading] = useState(true)
    const [alertMessage, setAlertMessage] = useState('')
    const [isError, setIsError] = useState(false)
    const [formValid, setFormValid] = useState(false)
    const [initialFiles, setInitialFiles] = useState<File[]>([])
    const dropZone = useRef(null)

    // @ts-ignore
    const _csrfToken = csrfToken || '';

    // specify upload params and url for your files
    // @ts-ignore
    const getUploadParams = ({file, meta}) => {
        if (loading) return null
        const body = new FormData()
        body.append('file', file)
        body.append('batch_edit_id', meta.batchEntityEditId)
        const headers = {
            'Content-Disposition': 'attachment; filename=' + meta.name,
            'X-CSRFToken': _csrfToken
        }
        return {url: '/api/batch-entity-edit/file/', body, headers}
    }

    useEffect(() => {
        if (props.batchEdit.input_file_name) {
          setFormValid(true)
          let extension = props.batchEdit.input_file_name.split('.').pop()
          let _fileType = ''
          if (extension === 'csv') {
            _fileType = 'text/csv'
          } else if (extension === 'xls') {
            _fileType = 'application/vnd.ms-excel'
          } else if (extension === 'xlsx') {
            _fileType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          }
          setInitialFiles([new File([], props.batchEdit.input_file_name, {
            type: _fileType
          })])
          setTimeout(() => {
            setLoading(false)
          }, 500)
        } else {
          setInitialFiles([])
          setLoading(false)
        }
    }, [props.batchEdit.input_file_name])

    // called every time a file's `status` changes
    // @ts-ignore
    const handleChangeStatus = (file, status) => {
        let {meta, f, xhr} = file
        meta.batchEntityEditId = props.batchEdit.id
        if (status === 'preparing') {
          setIsError(false)
          setAlertMessage('')
          if (initialFiles.length > 0) {
            meta.name = initialFiles[0].name
            meta.id = 1
            meta.percent = 100
          }
        }
        if (status === 'done') {
          setFormValid(true)
        }
        if (status === 'removed') {
          const dropZoneCurrent = dropZone.current;
          if (!dropZoneCurrent) {
              setIsError(true)
              setAlertMessage('Unable to remove the layer file, Please try again!')
              // exit if ref dropZone is not found
              return;
          }
          // we need to disable the dropzone
          setLoading(true)
          axios.delete(`/api/batch-entity-edit/file/?batch_edit_id=${props.batchEdit.id}`).then( response => {
              setLoading(false)
              if (response) {
                setFormValid(false)
              } else {
                setIsError(true)
                setAlertMessage('Could not remove the uploaded file, please try again later!')
                // TODO: add back the file if failed to remove
              }
          }).catch(
              error => {
                console.error('Error calling file-remove api :', error)
                setIsError(true)
                setAlertMessage('Could not remove the uploaded file, please try again later!')
                setLoading(false)
              }
          )
        }
        if (status === 'error_upload') {
          setTimeout(() => {
              file.remove()
              let response = JSON.parse(xhr.response)
              setIsError(true)
              setAlertMessage(response.detail)
          }, 300)
        }
        if (status === 'aborted') {
          setTimeout(() => {
              file.remove()
          }, 300)
        }
        if (status === 'error_file_size') {
          setTimeout(() => {
              file.remove()
              setIsError(true)
              setAlertMessage('Unable to upload file with more than 600MB!')
          }, 300)
        }
    }

    const handleSubmit = () => {
        props.onClickNext()
    }

    const CustomLayout = ({ input, previews, submitButton, dropzoneProps, files, extra: { maxFiles } }: ILayoutProps) => {
        return (
          <div className='uploader-container'>
            <div {...dropzoneProps}>
              {previews}
              {files.length === 0 && !props.batchEdit.is_read_only && input}
            </div>
            <div className='button-container' style={{marginLeft:0, width: '100%', marginTop: '20px'}}>
              {loading ?
                <LoadingButton loading loadingPosition="start"
                               startIcon={<div style={{width: 20}}/>}
                               variant="outlined">
                  Processing...
                </LoadingButton> :
                (<Grid container direction='row' justifyContent='space-between'>
                  <Grid item>
                  </Grid>
                  <Grid item>
                    {files.length > 0 && files.length < maxFiles && !props.batchEdit.is_read_only && input}
                  </Grid>
                  <Grid item>
                    <LoadingButton loading={loading} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={handleSubmit} variant="contained" disabled={!formValid || loading}>
                      Next
                    </LoadingButton>
                  </Grid>
                </Grid>)
              }
            </div>
          </div>
    
        )
      }

    return (
        <Box>
            <Box className={"description-box"}>
                <p>Drag and drop or click to browse for a csv or excel file.</p>
            </Box>
            <Scrollable>
                <div className='Step1'>
                    { alertMessage ?
                        <Alert style={{ width: '750px', textAlign: 'left' }} severity={ isError ? 'error' : 'success' }>
                            <AlertTitle>{ isError ? 'Error' : 'Success' }</AlertTitle>
                            <p className="display-linebreak">
                                { alertMessage }
                            </p>
                        </Alert> : null }
                    <Dropzone
                        ref={dropZone}
                        disabled={loading || props.batchEdit.is_read_only}
                        getUploadParams={getUploadParams}
                        initialFiles={initialFiles}
                        onChangeStatus={handleChangeStatus}
                        accept={ALLOWABLE_FILE_TYPES.join(', ')}
                        LayoutComponent={CustomLayout}
                        maxSizeBytes={ 600 * 1024 * 1024}
                        maxFiles={1}
                        inputContent={'Drag and drop or click to browse for a csv or excel file.'}
                        />
                </div>
            </Scrollable>
        </Box>
    )
}
