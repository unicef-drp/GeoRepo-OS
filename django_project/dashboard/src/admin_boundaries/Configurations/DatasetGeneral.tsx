import React, {useEffect, useState} from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import {useNavigate} from "react-router-dom";
import Select, { SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import axios from "axios";
import AlertDialog from '../../components/AlertDialog';
import AlertMessage from '../../components/AlertMessage';
import Dataset from '../../models/dataset';
import HtmlTooltip from "../../components/HtmlTooltip";
import Loading from "../../components/Loading";
import {postData} from "../../utils/Requests";
import PrivacyLevel from "../../models/privacy";
import Scrollable from '../../components/Scrollable';
import TaskStatus from '../../components/TaskStatus';

interface DatasetGeneralInterface {
    dataset: Dataset,
    onDatasetUpdated: () => void
}

const UPDATE_DATASET_URL = '/api/update-dataset/'
const FETCH_PRIVACY_LEVEL_LABELS = '/api/permission/privacy-levels/'

export default function DatasetGeneral(props: DatasetGeneralInterface) {
    const [loading, setLoading] = useState(false)
    const [datasetName, setDatasetName] = useState('')
    const [datasetShortCode, setDatasetShortCode] = useState('')
    const [thresholdNew, setThresholdNew] = useState(0)
    const [thresholdOld, setThresholdOld] = useState(0)
    const [generateAdm0DefaultViews, setGenerateAdm0DefaultViews] = useState(false)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const [maxPrivacyLevel, setMaxPrivacyLevel] = useState(4)
    const [minPrivacyLevel, setMinPrivacyLevel] = useState(1)
    const navigate = useNavigate()
    const [alertOpen, setAlertOpen] = useState<boolean>(false)
    const [alertLoading, setAlertLoading] = useState<boolean>(false)
    const [alertDialogTitle, setAlertDialogTitle] = useState<string>('')
    const [alertDialogDescription, setAlertDialogDescription] = useState<string>('')
    const [privacyLevelLabels, setPrivacyLevelLabels] = useState<PrivacyLevel>({})
    const [updateDatasetTaskId, setUpdateDatasetTaskId] = useState('')
    const [isPreferred, setIsPreferred] = useState<boolean>(false)

    const updateDatasetDetail = (name: string, thresholdNew: number, thresholdOld: number, generateAdm0DefaultViews: boolean, isActive: boolean, isPreferred: boolean) => {
        setLoading(true)
        setAlertLoading(true)
        postData(
            `${UPDATE_DATASET_URL}${props.dataset.uuid}/`,
            {
                'name': name,
                'geometry_similarity_threshold_new': thresholdNew,
                'geometry_similarity_threshold_old': thresholdOld,
                'generate_adm0_default_views': generateAdm0DefaultViews,
                'is_active': isActive,
                'is_preferred': isPreferred
            }
        ).then(
            response => {
                setLoading(false)
                setAlertOpen(false)
                setAlertLoading(false)
                let _taskId = response.data['generate_default_views_task']
                if (_taskId) {
                    setUpdateDatasetTaskId(_taskId)
                } else {
                    setAlertMessage('Successfully updating dataset configuration!')
                }
            }
        ).catch(error => {
            setLoading(false)
            setAlertOpen(false)
            setAlertLoading(false)
            console.log('error ', error)
            if (error.response) {
                if (error.response.status == 403) {
                  // TODO: use better way to handle 403
                  navigate('/invalid_permission')
                }
            } else {
                alert('Error updating dataset configuration!')
            }
        })
    }

    useEffect(() => {
        if (props.dataset) {
            setDatasetName(props.dataset.dataset)
            setThresholdNew(props.dataset.geometry_similarity_threshold_new)
            setThresholdOld(props.dataset.geometry_similarity_threshold_old)
            setGenerateAdm0DefaultViews(props.dataset.generate_adm0_default_views)
            setMaxPrivacyLevel(props.dataset.max_privacy_level)
            setMinPrivacyLevel(props.dataset.min_privacy_level)
            setDatasetShortCode(props.dataset.short_code)
            setIsPreferred(props.dataset.is_preferred)
        }
        fetchPrivacyLevelLabels()
    }, [props.dataset])

    const handleSaveClick = () => {
        updateDatasetDetail(datasetName, thresholdNew, thresholdOld, generateAdm0DefaultViews, props.dataset.is_active, isPreferred)
    }

    const toggleDatasetStatus = () => {
        let _title = props.dataset.is_active ? 'Deprecate this dataset?' : 'Activate this dataset?'
        let _desc = props.dataset.is_active ? 'Are you sure you want to deprecate this dataset?' : 'Are you sure you want to activate this dataset?'
        setAlertDialogTitle(_title)
        setAlertDialogDescription(_desc)
        setAlertOpen(true)
    }

    const alertConfirmed = () => {
        updateDatasetDetail(datasetName, thresholdNew, thresholdOld, generateAdm0DefaultViews, !props.dataset.is_active, isPreferred)
    }

    const handleAlertCancel = () => {
        setAlertOpen(false)
    }

    const fetchPrivacyLevelLabels = () => {
        axios.get(`${FETCH_PRIVACY_LEVEL_LABELS}`).then(
            response => {
                if (response.data) {
                    setPrivacyLevelLabels(response.data as PrivacyLevel)
                }
            }
        ).catch(error => {
            console.log(error)
        })
    }

    return (
        <Scrollable>
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AlertMessage message={alertMessage} onClose={() => {
                    props.onDatasetUpdated()
                    setAlertMessage('')
                }} />
                <AlertDialog open={alertOpen} alertClosed={handleAlertCancel}
                         alertConfirmed={alertConfirmed}
                         alertLoading={alertLoading}
                         alertDialogTitle={alertDialogTitle}
                         alertDialogDescription={alertDialogDescription} />
                <TaskStatus dialogTitle='Update Dataset' errorMessage='Error! There is unexpected error while generating adm0 default views, please contact Administrator.'
                    successMessage='Successfully updating dataset configuration!' task_id={updateDatasetTaskId} onCompleted={() => {
                        setUpdateDatasetTaskId('')
                        setAlertMessage('Successfully updating dataset configuration!')
                    }}
                />
                <div className='FormContainer'>
                    <FormControl className='FormContent'>
                        <Grid container columnSpacing={2} rowSpacing={2}>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Dataset Name</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={loading || !props.dataset.is_active}
                                    id="input_datasetname"
                                    hiddenLabel={true}
                                    type={"text"}
                                    onChange={val => setDatasetName(val.target.value)}
                                    value={datasetName}
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Short Code</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={true}
                                    id="input_datasetshortcode"
                                    hiddenLabel={true}
                                    type={"text"}
                                    value={datasetShortCode}
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Grid container flexDirection={'row'} alignItems={'center'}>
                                    <Grid item>
                                        <Typography variant={'subtitle1'}>
                                            Similarity Threshold (% new)
                                        </Typography>
                                    </Grid>
                                    <Grid item>
                                    <HtmlTooltip tooltipTitle='Geometry Similarity Threshold (% new)'
                                        tooltipDescription={<p>The percentage of the new boundary area covered by the old matching boundary</p>}
                                    />
                                    </Grid>
                                </Grid>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={loading || !props.dataset.is_active}
                                    id="input_threshold_new"
                                    hiddenLabel={true}
                                    type='number'
                                    onChange={val => setThresholdNew(parseFloat(val.target.value))}
                                    value={thresholdNew}
                                    sx={{ width: '30%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Grid container flexDirection={'row'} alignItems={'center'}>
                                    <Grid item>
                                        <Typography variant={'subtitle1'}>
                                            Similarity Threshold (% old)
                                        </Typography>
                                    </Grid>
                                    <Grid item>
                                        <HtmlTooltip tooltipTitle='Geometry Similarity Threshold (% old)'
                                            tooltipDescription={<p>The percentage of the old boundary area covered by the matching new boundary</p>}
                                        />
                                    </Grid>
                                </Grid>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={loading || !props.dataset.is_active}
                                    id="input_threshold_old"
                                    hiddenLabel={true}
                                    type='number'
                                    onChange={val => setThresholdOld(parseFloat(val.target.value))}
                                    value={thresholdOld}
                                    sx={{ width: '30%' }}
                                />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Maximum privacy level</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <FormControl sx={{minWidth: '300px'}} disabled>
                                    <Select
                                        id="max-privacy-level-select"
                                        value={'' +maxPrivacyLevel}
                                        label=""
                                        onChange={(event: SelectChangeEvent) => {
                                            setMaxPrivacyLevel(parseInt(event.target.value))
                                        }}
                                    >
                                        <MenuItem value={1}>{`1${privacyLevelLabels[1] ? ' - ' + privacyLevelLabels[1] : ''}`}</MenuItem>
                                        <MenuItem value={2}>{`2${privacyLevelLabels[2] ? ' - ' + privacyLevelLabels[2] : ''}`}</MenuItem>
                                        <MenuItem value={3}>{`3${privacyLevelLabels[3] ? ' - ' + privacyLevelLabels[3] : ''}`}</MenuItem>
                                        <MenuItem value={4}>{`4${privacyLevelLabels[4] ? ' - ' + privacyLevelLabels[4] : ''}`}</MenuItem>
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Minimum privacy level</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <FormControl sx={{minWidth: '300px'}} disabled>
                                    <Select
                                        id="min-privacy-level-select"
                                        value={'' +minPrivacyLevel}
                                        label=""
                                        onChange={(event: SelectChangeEvent) => {
                                        setMinPrivacyLevel(parseInt(event.target.value))
                                        }}
                                    >
                                        <MenuItem value={1}>{`1${privacyLevelLabels[1] ? ' - ' + privacyLevelLabels[1] : ''}`}</MenuItem>
                                        <MenuItem value={2}>{`2${privacyLevelLabels[2] ? ' - ' + privacyLevelLabels[2] : ''}`}</MenuItem>
                                        <MenuItem value={3}>{`3${privacyLevelLabels[3] ? ' - ' + privacyLevelLabels[3] : ''}`}</MenuItem>
                                        <MenuItem value={4}>{`4${privacyLevelLabels[4] ? ' - ' + privacyLevelLabels[4] : ''}`}</MenuItem>
                                    </Select>
                                </FormControl>
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Grid container flexDirection={'row'} alignItems={'center'}>
                                    <Grid item>
                                        <Typography variant={'subtitle1'}>
                                            Create Default Views for Every Level 0 Entity
                                        </Typography>
                                    </Grid>
                                    <Grid item>
                                        <HtmlTooltip tooltipTitle='Create Default Views for Every Level 0 Entity'
                                            tooltipDescription={
                                                <div>
                                                    <p>
                                                        Set to true to automatically create default views (latest & all versions) for every level 0 entity.
                                                    </p>
                                                    Note:<br />
                                                    <ul>
                                                        <li>Updating this value to true will generate level 0 entities without default views</li>
                                                        <li>Updating this value to false will not remove default views for level 0 entities</li>
                                                    </ul>
                                                </div>
                                            }
                                        />
                                    </Grid>
                                </Grid>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <FormControlLabel control={<Checkbox value={generateAdm0DefaultViews} checked={generateAdm0DefaultViews}
                                                    disabled={loading || !props.dataset.is_active}
                                                    onChange={(val) => setGenerateAdm0DefaultViews(val.target.checked)}/>}
                                                    label="" />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Grid container flexDirection={'row'} alignItems={'center'}>
                                    <Grid item>
                                        <Typography variant={'subtitle1'}>
                                            Is Favorite
                                        </Typography>
                                    </Grid>
                                    <Grid item>
                                    <HtmlTooltip tooltipTitle='Dataset Favorite Flag'
                                        tooltipDescription={
                                            <div>
                                                <p>
                                                    The favorite dataset will appear at the top in the GeoRepo Dataset List API.
                                                </p>
                                            </div>
                                        }
                                    />
                                    </Grid>
                                </Grid>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <FormControlLabel control={<Checkbox value={isPreferred} checked={isPreferred}
                                    disabled={loading || !props.dataset.is_active}
                                    onChange={(val) => setIsPreferred(val.target.checked)}/>}
                                    label="" />
                            </Grid>
                            <Grid className={'form-label'} item md={4} xl={4} xs={12}>
                                <Typography variant={'subtitle1'}>Status</Typography>
                            </Grid>
                            <Grid item md={8} xs={12} sx={{ display: 'flex' }}>
                                <TextField
                                    disabled={true}
                                    id="input_datasetstatus"
                                    hiddenLabel={true}
                                    type={"text"}
                                    value={props.dataset.is_active ? 'Active' : 'Deprecated'}
                                    sx={{ width: '100%' }}
                                />
                            </Grid>
                        </Grid>
                        <Grid container columnSpacing={2} rowSpacing={2} sx={{paddingTop: '1em'}} flexDirection={'row'} justifyContent={'space-between'}>
                            <Grid item>
                                <div className='button-container'>
                                    <Button
                                        variant={"contained"}
                                        color={ props.dataset.is_active ? 'error' : 'primary' }
                                        disabled={loading || !props.dataset.permissions.includes('Own')}
                                        onClick={toggleDatasetStatus}>
                                        <span style={{ display: 'flex' }}>
                                        { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { props.dataset.is_active ? 'Deprecate' : 'Activate' }</span>
                                    </Button>
                                </div>
                            </Grid>
                            <Grid item>
                                <div className='button-container'>
                                    <Button
                                        variant={"contained"}
                                        disabled={loading || !props.dataset.is_active}
                                        onClick={handleSaveClick}>
                                        <span style={{ display: 'flex' }}>
                                        { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Save" }</span>
                                    </Button>
                                </div>
                            </Grid>
                        </Grid>
                    </FormControl>
                </div>
            </Box>
        </Box>
        </Scrollable>
    )
}