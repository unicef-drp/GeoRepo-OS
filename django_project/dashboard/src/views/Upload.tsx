import React, {useEffect, useRef, useState} from "react";
import '../styles/Uploader.scss';
import '../styles/RDU.styles.scss';
import Dropzone from 'react-dropzone-uploader'
import {
    Button,
    Card,
    CardContent,
    LinearProgress,
    TextField,
    Typography,
    Alert,
    AlertTitle
} from "@mui/material";
import LoadingButton from '@mui/lab/LoadingButton';


function UploadComponent (props: any)  {
    const meta = props.meta
    const fileWithMeta = props.fileWithMeta
    const [level, setLevel] = useState(props.level)
    const [entityType, setEntityType] = useState(props.entityType)

    const handleBlur = (e: { currentTarget: any; }) => {
        const currentTarget = e.currentTarget.parentElement.parentElement.parentElement;
        setTimeout(() => {
            if (!currentTarget.contains(document.activeElement)) {
                props.updateLevelAndEntityType(meta.id, level, entityType)
            }
        }, 10);
    };

    return (
        <Card sx={{ minWidth: 730, marginTop: 1 }}>
            <CardContent>
                <Typography sx={{ fontSize: 14 }} color='text.secondary' gutterBottom>
                    {meta.type}
                </Typography>
                <Typography variant="h6" component="div">
                    {meta.name}
                </Typography>
                <TextField type="number" id={ meta.id + 'level' } label="Level" variant="filled" value={level} sx={{ marginRight: 1 }} onChange={(e) => {
                    const level = e.target.value;
                    setLevel(level);
                }} onBlur={handleBlur}/>
                <TextField id={ meta.id + 'entity-type' } label="Entity Type" variant="filled" value={entityType} onChange={(e) => {
                    const entityType = e.target.value;
                    setEntityType(entityType)
                }} onBlur={handleBlur}/>
                <LinearProgress variant="determinate" value={meta.percent} sx={{ marginTop: 2 }} />
                <Button variant="outlined" color="error" onClick={() => fileWithMeta.remove()} sx={{ marginTop: 1 }}>
                  Remove
                </Button>
            </CardContent>
        </Card>
    )
}

interface Level {
  [layerId: string]: string;
}
interface EntityType {
  [layerId: string]: string;
}


function Uploader() {
    const [labelFormat, setLabelFormat] = useState('name_{level}');
    const [codeFormat, setCodeFormat] = useState('code_{level}');
    const [dataset, setDataset] = useState('');
    const [entityTypes, setEntityTypes] = useState<EntityType | undefined>({})
    const [levels, setLevels] = useState<Level | undefined>({})
    const [loading, setLoading] = useState(false)
    const [alertMessage, setAlertMessage] = useState('')
    const [isError, setIsError] = useState(false)
    const [formValid, setFormValid] = useState(false)
    const dropZone = useRef(null)

    // @ts-ignore
    const _csrfToken = csrfToken || '';

    // specify upload params and url for your files
    // @ts-ignore
    const getUploadParams = ({file, meta}) => {
        const body = new FormData()
        body.append('file', file)
        body.append('id', meta.id)
        body.append('uploadDate', meta.lastModifiedDate)
        const headers = {
            'Content-Disposition': 'attachment; filename=' + meta.name,
            'X-CSRFToken': _csrfToken
        }
        return {url: '/api/layer-upload/', body, headers}
    }

    useEffect(() => {
        const dropZoneCurrent = dropZone.current;
        if (!dropZoneCurrent) {
            return;
        }
        const currentFiles: any = dropZoneCurrent['files']
        let allFilesValid = true
        for (let file of currentFiles) {
            if (!levels![file.meta.id]) {
                allFilesValid = false
                break
            }
            if (!entityTypes![file.meta.id]) {
                allFilesValid = false
                break
            }
        }

        if (currentFiles.length > 0 && dataset && labelFormat && codeFormat && allFilesValid) {
            setFormValid(true)
        } else {
            setFormValid(false)
        }
    }, [dataset, labelFormat, codeFormat, levels])

    // called every time a file's `status` changes
    // @ts-ignore
    const handleChangeStatus = ({meta, file}, status) => {
        const _levels = levels!
        const _entityTypes = entityTypes!

        if (status === 'preparing') {
            _levels[meta.id] = ''
            setLevels(_levels)
            _entityTypes[meta.id] = ''
            setEntityTypes(_entityTypes)
        }
        if (status === 'removed') {
            delete _levels[meta.id]
            delete _entityTypes[meta.id]
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
                    setLevels(_levels)
                    setEntityTypes(_entityTypes)
                }
            }).catch(
                error => {
                    console.error('Error calling layer-remove api :', error)
                    setIsError(true)
                    setAlertMessage('Could not remove the layer, please try again later')
                }
            )
        }
    }

    const updateLevelAndEntityType = (layerId: string, level: string, entityType: string) => {
        setLevels({ ...levels, [layerId]: level })
        setEntityTypes({ ...entityTypes, [layerId]: entityType })
    }

    const checkLayerProcessingStatus = (uploadSessionId: string) => {
        fetch('/api/layers-process-status/?session_id=' + uploadSessionId, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': _csrfToken
            }
        }).then(response => {
            if (response.ok) {
                return response.json()
            } else {
                return response.text().then(data => {
                    throw new Error(data)
                })
            }
        }).then(data => {
            if (data['status'] === 'Done') {
                setAlertMessage(data['message'])
                setLoading(false)
                setIsError(false)
            } else if (data['status'] === 'Error') {
                throw new Error(data['message'])
            } else {
                setTimeout(() => {
                    checkLayerProcessingStatus(uploadSessionId)
                }, 1000)
            }
        }).catch( error => {
            console.log(error)
            if (error.message) {
                setAlertMessage(error.message.replaceAll('"', ''))
            }
            setLoading(false)
            setIsError(true)
        })
    }

    // receives array of files that are done uploading when submit button is clicked
    const handleSubmit = () => {
        const files: any = dropZone.current!['files']
        const postData = {
            'entity_types': entityTypes,
            'levels': levels,
            'all_files': files.map((f: { meta: any; }) => f.meta),
            'dataset': dataset,
            'code_format': codeFormat,
            'label_format': labelFormat
        }

        setLoading(true)
        setAlertMessage('')
        setIsError(false)

        fetch('/api/layers-process/', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': _csrfToken
            },
            body: JSON.stringify(postData)
        }).then( response => {
            if (response.ok) {
                return response.json()
            } else {
                return response.text().then(data => { throw new Error(data) })
            }
        }).then( data => {
            if (data) {
                checkLayerProcessingStatus(data['layer_upload_session_id'])
            }
        }).catch(
            error => {
                console.error('Error calling layers-process api :', error)
                if (error.message) {
                    setAlertMessage(error.message.replaceAll('"', ''))
                }
                setLoading(false)
                setIsError(true)
            }
        )
    }

    // @ts-ignore
    return (
        <div className="App" style={{ display: "flex", alignItems: 'center', justifyContent: 'center' }}>
            <div className='content-body' style={{ width: 900, height: 400 }}>
                { alertMessage ?
                <Alert style={{ width: '750px' }} severity={ isError ? 'error' : 'success' }>
                    <AlertTitle>{ isError ? 'Error' : 'Success' }</AlertTitle>
                    <p className="display-linebreak">
                        { alertMessage }
                    </p>
                </Alert> : null }
                <h3>Layer Uploader</h3>
                <div className='layer-format'>
                    <TextField id="label-format" disabled={loading} label="Dataset" variant="outlined" value={dataset} onChange={(e) => setDataset(e.target.value)}/>
                    <TextField id="label-format" disabled={loading} label="Label Format" variant="outlined" value={labelFormat} onChange={(e) => setLabelFormat(e.target.value)}/>
                    <TextField id="code-format" disabled={loading} label="Pcode Format" variant="outlined" value={codeFormat} onChange={(e) => setCodeFormat(e.target.value)} />
                </div>
                <div className='uploader-container'>
                     <Dropzone
                         ref={dropZone}
                         disabled={loading}
                         PreviewComponent={(props) => <UploadComponent
                             key={props.meta.id} meta={props.meta}
                             fileWithMeta={props.fileWithMeta}
                             level={levels![props.meta.id]} entityType={entityTypes![props.meta.id]} updateLevelAndEntityType={updateLevelAndEntityType} /> }
                         getUploadParams={getUploadParams}
                         onChangeStatus={handleChangeStatus}
                         accept="application/geo+json,application/json"
                     />
                </div>
                <div className='button-container' style={{ marginTop: 'unset', marginLeft: 'unset' }}>
                    {loading ?
                        <LoadingButton loading loadingPosition="start"
                                       startIcon={<div style={{width: 20}}/>}
                                       variant="outlined">
                            Processing...
                        </LoadingButton> :
                        <Button onClick={handleSubmit} variant="contained" disabled={!formValid}>
                            Submit
                        </Button>
                    }
                </div>
            </div>
        </div>
    )
}

export default Uploader;
