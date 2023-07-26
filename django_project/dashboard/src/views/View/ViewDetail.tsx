import React, {useEffect, useState} from 'react';

import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Tooltip from '@mui/material/Tooltip';
import Button from '@mui/material/Button';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import streamSaver from 'streamsaver';
import TabPanel, {a11yProps} from '../../components/TabPanel';
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import ViewCreate, {TempQueryCreateInterface} from './ViewCreate';
import {postData} from "../../utils/Requests";
import View, {isReadOnlyView} from "../../models/view";
import DatasetEntities from '../Dataset/DatasetEntities';
import DatasetTilingConfig from '../Dataset/Configurations/DatasetTilingConfig';
import ViewPermission from './ViewPermission';
import '../../styles/ViewDetail.scss';

const QUERY_CHECK_URL = '/api/query-view-preview/'
const DOWNLOAD_VIEW_URL = '/api/view-download/'

interface ButtonContainerInterface {
    children?: React.ReactNode;
    onClick: () => void;
}

export default function ViewDetail() {
    const dispatch = useAppDispatch()
    const [tabSelected, setTabSelected] = useState(0)
    const [isQueryValid, setIsQueryValid] = useState(false)
    const [previewSession, setPreviewSession] = useState(null)
    const [tempData, setTempData] = useState<TempQueryCreateInterface>(null)
    const [view, setView] = useState<View>(null)
    const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
    const downloadAsOpen = Boolean(anchorEl)
    const [isDownloading, setIsDownloading] = useState(false)
    
    useEffect(() => {
        if (view) {
            setPreviewSession(view.preview_session)
            if (view.id) {
                let _isReadOnly = isReadOnlyView(view)
                if (_isReadOnly) {
                    setTabSelected(1)
                    dispatch(updateMenu({
                        id: `view_edit`,
                        name: `View ${view.name}`
                    }))
                } else {
                    dispatch(updateMenu({
                        id: `view_edit`,
                        name: `Edit ${view.name}`
                    }))
                }                
            }
        }
    }, [view])

    const onQueryValidation = (isValid: boolean, query: string) => {
        if (view) {
            // detail page, check if query is changed
            if (view.query_string != query) {
                setIsQueryValid(isValid)
            } else {
                // set query valid if this is from detail
                setIsQueryValid(true)
            }
        } else {
            setIsQueryValid(isValid)
        }
    }

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabSelected(newValue)
    }

    const onPreviewClicked = (tempData: TempQueryCreateInterface) => {
        let _post_data:any = {
            'query_string': tempData.queryString,
            'dataset': tempData.dataset
        }
        if (previewSession) {
            _post_data['session'] = previewSession
        }
        postData(QUERY_CHECK_URL, _post_data).then(
            response => {
                setTempData(tempData)
                setPreviewSession(response.data['session'])
                setTabSelected(1)
            }
          ).catch(
            error => {
                setTempData(null)
                console.log(error)
            }
          )
    }

    const onViewUpdated = () => {

    }

    const downloadViewOnClick = (format: string) => {
        setIsDownloading(true)
        setAnchorEl(null)
        let _queryParams = []
        if (previewSession) {
            _queryParams.push(`session=${previewSession}`)
        }
        if (format) {
            _queryParams.push(`format=${format}`) 
        }
        fetch(`${DOWNLOAD_VIEW_URL}${view.id}/?${_queryParams.join('&')}`)
        .then((response) => {
            setIsDownloading(false)
            if (response.status === 200) {
                const readableStream = response.body
                let _filename = response.headers.get('content-disposition').split('filename=')[1].split(';')[0]
                _filename = _filename.replaceAll('"', '')
                const fileStream = streamSaver.createWriteStream(_filename)
                // more optimized
                if (window.WritableStream && readableStream.pipeTo) {
                    return readableStream.pipeTo(fileStream)
                            .then(() => {})
                }
                (window as any).writer = fileStream.getWriter()

                const reader = response.body.getReader()
                const pump = () => reader.read()
                    .then(res => res.done
                    ? (window as any).writer.close()
                    : (window as any).writer.write(res.value).then(pump))
                pump()
            } else if (response.status === 404) {
                alert('Error! The requested file does not exist!')
            } else {
                response.json().then((data) => {
                    let _json = data as {detail?:string}
                    if (_json && _json.detail) {
                        alert(`Failed to download: ${_json.detail}`)
                    } else {
                        alert('Failed to download the requested file!')
                    }
                })                
            }
        })
        .catch((error) => {
            setIsDownloading(false)
            console.log('Failed to download file!', error)
            alert('Failed to download the requested file!')
        })
    }

    return (
        <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
            <Box display={'flex'} flexDirection={'row'} justifyContent={'space-between'} sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabSelected} onChange={handleChange} aria-label="Configuration Tab">
                    <Tab label={ "Detail" + (tempData != null ? "*" : "") } {...a11yProps(0)} />
                    <Tab label="Preview" {...a11yProps(1)} disabled={!isQueryValid} />
                    { view && view.permissions && view.permissions.includes('Manage') && (
                        <Tab label="Permission" {...a11yProps(2)} disabled={view === null} />
                    )}
                    { view && view.permissions && view.permissions.includes('Manage') && (
                        <Tab label="Tiling Config" {...a11yProps(3)} disabled={view === null} />
                    )}
                </Tabs>
                { tabSelected === 1 && <Box flexDirection={'column'} justifyContent={'center'} display={'flex'} sx={{marginRight: '20px'}}>
                    <Tooltip title='Download view with possible filters: Country, Admin Level'>
                        <Button disabled={isDownloading}
                            id='download-as-button'
                            className={'ThemeButton MuiButton-secondary DownloadAsButton'}
                            onClick={(event: React.MouseEvent<HTMLButtonElement>) => setAnchorEl(event.currentTarget)}
                            aria-controls={downloadAsOpen ? 'download-as-menu' : undefined}
                            aria-haspopup="true"
                            aria-expanded={downloadAsOpen ? 'true' : undefined}
                            disableElevation
                            endIcon={<KeyboardArrowDownIcon />}
                        >
                            Download As
                        </Button>
                    </Tooltip>
                    <Menu
                        id="download-as-menu"
                        anchorEl={anchorEl}
                        open={downloadAsOpen}
                        onClose={() => setAnchorEl(null)}
                        MenuListProps={{
                            'aria-labelledby': 'download-as-button',
                        }}
                    >
                        <MenuItem onClick={() => downloadViewOnClick('geojson')}>Geojson</MenuItem>
                        <MenuItem onClick={() => downloadViewOnClick('shapefile')}>Shapefile</MenuItem>
                        <MenuItem onClick={() => downloadViewOnClick('kml')}>KML</MenuItem>
                        <MenuItem onClick={() => downloadViewOnClick('topojson')}>Topojson</MenuItem>
                    </Menu>
                </Box>
                }
            </Box>
            <Grid container sx={{ flexGrow: 1, flexDirection: 'column' }}>
                <TabPanel value={tabSelected} index={0}>
                    <ViewCreate onQueryValidation={onQueryValidation}
                     onPreviewClicked={onPreviewClicked} tempData={tempData}
                     onViewLoaded={(view: View) => setView(view)} />
                </TabPanel>
                <TabPanel value={tabSelected} index={1} noPadding>
                    { (tempData && previewSession && tempData.dataset) ? (
                        <Grid container flexDirection={'column'} sx={{height:'100%'}}>
                            <Grid item sx={{display:'flex', flex:1, height:'100%'}}>
                                <DatasetEntities datasetId={tempData.dataset} session={previewSession}
                                    mapProps={{
                                        'datasetViewUuid': view ? view.uuid : null
                                    }} />
                            </Grid>
                        </Grid>
                    ) : (view && previewSession) ? (
                        <Grid container flexDirection={'column'} sx={{height:'100%'}}>
                            <Grid item sx={{display:'flex', flex:1, height:'100%'}}>
                                <DatasetEntities datasetId={view.dataset} session={previewSession}
                                    datasetUuid={view.dataset_uuid} datasetStyleSourceName={view.dataset_style_source_name}
                                    viewUuid={view.uuid}
                                    mapProps={{
                                        'datasetViewUuid': view.uuid
                                    }} />
                            </Grid>
                        </Grid>
                    ): null
                    }
                </TabPanel>
                { view && view.permissions && view.permissions.includes('Manage') && (
                    <TabPanel value={tabSelected} index={2} noPadding>
                        <ViewPermission view={view} onViewUpdated={onViewUpdated} />
                    </TabPanel>
                )}
                { view && view.permissions && view.permissions.includes('Manage') && (
                    <TabPanel value={tabSelected} index={3} padding={1}>
                        <DatasetTilingConfig view={view} isReadOnly={view.is_read_only} />
                    </TabPanel>
                )}
            </Grid>
        </div>
    )
}