import React, {useEffect, useRef, useState} from 'react';
import {
  Alert,
  AlertTitle,
  Button,
  Grid,
  Checkbox, FormControlLabel, SelectChangeEvent,
  Box
} from "@mui/material";
import Dropzone, { IFileWithMeta, ILayoutProps } from "react-dropzone-uploader";
import LoadingButton from "@mui/lab/LoadingButton";
import {useSearchParams} from "react-router-dom";
import axios from "axios";
import { postData } from '../../utils/Requests';
import '../../styles/UploadWizard.scss'
import Scrollable from '../../components/Scrollable';
import '../../styles/RDU.styles.scss';
import {LOAD_UPLOAD_SESSION_DETAIL_URL} from "./Step0";
import UploadComponent, { isFirstLevel, isLastLevel } from '../../components/Uploads/UploadComponent';
import { WizardStepInterface, Level, ALLOWABLE_FILE_TYPES, nameIdSeparator } from '../../models/upload';
import { getFileType } from '../../utils/Helpers';


const LAYER_FILE_CHANGE_LEVEL_URL = '/api/layer-file-change-level/'
const LAYER_FILE_DOWNLOAD_URL = '/api/layer-file-download/'

export default function Step1(props: WizardStepInterface) {
  const [levels, setLevels] = useState<Level | {}>({})
  const [loading, setLoading] = useState(true)
  const [alertMessage, setAlertMessage] = useState('')
  const [isError, setIsError] = useState(false)
  const [formValid, setFormValid] = useState(false)
  const [initialFiles, setInitialFiles] = useState<File[]>([])
  const [searchParams, setSearchParams] = useSearchParams()
  const dropZone = useRef(null)

  // @ts-ignore
  const _csrfToken = csrfToken || '';

  // specify upload params and url for your files
  // @ts-ignore
  const getUploadParams = ({file, meta}) => {
    if (loading) return null
    const body = new FormData()
    body.append('file', file)
    body.append('id', meta.id)
    body.append('uploadSession', meta.uploadSession)
    body.append('uploadDate', meta.lastModifiedDate)
    body.append('level', meta.level)
    const headers = {
      'Content-Disposition': 'attachment; filename=' + meta.name,
      'X-CSRFToken': _csrfToken
    }
    return {url: '/api/layer-upload/', body, headers}
  }

  useEffect(() => {
    if (initialFiles.length > 0) {
      setTimeout(() => {
        setLoading(false)
      }, 500)
    }
  }, [initialFiles])

  useEffect(() => {
    const isAdminUser = (window as any).is_admin
    axios.get(LOAD_UPLOAD_SESSION_DETAIL_URL + searchParams.get('session')).then(
      response => {
        if (response.data.dataset_creator) {
        }
      }, error => {
        console.log(error)
      })

    axios.get(
      (window as any).layerUploadList +
      `?upload_session=${props.uploadSession}`
    ).then(
      response => {
        if (response.data) {
          if (response.data.length > 0) {
            const _initialFiles = []
            let _levels: Level = {}
            for (const layerUploadFile of response.data) {
              let nameWithId = `${layerUploadFile.name}${nameIdSeparator}${layerUploadFile.meta_id}`
              _initialFiles.push(new File([], nameWithId, {
                type: getFileType(layerUploadFile.layer_type, layerUploadFile.name)
              }))
              _levels[layerUploadFile.meta_id] = layerUploadFile.level
            }
            setLevels(_levels)
            setInitialFiles(_initialFiles)
          } else {
            setLoading(false)
          }
        }
      },
      error => console.error(error)
    )
  }, [])

  useEffect(() => {
    const dropZoneCurrent = dropZone.current;
    if (!dropZoneCurrent) {
      return;
    }
    const currentFiles: any = dropZoneCurrent['files']
    let allFilesValid = true
    for (let file of currentFiles) {
      // @ts-ignore
      if (!levels![file.meta.id]) {
        allFilesValid = false
        break
      }
    }
    if (currentFiles.length > 0 && allFilesValid) {
      setFormValid(true)
    } else {
      setFormValid(false)
    }
  }, [levels])

  // called every time a file's `status` changes
  // @ts-ignore
  const handleChangeStatus = (file, status) => {
    let {meta, f, xhr} = file
    const _levels: Level = levels!
    meta.uploadSession = props.uploadSession
    if (status === 'preparing') {
      setIsError(false)
      setAlertMessage('')
      if (initialFiles.length > 0 && meta.name.includes(nameIdSeparator)) {
        let nameWithId = meta.name.split(nameIdSeparator)
        meta.name = nameWithId[0]
        meta.id = nameWithId.at(-1)
        meta.percent = 100
      }
      if (!(meta.id in _levels)) {
        _levels[meta.id] = '' + (Object.keys(_levels).length)
      }
      meta.level = _levels[meta.id]
      setLevels(_levels)
    }
    if (status === 'done') {
      setLevels({..._levels})
    }
    if (status === 'removed') {
      delete _levels[meta.id]
      const dropZoneCurrent = dropZone.current;
      if (!dropZoneCurrent) {
        setIsError(true)
        setAlertMessage('Unable to remove the layer file, Please try again!')
        // exit if ref dropZone is not found
        return;
      }

      fetch('/api/layer-remove/', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': _csrfToken
        },
        body: JSON.stringify({
          'meta_id': meta.id
        })
      }).then( response => {
        if (response.ok) {
          // fix level after item has been removed
          let level = 0
          for (let file of dropZoneCurrent['files']) {
            if (file.meta.id === meta.id)
              continue
            file.meta.level = level.toString()
            _levels![file.meta.id] = file.meta.level
            level += 1
          }
          setLevels({..._levels})
        } else {
          setIsError(true)
          setAlertMessage('Could not remove the layer, please try again later')
          // TODO: add back the file if failed to remove
        }
      }).catch(
        error => {
          console.error('Error calling layer-remove api :', error)
          setIsError(true)
          setAlertMessage('Could not remove the layer, please try again later')
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
  }

  const handleSubmit = () => {
    props.onClickNext()
  }

  const downloadLayerFile = (layerId: string) => {
    const link = document.createElement('a');
    link.href = `${LAYER_FILE_DOWNLOAD_URL}?meta_id=${layerId}`;
    link.dispatchEvent(new MouseEvent('click'));
  }

  const CustomLayout = ({ input, previews, submitButton, dropzoneProps, files, extra: { maxFiles } }: ILayoutProps) => {
    return (
      <div className='uploader-container'>
        <div {...dropzoneProps}>
          {previews}
          {files.length === 0 && !props.isReadOnly && input}
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
                <Button onClick={() => props.onBackClicked()} variant="outlined">
                  Back
                </Button>
              </Grid>
              <Grid item>
                {files.length > 0 && files.length < maxFiles && !props.isReadOnly && input}
              </Grid>
              <Grid item>
                { props.canResetProgress && !loading && (
                  <Button onClick={props.onResetProgress} color={'warning'} variant="outlined" sx={{marginRight: '10px'}}>
                    Update Files
                  </Button>
                )}
                <Button onClick={handleSubmit} variant="contained" disabled={!formValid}>
                  Next
                </Button>
              </Grid>
            </Grid>)
          }
        </div>
      </div>

    )
  }

  // @ts-ignore
  return (
    <Box>
      <Box className={"description-box"}>
        Drag layer files to the box or click the box to browse
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
              disabled={loading || props.isReadOnly}
              PreviewComponent={(props_preview) => <UploadComponent
                key={props_preview.meta.id}
                meta={props_preview.meta}
                fileWithMeta={props_preview.fileWithMeta}
                level={(levels as Level)![props_preview.meta.id]}
                totalLevel={levels?Object.keys(levels).length:0}
                downloadLayerFile={downloadLayerFile}
                uploadLevel0={true}
                isReadOnly={props.isReadOnly}
                />
              }
              maxFiles={1}
              getUploadParams={getUploadParams}
              initialFiles={initialFiles}
              onChangeStatus={handleChangeStatus}
              accept={ALLOWABLE_FILE_TYPES.join(', ')}
              LayoutComponent={CustomLayout}
            />
        </div>
      </Scrollable>
    </Box>
  )
}
