import React, {useEffect, useState} from "react";
import {
  Box,
  Tab,
  Tabs,
  Grid} from "@mui/material";
import axios from "axios";
import {useNavigate} from "react-router-dom";
import {useSearchParams} from "react-router-dom";
import '../styles/UploadWizard.scss';
import {postData} from "../utils/Requests";
import {useAppDispatch} from "../app/hooks";
import {updateMenu} from "../reducers/breadcrumbMenu";
import Loading from "../components/Loading";
import TabPanel, {a11yProps} from '../components/TabPanel';
import {NameField, IdField} from "../models/upload";
import { BatchEntityEditInterface } from "../models/upload";
import Step0 from "./BatchEntityEdit/Step0";
import Step1 from "./BatchEntityEdit/Step1";
import Step2 from "./BatchEntityEdit/Step2";


const LOAD_BATCH_ENTITY_EDIT_URL = '/api/batch-entity-edit/'
const PROCESSING_STATUS = 'PROCESSING'


export default function BatchEntityEditWizard(props: any) {
    const [loading, setLoading] = useState<boolean>(true)
    const [searchParams, setSearchParams] = useSearchParams()
    const navigate = useNavigate()
    const dispatch = useAppDispatch()
    const [tabSelected, setTabSelected] = useState(0)
    const [batchEdit, setBatchEdit] = useState<BatchEntityEditInterface>(null)

    const fetchBatchEditData = () => {
        const batchEditId = searchParams.get('session')
        const datasetId = searchParams.get('dataset')
        if (batchEditId) {
            setLoading(true)
            axios.get(LOAD_BATCH_ENTITY_EDIT_URL + `?batch_edit_id=${batchEditId}&dataset_id=${datasetId}`).then(
                response => {
                    let _data: BatchEntityEditInterface = response.data as BatchEntityEditInterface
                    setBatchEdit(_data)
                    let step = 1
                    if (searchParams.get('step')) {
                        step = parseInt(searchParams.get('step'))
                    } else {
                        step = _data.step
                    }
                    setTabSelected(step)
                    setLoading(false)
                    dispatch(updateMenu({
                        id: `admin_boundaries_dataset_entities`,
                        name: _data.dataset,
                        link: `/admin_boundaries/dataset_entities?id=${datasetId}`
                    }))
                }, error => {
                    console.log(error)
                    setLoading(false)
            })
        }
    }

    const fetchStatus = () => {
        if (!batchEdit) return;
        axios.get(LOAD_BATCH_ENTITY_EDIT_URL + `?batch_edit_id=${batchEdit.id}&dataset_id=${batchEdit.dataset_id}`).then(
            response => {
                let _data: BatchEntityEditInterface = response.data as BatchEntityEditInterface
                setBatchEdit(_data)
            }, error => {
                console.log(error)
        })
    }

    useEffect(() => {
        fetchBatchEditData()
    }, [searchParams])

    useEffect(() => {
        if (batchEdit && batchEdit.status === PROCESSING_STATUS) {
            const interval = setInterval(() => {
                fetchStatus()
            }, 5000)
            return () => clearInterval(interval)
        }
    }, [batchEdit?.status])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        if (newValue > 2) {
            // redirect to dataset detail
            navigate(`/admin_boundaries/dataset_entities?id=${searchParams.get('dataset')}&tab=0`)
        } else {
            let _navigate_to = `/admin_boundaries/edit_entity/wizard?session=${searchParams.get('session')}&step=${newValue}&dataset=${searchParams.get('dataset')}`
            navigate(_navigate_to)
        }
    }

    const handleBack = () => {
        if (tabSelected === 0)
            return;
        handleChange(null, tabSelected - 1)
    }

    const handleNext = () => {
        handleChange(null, tabSelected + 1)
    }

    const isTabDisabled = (index: number) => {
        return false
    }

    return (
        <div className={"UploadWizard AdminContentMain"}>
            <Grid container flexDirection='column'>
                <Grid item>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                        <Tabs className="WizardTabs" value={tabSelected} onChange={handleChange} aria-label="basic tabs example">
                            <Tab key={0} label={'Step 1'} {...a11yProps(0)} disabled={isTabDisabled(0)}
                            />
                            <Tab key={1} label={'Step 2'} {...a11yProps(1)} disabled={isTabDisabled(1)}
                            />
                            <Tab 
                                icon={batchEdit?.status === PROCESSING_STATUS ? <div><Loading size={10} /></div> : null}
                                iconPosition={'start'}
                                key={2} label={'Step 3'} {...a11yProps(2)} disabled={isTabDisabled(2)}
                            />
                        </Tabs>
                    </Box>
                </Grid>
            </Grid>
            <Grid item style={{display: 'flex', flex: 1, flexDirection: 'column'}}>
                {loading ? <Loading/> : 
                    <div className={`UploadWizardContent ${tabSelected !== 2 ? "scrollable":""}`}>
                        <TabPanel key={0} value={tabSelected} index={0}>
                            <Step0 batchEdit={batchEdit} onClickNext={handleNext} />
                        </TabPanel>
                        <TabPanel key={1} value={tabSelected} index={1}>
                            <Step1 batchEdit={batchEdit} onBackClicked={handleBack} onClickNext={(ucodeField: string, nameFields: NameField[], idFields: IdField[], onSaved: (error?: string) => void) => {
                                if (batchEdit.is_read_only) {
                                    handleNext()
                                } else {
                                    let _data = {
                                        'batch_edit_id': batchEdit.id,
                                        'ucode_field': ucodeField.trim(),
                                        'id_fields': idFields.filter(e => e.field && e.idType).map(e => {
                                            e.default = false
                                            return e
                                        }),
                                        'name_fields': nameFields.filter(e => e.field && e.selectedLanguage).map(e => {
                                            e.default = false
                                            return e
                                        })
                                    }
                                    postData(LOAD_BATCH_ENTITY_EDIT_URL, _data).then(
                                        response => {
                                            onSaved()
                                            handleNext()
                                        }
                                      ).catch(error => {
                                        alert('Error saving level...')
                                        onSaved(error)
                                    })
                                }                                
                            }} />
                        </TabPanel>
                        <TabPanel key={2} value={tabSelected} index={2}>
                            <Step2 batchEdit={batchEdit} onBackClicked={handleBack} onClickNext={handleNext} />
                        </TabPanel>
                    </div>
                }                
            </Grid>
        </div>
    )
}
