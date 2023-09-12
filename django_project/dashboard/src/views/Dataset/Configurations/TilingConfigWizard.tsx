import React, {useEffect, useState} from 'react';
import {useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import AlertMessage from '../../../components/AlertMessage';
import AlertDialog from "../../../components/AlertDialog";
import {postData} from "../../../utils/Requests";
import TabPanel, {a11yProps} from '../../../components/TabPanel';
import {DatasetTilingConfigMatrix} from './DatasetTilingConfig';
import Scrollable from '../../../components/Scrollable';
import {useAppDispatch} from "../../../app/hooks";
import {updateMenu} from "../../../reducers/breadcrumbMenu";
import TilingConfigPreview from './TilingConfigPreview';


interface TabInterface {
    onNext?: () => void,
    onBack?: () => void
}

const FETCH_DATASET_DETAIL_URL = '/api/dataset-detail/'
const FETCH_VIEW_DETAIL_URL = '/api/view-detail/'
const TILING_CONFIGS_TEMP_CONFIRM_URL = '/api/tiling-configs/temporary/apply/'
const TILING_CONFIGS_STATUS_URL = '/api/tiling-configs/status/'

function TilingConfigConfirm(props: any) {
    const [loading, setLoading] = useState(false)
    const [alertOpen, setAlertOpen] = useState(false)

    const confirmTilingConfig = (overwriteView: boolean = false) => {
        setLoading(true)
        let _data = {
            'object_uuid': props.viewUUID ? props.viewUUID : props.datasetUUID,
            'object_type': props.viewUUID ? 'datasetview' : 'dataset',
            'session': props.session,
            'overwrite_view': props.viewUUID ? true : overwriteView
        }
        postData(TILING_CONFIGS_TEMP_CONFIRM_URL, _data).then(
            response => {
                setLoading(false)
                props.onTilingConfigConfirmed()
            }
        ).catch(error => {
            setLoading(false)
            console.log('error ', error)
            alert('Error saving tiling config...')
        })
    }

    const handleConfirmClick = () => {
        if (props.viewUUID) {
            confirmTilingConfig(true)
        } else {
            setAlertOpen(true)
        }
    }

    const onConfirmedNo = () => {
        setAlertOpen(false)
        confirmTilingConfig(false)
    }

    const onConfirmedYes = ()  => {
        setAlertOpen(false)
        confirmTilingConfig(true)
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'auto' }}>
            <Grid container>
                <Grid item>
                    <Typography>Please check and confirm the configuration:</Typography>
                </Grid>
                <Grid item>
                    <DatasetTilingConfigMatrix session={props.session} isReadOnly={true} hideActions={true}/>
                </Grid>
                <Grid item sx={{marginLeft:0, width: '100%', padding: '10px'}}>
                    <Grid container direction='row' justifyContent='space-between'>
                        <Grid item>
                        </Grid>
                        <Grid item>
                            <Button disabled={loading} onClick={() => handleConfirmClick()} variant="contained">
                                Confirm and Save
                            </Button>
                        </Grid>
                        <Grid item>
                          <AlertDialog open={alertOpen} alertClosed={onConfirmedNo}
                            alertConfirmed={onConfirmedYes}
                            alertDialogTitle={`Saving Tiling Config.`}
                            alertDialogDescription={'Apply to existing views?'}
                            cancelButtonText={'No'}
                            confirmButtonText={'Yes'}
                          />
                        </Grid>
                    </Grid>
                </Grid>
            </Grid>
        </Box>
    )
}


export default function TilingConfigWizard(props: any) {
    // Tab 1: Tiling Config editable
    // Tab 2: Preview
    // Tab 3: Confirm+Save + Progress
    const [tabSelected, setTabSelected] = useState(0)
    const [searchParams, setSearchParams] = useSearchParams()
    const [session, setSession] = useState(null)
    const [datasetUUID, setDatasetUUID] = useState(null)
    const [viewUUID, setViewUUID] = useState(null)
    const [alertMessage, setAlertMessage] = useState<string>('')
    const navigate = useNavigate()
    const dispatch = useAppDispatch();

    useEffect(() => {
        let _view_uuid = searchParams.get('view_uuid')
        let _dataset_uuid = searchParams.get('dataset_uuid')
        let _url = _view_uuid ? `${FETCH_VIEW_DETAIL_URL}${_view_uuid}` : `${FETCH_DATASET_DETAIL_URL}${_dataset_uuid}/`
        axios.get(`${_url}`).then((response) => {
            let _session = searchParams.get('session')
            setSession(_session)
            setViewUUID(_view_uuid)
            setDatasetUUID(_dataset_uuid)
            if (_view_uuid) {
                // append view name to View Breadcrumbs
                let _name = response.data.name
                dispatch(updateMenu({
                    id: `view_edit`,
                    name: _name,
                    link: `/view_edit?id=${response.data.id}`
                }))
            } else {
                // append dataset name to Dataset Breadcrumbs
                let _name = response.data.dataset
                if (response.data.type) {
                    _name = _name + ` (${response.data.type})`
                }
                let moduleName = toLower(response.data.type.replace(' ', '_'))
                dispatch(updateMenu({
                    id: `${moduleName}_dataset_entities`,
                    name: _name,
                    link: `/${moduleName}/dataset_entities?id=${response.data.id}`
                }))
            }
        }).catch((error) => {
            console.log('Error fetching dataset detail ', error)
        })
    }, [searchParams])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabSelected(newValue)
    }

    const onTilingConfigUpdated = () => {
        setTabSelected(1)
    }

    const onBack = () => {
        setTabSelected(tabSelected - 1)
    }

    const onNext = () => {
        setTabSelected(tabSelected + 1)
    }

    const onTilingConfigConfirmed = () => {
        // display message, then navigate to dataset/view tiling config tab
        setAlertMessage('Successfully updating tiling config! Simplification and vector tiles generation will be run in the background.')
    }

    const onRedirectToTilingConfig = () => {
        let _object_type = viewUUID ? 'datasetview' : 'dataset'
        let _object_uuid = viewUUID ? viewUUID : datasetUUID 
        let _fetch_url = `${TILING_CONFIGS_STATUS_URL}${_object_type}/${_object_uuid}/`
        axios.get(_fetch_url).then(
            response => {
                setAlertMessage('')
                let moduleName = toLower(response.data['module']).replace(' ', '_')
                let _path = ''
                let _object_id = response.data['object_id']
                if (viewUUID) {
                    _path = `/view_edit?id=${_object_id}&tab=3`
                } else {
                    _path = `/${moduleName}/dataset_entities?id=${_object_id}&tab=5`
                }
                navigate(_path)
            }
        )
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <AlertMessage message={alertMessage} onClose={() => onRedirectToTilingConfig()} />
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="Tiling Config Tab">
                    <Tab label="1 - Detail" {...a11yProps(0)} />
                    <Tab label="2 - Preview" {...a11yProps(1)} disabled={tabSelected < 1} />
                    <Tab label="3 - Confirm" {...a11yProps(2)} disabled={tabSelected < 2} />
                </Tabs>
            </Box>
            {session && (
                <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                    <TabPanel value={tabSelected} index={0}>
                        <Scrollable>
                            <DatasetTilingConfigMatrix session={session} isReadOnly={false} onTilingConfigUpdated={onTilingConfigUpdated} hideBottomNotes={true} />
                        </Scrollable>
                    </TabPanel>
                    <TabPanel value={tabSelected} index={1} noPadding>
                        <Scrollable>
                            <TilingConfigPreview session={session} viewUUID={viewUUID} datasetUUID={datasetUUID} onBackClicked={onBack} onNextClicked={onNext} />
                        </Scrollable>
                    </TabPanel>
                    <TabPanel value={tabSelected} index={2}>
                        <Scrollable>
                            <TilingConfigConfirm session={session} viewUUID={viewUUID} datasetUUID={datasetUUID} onBack={onBack} onTilingConfigConfirmed={onTilingConfigConfirmed} />
                        </Scrollable>
                    </TabPanel>
                </Grid>
            )}
        </div>
    )
}