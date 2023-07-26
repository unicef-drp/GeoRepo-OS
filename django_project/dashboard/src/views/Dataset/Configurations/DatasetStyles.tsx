import React, {useEffect, useState, ChangeEvent, useRef} from 'react';
import {
    Box,
    Grid,
    Typography,
    Button,
    Divider,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    SelectChangeEvent
} from '@mui/material';
import {useNavigate} from "react-router-dom";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import maplibregl, {AttributionControl} from 'maplibre-gl';
import {postData} from "../../../utils/Requests";
import AlertMessage from '../../../components/AlertMessage';
import {validate} from '@mapbox/mapbox-gl-style-spec';
import Dataset from '../../../models/dataset';

const DOWNLOAD_STYLE_URL = '/api/dataset-style/dataset/'
const UPLOAD_STYLE_URL = '/api/update-dataset-style/'

interface DatasetStyleInterface {
    dataset: Dataset
}

export default function DatasetStyle(props: DatasetStyleInterface) {
    const navigate = useNavigate()
    const [datasetStyleSourceName, setDatasetStyleSourceName] = useState<string>('')
    const [sources, setSources] = useState<string[]>([])
    const [jsonStyleData, setJsonStyleData] = useState(null)
    const [jsonStyleFileName, setJsonStyleFileName] = useState('')
    // map
    const mapContainer = useRef(null);
    const map = useRef(null);
    const [lng] = useState(139.753);
    const [lat] = useState(35.6844);
    const [zoom] = useState(1);
    const [alertMessage, setAlertMessage] = useState<string>('')

    const fetchCurrentStyle = () => {
        const link = document.createElement('a');
        link.href = `${DOWNLOAD_STYLE_URL}${props.dataset.uuid}/?download=True`;
        link.dispatchEvent(new MouseEvent('click'));
    }

    useEffect(() => {
        if (!jsonStyleData) return;
        if (map.current) {
            map.current.setStyle(jsonStyleData)
            return;
        }
        map.current = new maplibregl.Map({
            container: mapContainer.current,
            style: jsonStyleData,
            center: [lng, lat],
            zoom: zoom,
            attributionControl: false
        })
        map.current.addControl(new AttributionControl(), 'top-left')
    }, [jsonStyleData])

    const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files) {
            return;
        }
        const file = e.target.files[0];
        const { name } = file;
        const reader = new FileReader();
        reader.onload = (evt) => {
            if (!evt?.target?.result) {
                return;
            }
            const { result } = evt.target;
            let errors = validate(result as string)
            if (errors && errors.length) {
                setAlertMessage(`There is error in the json style: ${errors[0].message}`)
                e.target.value = null
                return;
            }
            const styleData = JSON.parse(result as string)
            setJsonStyleFileName(name);
            setSources(Object.keys(styleData.sources))
            setJsonStyleData(styleData)
            if (props.dataset.source_name) {
                setDatasetStyleSourceName(props.dataset.source_name)
            }
            e.target.value = null
        }
        reader.readAsBinaryString(file)
    }

    const uploadStyle = () => {
        postData(
            `${UPLOAD_STYLE_URL}${props.dataset.uuid}/${datasetStyleSourceName}/`,
            jsonStyleData
        ).then(
            response => {
                // navigate to dataset page
                setAlertMessage('Successfully updating dataset style, redirecting...')
                setTimeout(() => {
                    navigate(`/admin_boundaries/dataset_entities?id=${props.dataset.id}`)
                }, 2000)
            }
        ).catch(error => {
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                alert('Error updating dataset style')
            }
        })
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => setAlertMessage('')} />
                <Grid container sx={{marginBottom: '20px'}}>
                    <Grid item>
                        <Button onClick={fetchCurrentStyle} variant="contained" color="primary">
                            Download current style json
                        </Button>
                    </Grid>
                </Grid>
                <Divider />
                <Grid container flexDirection={'column'} sx={{marginTop: '20px', width: '50%', alignItems: 'flex-start'}} spacing={2}>
                    <Grid item>
                        <Grid container flexDirection={'row'} sx={{ alignItems: 'center' }}>
                            <Button
                                component="label"
                                variant="outlined"
                                startIcon={<UploadFileIcon />}
                                sx={{ marginRight: "1rem" }}
                                disabled={!props.dataset.is_active}
                            >
                                Select style json file
                                <input type="file" accept=".json" hidden onChange={handleFileUpload} />
                            </Button>
                            { jsonStyleFileName && 
                                <Typography variant='subtitle1' sx={{marginLeft: '20px'}}>
                                    {jsonStyleFileName}
                                </Typography>
                            }
                        </Grid>
                    </Grid>
                    <Grid item>
                        <Grid container flexDirection={'row'} sx={{ alignItems: 'center' }}>
                            <Grid item>
                                <FormControl sx={{width: '100%'}} disabled={!jsonStyleData}>
                                    <InputLabel
                                        id="sourcename-select">Select Source </InputLabel>
                                    <Select
                                        labelId="sourcename-select"
                                        value={datasetStyleSourceName}
                                        label='Select Source'
                                        onChange={(event: SelectChangeEvent) => setDatasetStyleSourceName(event.target.value as string)}
                                        required
                                        sx={{minWidth: '350px'}}
                                    >
                                        {sources.map(source => 
                                            <MenuItem
                                                value={source}
                                                key={source}>{source}
                                            </MenuItem>
                                        )}
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid item sx={{marginLeft: '20px'}}>
                                <Button onClick={uploadStyle} variant="contained" color="primary" disabled={datasetStyleSourceName==='' || jsonStyleData===null}>
                                        Upload style
                                </Button>
                            </Grid>
                        </Grid>
                    </Grid>
                </Grid>
                <Grid container flexDirection={'column'} sx={{alignItems: 'flex-start', flexGrow: 1, paddingTop: '10px'}}>
                    <Grid item>
                    { map.current &&
                        <Typography variant='subtitle1' sx={{marginBottom: '10px'}}>
                            Preview:
                        </Typography>
                    }
                    </Grid>
                    <Grid item sx={{ display: 'flex', flex: 1, width: '100%', height: '100%'}}>
                        <div ref={mapContainer} style={{height: '100%', width: '100%'}}/>
                    </Grid>
                </Grid>
            </Box>
        </Box>
    )
}