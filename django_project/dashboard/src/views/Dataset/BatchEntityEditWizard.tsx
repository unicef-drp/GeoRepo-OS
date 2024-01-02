import React, {useEffect, useState} from "react";
import {
  Box,
  Tab,
  Tabs,
  Grid} from "@mui/material";
import toLower from "lodash/toLower";
import {useNavigate} from "react-router-dom";
import {useSearchParams} from "react-router-dom";
import '../../styles/UploadWizard.scss'
import {postData} from "../../utils/Requests";
import {useAppDispatch, useAppSelector} from "../../app/hooks";
import {currentDataset, changeCurrentDataset, updateMenu} from "../../reducers/breadcrumbMenu";
import {setModule} from "../../reducers/module";
import {DatasetRoute} from "../../views/routes";
import Loading from "../../components/Loading";
import AlertDialog from '../../components/AlertDialog'
import TabPanel, {a11yProps} from '../../components/TabPanel';
import { WizardStepInterface, WizardStepElementInterface } from "../../models/upload";
import TaskStatus from '../../components/TaskStatus';


export default function BatchEntityEditWizard(props: any) {
    const [loading, setLoading] = useState<boolean>(true)
    const [searchParams, setSearchParams] = useSearchParams()
    const [uploadSession, setUploadSession] = useState<string>('')
    const navigate = useNavigate()
    let currentDatasetId = useAppSelector(currentDataset)
    const dispatch = useAppDispatch()
    const [isInProgress, setIsInProgress] = useState(false)
    const [tabSelected, setTabSelected] = useState(0)

    const initWizard = () => {

    }

    useEffect(() => {

    }, [searchParams])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        let _navigate_to = `/${props.moduleName}/upload_wizard?session=${searchParams.get('session')}&step=${newValue}&dataset=${currentDatasetId ? currentDatasetId : searchParams.get('dataset')}`
        navigate(_navigate_to)
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
        
    }

    

}
