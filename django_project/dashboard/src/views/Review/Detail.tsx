import React, {useEffect, useState} from "react";
import {useNavigate} from "react-router-dom";
import {
    Box,
    Grid,
    Tab,
    Tabs
} from "@mui/material";
import '../../styles/Review.scss';
import ReviewStatus from "./DetailStatus";
import Loading from "../../components/Loading";
import TabPanel from "../../components/TabPanel";
import {useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import { UploadSession, ReviewTabInterface, ReviewTabElementInterface } from "../../models/upload";

export interface BoundaryData {
    id: number,
    name: string,
    code: string
}

export interface BoundaryComparisonData {
    id: number,
    mainBoundary?: BoundaryData,
    comparisonBoundary?: BoundaryData,
    similarity: number
}


const SUMMARY = 'Summary'
const MATCH_TABLE = 'Match Table'
const ENTITY_STATUS_UPLOAD_URL = '/api/entity-upload-status-detail/'

const ReviewTab = (Component: React.ElementType, givenProps: ReviewTabInterface) => {
    return <Component {...givenProps} />
  }

export default function ReviewDetail(props: ReviewTabElementInterface) {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [tabSelected, setTabSelected] = useState<number>(0)
    const [loading, setLoading] = useState<boolean>(true)
    const [uploadSessionData, setUploadSessionData] = useState<UploadSession | null>(null)
    const [isDataReady, setIsDataReady] = useState<boolean>(false)
    const [searchParams, setSearchParams] = useSearchParams()
    const [currentInterval, setCurrentInterval] = useState<any>(null)
    const [summaryUpdated, setSummaryUpdated] = useState(null)

    const fetchSessionData = () => {
        axios.get(ENTITY_STATUS_UPLOAD_URL + searchParams.get('id')).then(
            response => {
                if (response.data) {
                    setUploadSessionData({
                        id: response.data.id,
                        name: response.data.source?response.data.source:`${response.data.dataset_name} - ${response.data.adm0_entity}`,
                        created_by: response.data.uploader,
                        created_at: new Date(response.data.started_at).toLocaleDateString(),
                        status: response.data.status,
                        levels: response.data.levels.map((level_data: any) => level_data.level),
                        comparisonReady: response.data.comparison_ready,
                        entityUploadId: searchParams.get('id'),
                        datasetUuid: response.data.dataset_uuid,
                        revisedEntityUuid: response.data.revised_entity_uuid,
                        datasetStyleSource: response.data.dataset_style_source,
                        bbox: response.data.ancestor_bbox,
                        types: response.data.types,
                        revisionNumber: response.data.revision_number,
                        uploadStatus: response.data.upload_status,
                        progress: response.data.progress,
                        datasetName: response.data.dataset_name,
                        adm0Entity: response.data.adm0_entity,
                        moduleName: response.data.module_name
                    })
                    setLoading(false)
                    if (response.data.comparison_ready) {
                        setIsDataReady(true)
                        setSummaryUpdated(new Date())
                    }
                    if (response.data.module_name) {
                        let moduleName = toLower(response.data.module_name.replace(' ', '_'))
                        dispatch(updateMenu({
                            id: `${moduleName}_review_detail`,
                            link: `${moduleName}/review_detail`,
                            name: `Detail ${response.data.dataset_name} - ${response.data.adm0_entity}`
                        }))
                    }                    
                }
        }).catch(error => {
            console.log(error)
            if (error.response) {
                if (error.response.status == 403) {
                    // TODO: use better way to handle 403
                    navigate('/invalid_permission')
                }
            }
        })
    }

    useEffect(() => {
        // Data is not ready yet, add interval check
        if (!isDataReady) {
            if (currentInterval) {
                clearInterval(currentInterval)
                setCurrentInterval(null)
            }
            const interval = setInterval(() => {
                fetchSessionData()
            }, 2000);
            setCurrentInterval(interval)
            return () => clearInterval(interval);
        }
    }, [isDataReady])

    useEffect(() => {
        fetchSessionData()
    }, [searchParams])


    const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabSelected(newValue)
        if (newValue === 0) {
            // refresh summary data
            setSummaryUpdated(new Date())
        }
    }

    useEffect(() => {
        if (!loading) {
            return
        }
    }, [])

    return (<div className='review-detail AdminContentMain'>
        <ReviewStatus data={uploadSessionData}/>
        <Grid container className='review-detail-content' flexDirection='column' flex={1}>
            <Grid item>
                <Box>
                    <Tabs value={tabSelected} onChange={handleTabChange}>
                        <Tab label={SUMMARY} value={0} disabled={loading || !uploadSessionData.comparisonReady}/>
                        <Tab label={MATCH_TABLE} value={1} disabled={loading || !uploadSessionData.comparisonReady}/>
                    </Tabs>
                </Box>
            </Grid>
            <Grid item style={{display: 'flex', flex: 1, flexDirection: 'column'}}>
                { loading ? <Loading label={'Fetching review data...'}/> :
                    <div className={'review-detail-tab-content'}>
                        <TabPanel value={tabSelected} index={0} noPadding>
                            {
                                ReviewTab(props.summary, {
                                    uploadSession: uploadSessionData,
                                    updated_date: summaryUpdated
                                })
                            }
                        </TabPanel>
                        <TabPanel value={tabSelected} index={1} noPadding>
                            {
                                ReviewTab(props.detail, {
                                    uploadSession: uploadSessionData
                                })
                            }
                        </TabPanel>
                    </div>
                }
            </Grid>
        </Grid>
    </div>)
}
