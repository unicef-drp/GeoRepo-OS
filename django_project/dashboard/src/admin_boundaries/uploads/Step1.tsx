import React, {useEffect, useRef, useState} from 'react';
import {
  Alert,
  AlertTitle,
  Button,
  Grid,
  Checkbox, FormControlLabel, SelectChangeEvent,
  Box
} from "@mui/material";
import LoadingButton from '@mui/lab/LoadingButton';
import Dropzone, { IFileWithMeta, ILayoutProps } from "react-dropzone-uploader";
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
  const [uploadLevel0, setUploadLevel0] = useState<boolean>(false)
  // only admin or dataset creator can upload admin 0
  const [canUploadAdmin0, setCanUploadLevel0] = useState<boolean>(false)
  const [firstUpload, setFirstUpload] = useState<boolean>(false)
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
          setCanUploadLevel0(response.data.dataset_creator == (window as any).user_id || isAdminUser)
          setFirstUpload(response.data.first_upload)
          if (response.data.first_upload) {
            setUploadLevel0(true)
          }
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
              if (layerUploadFile.level === '0') {
                setUploadLevel0(true)
              }
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
      let _isInitFile = initialFiles.findIndex((f) => f.name.includes(file.meta.id))
      if (_isInitFile > -1) continue
      // @ts-ignore
      if (!levels![file.meta.id] || file.meta.status !== 'done') {
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
        _levels[meta.id] = '' + (Object.keys(_levels).length + (uploadLevel0 ? 0 : 1))
      }
      meta.level = _levels[meta.id]
      setLevels({..._levels})
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
      // we need to disable the dropzone
      setLoading(true)
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
          // use start level = 0 if uploadLevel0
          let level = uploadLevel0 ? 0 : 1
          for (let file of dropZoneCurrent['files']) {
            if (file.meta.id === meta.id)
              continue
            file.meta.level = level.toString()
            _levels![file.meta.id] = file.meta.level
            level += 1
          }
          setLevels({..._levels})
          setLoading(false)
        } else {
          setIsError(true)
          setAlertMessage('Could not remove the layer, please try again later')
          setLoading(false)
          // TODO: add back the file if failed to remove
        }
      }).catch(
        error => {
          console.error('Error calling layer-remove api :', error)
          setIsError(true)
          setAlertMessage('Could not remove the layer, please try again later')
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

  const moveLevelUp = (layerId: string) => {
    const current_level = (levels as Level)![layerId]
    if (isFirstLevel(current_level, uploadLevel0)) {
      // exit if it is first level
      return;
    }

    const dropZoneCurrent = dropZone.current;
    if (!dropZoneCurrent) {
      // exit if ref dropZone is not found
      return;
    }
    const idx_layer = dropZoneCurrent['files'].findIndex((element: IFileWithMeta) => element.meta.id === layerId)
    if (idx_layer === -1 || idx_layer - 1 === -1) {
      // exit if cannot find layerId or layerId is first item
      return;
    }

    const to_idx = idx_layer - 1;
    const to_element = dropZoneCurrent['files'][to_idx]
    const to_level = to_element.meta.level

    const level_data:Level = {}
    level_data[layerId] = to_level
    level_data[to_element.meta.id] = current_level
    const json_data = {
      'levels': level_data
    }

    postData(LAYER_FILE_CHANGE_LEVEL_URL, json_data).then(response => {
      // switch the level inside IFileWithmeta.meta
      to_element.meta.level = current_level
      const element = dropZoneCurrent['files'].splice(idx_layer, 1)[0]
      // switch the level inside IFileWithmeta.meta
      element.meta.level = to_level
      // add back the element to to_idx position
      dropZoneCurrent['files'].splice(to_idx, 0, element)

      // switch level in levels state
      const _levels:Level = levels!
      _levels[layerId] = to_level
      _levels[to_element.meta.id] = current_level
      setLevels({..._levels})
      // force update the dropZone
      dropZoneCurrent.forceUpdate()
    }).catch(error => {
        let _message = 'Unable to move the layer file'
        if (error.response) {
          if ('detail' in error.response.data) {
            _message = _message + ': ' + error.response.data.detail
          } else {
            _message = _message + ': ' +error.response.data
          }
        }
        setIsError(true)
        setAlertMessage(_message)
    })
  }

  const moveLevelDown = (layerId: string) => {
    const current_level = (levels as Level)![layerId]
    if (isLastLevel(current_level, Object.keys(levels).length, uploadLevel0)) {
      // exit if it is last level
      return;
    }

    const dropZoneCurrent = dropZone.current;
    if (!dropZoneCurrent) {
      // exit if ref dropZone is not found
      return;
    }
    const idx_layer = dropZoneCurrent['files'].findIndex((element: IFileWithMeta) => element.meta.id === layerId)
    if (idx_layer === -1 || idx_layer + 1 === Object.keys(levels).length) {
      // exit if cannot find layerId or layerId is last item
      return;
    }

    const to_idx = idx_layer + 1;
    const to_element = dropZoneCurrent['files'][to_idx]
    const to_level = to_element.meta.level

    const level_data:Level = {}
    level_data[layerId] = to_level
    level_data[to_element.meta.id] = current_level
    const json_data = {
      'levels': level_data
    }

    postData(LAYER_FILE_CHANGE_LEVEL_URL, json_data).then(response => {
      // switch the level inside IFileWithmeta.meta
      to_element.meta.level = current_level
      const element = dropZoneCurrent['files'].splice(idx_layer, 1)[0]
      // switch the level inside IFileWithmeta.meta
      element.meta.level = to_level
      // add back the element to to_idx position
      dropZoneCurrent['files'].splice(to_idx, 0, element)

      // switch level in levels state
      const _levels: Level = levels!
      _levels[layerId] = to_level
      _levels[to_element.meta.id] = current_level
      setLevels({..._levels})
      // force update the dropZone
      dropZoneCurrent.forceUpdate()
    }).catch(error => {
        let _message = 'Unable to move the layer file'
        if (error.response) {
          if ('detail' in error.response.data) {
            _message = _message + ': ' + error.response.data.detail
          } else {
            _message = _message + ': ' + error.response.data
          }
        }
        setIsError(true)
        setAlertMessage(_message)
    })
  }

  const onUploadLevel0CheckboxChanged = (event: SelectChangeEvent) => {
    setUploadLevel0(!uploadLevel0);
  }

  const downloadLayerFile = (layerId: string) => {
    const link = document.createElement('a');
    link.href = `${LAYER_FILE_DOWNLOAD_URL}?meta_id=${layerId}`;
    link.dispatchEvent(new MouseEvent('click'));
  }

  const CustomLayout = ({ input, previews, submitButton, dropzoneProps, files, extra: { maxFiles } }: ILayoutProps) => {
    return (
      <div className='uploader-container'>
        <div style={{ textAlign: 'left' }}>
          <FormControlLabel control={
            <Checkbox disabled={Object.keys(levels).length > 0 || !canUploadAdmin0 || firstUpload || props.isReadOnly} checked={uploadLevel0} onChange={onUploadLevel0CheckboxChanged} />
          } label="Upload level 0" />
        </div>
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
                <LoadingButton loading={props.isUpdatingStep} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={() => props.onBackClicked()} variant="outlined" disabled={loading}>
                  Back
                </LoadingButton>
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
                <LoadingButton loading={props.isUpdatingStep} loadingPosition="start" startIcon={<div style={{width: 0}}/>} onClick={handleSubmit} variant="contained" disabled={!formValid || loading}>
                  Next
                </LoadingButton>
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
        <p>Drag and drop or click to browse for a file in one of these formats: .json, .geojson, .gpkg or a zip file containing a shapefile.</p>
        <p>The dataset CRS should be EPSG:4326. For zip shapefiles, the shapefiles should be in the root directory of the zip.</p>
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
                moveLevelUp={moveLevelUp}
                moveLevelDown={moveLevelDown}
                downloadLayerFile={downloadLayerFile}
                uploadLevel0={uploadLevel0}
                isReadOnly={props.isReadOnly}
                initialFiles={initialFiles}
                />
              }
              getUploadParams={getUploadParams}
              initialFiles={initialFiles}
              onChangeStatus={handleChangeStatus}
              accept={ALLOWABLE_FILE_TYPES.join(', ')}
              LayoutComponent={CustomLayout}
              maxSizeBytes={ 600 * 1024 * 1024}
              inputContent={'Drag and drop or click to browse for a file in one of these formats: .json, .geojson, .gpkg or a zip file containing a shapefile.'}
            />
        </div>
      </Scrollable>
    </Box>
  )
}
