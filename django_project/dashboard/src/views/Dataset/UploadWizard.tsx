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


interface UploadWizardInterface {
  steps: WizardStepElementInterface[]
  moduleName: string,
  datasetEntitiesPath: string
}

interface NavigateToInterface {
  type: number,
  nav: string
}

const WizardStep = (Component: React.ElementType, givenProps: WizardStepInterface) => {
  return <Component {...givenProps} />
}

const CONFIRM_RESET_SESSION_URL = '/api/reset-upload-session/'

export default function UploadWizard (props: UploadWizardInterface) {
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [uploadSession, setUploadSession] = useState<string>('')
  const [editable, setEditable] = useState<boolean>(true)
  const navigate = useNavigate()
  let currentDatasetId = useAppSelector(currentDataset);
  const dispatch = useAppDispatch();
  const [isReadOnly, setIsReadOnly] = useState(false)
  const [isInProgress, setIsInProgress] = useState(false)
  const [hasAnyResult, setHasAnyResult] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [confirmationOpen, setConfirmationOpen] = useState(false)
  const [navigateTo, setNavigateTo] = useState<NavigateToInterface>({
    type: -1,
    nav: ''
  })
  const [tabSelected, setTabSelected] = useState(0)
  const [childTab, setChildTab] = useState(0)
  const [resetChildTab, setResetChildTab] = useState(null)
  const [ongoingTab, setOngoingTab] = useState(-1)
  const [lastStep, setLastStep] = useState(0)
  const [resetProgressOpen, setResetProgressOpen] = useState(false)
  const [resetTaskId, setResetTaskId] = useState('')
  const [updateStepInProgress, setUpdateStepInProgress] = useState(false)

  const initUploadWizardStep = () => {
    if (props.moduleName) {
      dispatch(setModule(props.moduleName))
    }
    if (searchParams.get('dataset')) {
      dispatch(changeCurrentDataset(searchParams.get('dataset')))
      currentDatasetId = searchParams.get('dataset')
    } else {
      if (!currentDatasetId) {
        navigate(DatasetRoute.path)
        return
      }
    }
    setIsDirty(false)
    if (searchParams.get('session')) {
      let step = 1
      if (searchParams.get('step')) {
        step = parseInt(searchParams.get('step'))
      }
      setUpdateStepInProgress(true)
      postData((window as any).uploadSessionUpdateStep, {
        'id': searchParams.get('session'),
        'step': step
      }).then(
        response => {
          setUpdateStepInProgress(false)
          // append dataset name to Dataset Breadcrumbs
          let _name = response.data.dataset_name
            if (response.data.type) {
                _name = _name + ` (${response.data.type})`
            }
          dispatch(updateMenu({
            id: `${props.moduleName}_dataset_entities`,
            name: _name,
            link: `${props.datasetEntitiesPath}?id=${currentDatasetId}`
          }))
          dispatch(setModule(toLower(response.data.type.replace(' ', '_'))))
          if (response.data.status === 'Canceled') {
            // add Canceled status after upload
            dispatch(updateMenu({
              id: `${props.moduleName}_upload_wizard`,
              name: 'Upload (Canceled)'
            }))
          }
          setTabSelected(step);
          if (step === 4) {
            setEditable(false)
          }
          if (response.data['ongoing_step'] !== undefined) {
            let _ongoing_tab = response.data['ongoing_step']
            setOngoingTab(_ongoing_tab)
          }
          setIsReadOnly(response.data.is_read_only)
          setIsInProgress(response.data.is_in_progress)
          setHasAnyResult(response.data.has_any_result)
          setLastStep(response.data.last_step)
          setLoading(false)
        }
      ).catch(error => {
        setUpdateStepInProgress(false)
        setLoading(false)
        alert('There is something wrong, please try again later')
      })
      setUploadSession(searchParams.get('session'))
    }
  }

  useEffect(() => {
    initUploadWizardStep()
  }, [searchParams])

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    let _navigate_to = `/${props.moduleName}/upload_wizard?session=${searchParams.get('session')}&step=${newValue}&dataset=${currentDatasetId ? currentDatasetId : searchParams.get('dataset')}`
    if (isDirty) {
      // toggle confirmation
      setConfirmationOpen(true)
      setNavigateTo({
        'type': 0,
        'nav': _navigate_to
      })
      return;
    }
    navigate(_navigate_to)
  }

  const handleBack = () => {
    if (tabSelected === 0)
      return;
    handleChange(null, tabSelected - 1)
  }

  const handleConfirmationClose = () => {
    setConfirmationOpen(false)
    setNavigateTo({
      type: -1,
      nav: ''
    })
  }

  const handleNext = () => {
    setChildTab(0)
    handleChange(null, tabSelected + 1)
  }

  const handleConfirmationOk = () => {
    setResetChildTab(new Date())
    if (navigateTo.type === 0) {
      navigate(navigateTo.nav)
    } else if (navigateTo.type === 1) {
      // navigate to child tab
      setChildTab(parseInt(navigateTo.nav))
    }
    handleConfirmationClose()
  }

  const checkFormIsDirty = () => {
    return isDirty
  }

  const canChangeTab = (tab: number) => {
    if (isDirty) {
      // toggle confirmation
      setConfirmationOpen(true)
      setNavigateTo({
        'type': 1,
        'nav': tab.toString()
      })
      return false
    }
    return true
  }

  const isTabDisabled = (index: number) => {
    if (index === props.steps.length) {
      return !isReadOnly && (tabSelected < index || loading)
    }
    if (ongoingTab !== -1) {
      return ongoingTab < index || loading
    }
    if (!isReadOnly && (isInProgress || hasAnyResult)) {
      return index > lastStep || loading
    }
    return !isReadOnly && (tabSelected < index || loading || !editable)
  }

  const isTabReadOnly = (index: number) => {
    if (isReadOnly)
      return true
    if (ongoingTab !== -1 && (isInProgress || hasAnyResult))
      return index < ongoingTab
    if (isInProgress || hasAnyResult)
      return index < lastStep
    return false
  }

  const onResetProgress = () => {
    setResetProgressOpen(true)
  }

  const handleResetProgressOnOk = () => {
    setLoading(true)
    postData(`${CONFIRM_RESET_SESSION_URL}${searchParams.get('session')}/${tabSelected}/`, {}).then(
      response => {
        setResetTaskId(response.data['task_id'])
        setLoading(false)
        handleResetProgressOnClose()
      }
    ).catch(error => {
      setLoading(false)
      alert('There is something wrong, please try again later')
    })
  }

  const handleResetProgressOnClose = () => {
    setResetProgressOpen(false)
  }
  return (
    <div className={"UploadWizard AdminContentMain"}>
      <AlertDialog open={confirmationOpen} alertClosed={handleConfirmationClose}
          alertConfirmed={handleConfirmationOk}
          alertDialogTitle={'Unsaved changes'}
          alertDialogDescription={'You have unsaved changes. Are you sure to leave this page?'}
          confirmButtonText='Leave'
          confirmButtonProps={{color: 'error', autoFocus: true}}
      />
      <AlertDialog open={resetProgressOpen} alertClosed={handleResetProgressOnClose}
          alertConfirmed={handleResetProgressOnOk}
          alertDialogTitle={'Confirm edit'}
          alertDialogDescription={'You have results from the next upload steps, editing this page will reset the progress. Are you sure to edit this page?'}
          confirmButtonText='Confirm'
          alertLoading={loading}
          confirmButtonProps={{color: 'error', autoFocus: true}}
      />
      <TaskStatus dialogTitle='Reset upload session' errorMessage='Error! There is unexpected error while resetting upload session, please contact Administrator.'
        successMessage='' task_id={resetTaskId} onCompleted={() => {
          setResetTaskId('')
          initUploadWizardStep()
        }}
        />
      <Grid container flexDirection='column' flex={1}>
        <Grid item>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabSelected} onChange={handleChange} aria-label="basic tabs example">
              {
                props.steps.map((step, index) => {
                  return <Tab 
                      icon={ index===ongoingTab ? <div><Loading size={10} /></div> : null}
                      iconPosition={'start'}
                      key={index} label={step.title} {...a11yProps(index)} disabled={isTabDisabled(index)}
                    />
                })
              }
            </Tabs>
          </Box>
        </Grid>
        <Grid item style={{display: 'flex', flex: 1, flexDirection: 'column'}}>
          {loading ? <Loading/> : <div className={`UploadWizardContent ${tabSelected !== 2 ? "scrollable":""}`}>
              {
                props.steps.map((step, index) => {
                  return <TabPanel key={index} value={tabSelected} index={index}>
                    {WizardStep(step.element, {
                      datasetId: currentDatasetId,
                      uploadSession: uploadSession,
                      isReadOnly: isTabReadOnly(index),
                      isUpdatingStep: updateStepInProgress,
                      setFormIsDirty: setIsDirty,
                      canChangeTab: canChangeTab,
                      isFormDirty: checkFormIsDirty,
                      setEditable: setEditable,
                      // setIsReadOnly: setIsReadOnly,
                      initChildTab: childTab,
                      canResetProgress: !isReadOnly && (isInProgress || hasAnyResult)  && tabSelected != lastStep,
                      setChildTab: setChildTab,
                      onBackClicked: handleBack,
                      onClickNext: handleNext,
                      onReset: resetChildTab,
                      onResetProgress: onResetProgress,
                      onCheckProgress: initUploadWizardStep
                    })}
                  </TabPanel>
                })
              }
            </div>
          }
        </Grid>
      </Grid>
    </div>
  )
}
