import React, {useState, useEffect} from "react";
import axios from "axios";
import {Box, Tab, Tabs, Grid} from "@mui/material";
import TabPanel, {a11yProps} from '../../components/TabPanel';
import Step2LevelUpload from "./Step2LevelUpload";
import {LanguageOption, fetchLanguages} from "../../utils/Requests";
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import '../../styles/UploadWizard.scss'
import Step2Summary from "./Step2Summary";
import Loading from "../../components/Loading";
import {
  UploadInterface, WizardStepInterface
} from "../../models/upload"


export default function Step2(props: WizardStepInterface) {
  const [languageOptions, setLanguageOptions] = useState<[] | LanguageOption[]>([])
  const [loading, setLoading] = useState(true)
  const [uploads, setUploads] = useState<UploadInterface[]>([])
  const [allValid, setAllValid] = useState(false)

  const setTabSelected = (tab: number) => {
    props.setChildTab(tab)
  }

  const fetchUploadData = () => {
    // Get all uploaded files
    axios.get(
      (window as any).layerUploadList +
      `?upload_session=${props.uploadSession}`
    ).then(
      response => {
        if (response.data) {
          setUploads(response.data)
        }
      },
      error => console.error(error)
    )
  }

  useEffect(() => {
    props.setFormIsDirty(false)
  }, [props.initChildTab])

  useEffect(() => {
    // Get languages
    fetchLanguages().then(languages => {
      setLanguageOptions(languages)
    })
    fetchUploadData()
  }, [])

  useEffect(() => {
    fetchUploadData()
  }, [props.onReset])

  useEffect(() => {
    if (uploads.length > 0) {
      for (const uploadData of uploads) {
        if (!uploadData.form_valid) {
          setAllValid(false)
          return
        }
      }
      setAllValid(true)
    }
  }, [uploads])

  const updateLevelData = (uploadData: UploadInterface) => {
    setUploads(uploads.map(upload => {
      if (upload.id == uploadData.id) {
        return uploadData
      }
      return upload
    }))
  }

  const handleTabOnChange = (event: React.SyntheticEvent, newValue: number) => {
    if (props.canChangeTab(newValue)) {
      setTabSelected(newValue)
      props.setFormIsDirty(false)
    }
  }
  return <div className="AdminContentMain">
    { uploads.length === 0 || languageOptions.length === 0 ?
      <Loading color="inherit" /> :
      <Grid container className='Step2' flexDirection='column' flex={1}>
        <Grid item>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={props.initChildTab}
                  onChange={handleTabOnChange}
                  aria-label="basic tabs example">
              { uploads.map( (upload, index) =>
                <Tab
                    icon={ upload.form_valid ? <CheckBoxIcon sx={{ fontSize: 15 }} color="success" /> : null}
                    iconPosition={'start'}
                    key={index} label={ "Level " + upload.level + (props.isFormDirty() && props.initChildTab === index ? '*': '') }
                    {...a11yProps(index)}/>
              )}
              <Tab label={'Summary'} {...a11yProps(uploads.length)} disabled={!allValid} />
            </Tabs>
          </Box>
        </Grid>
        <Grid item className="Step2Content">
          { uploads.map( (upload, index) => (
            <TabPanel value={props.initChildTab} index={index} key={index}>
              <Step2LevelUpload languageOptions={languageOptions} uploadData={upload} updateLeveData={updateLevelData}
                 onBackClicked={props.onBackClicked} setFormIsDirty={props.setFormIsDirty} isReadOnly={props.isReadOnly}
                 canResetProgress={props.canResetProgress} onResetProgress={props.onResetProgress} />
            </TabPanel>
            )
          )}
          <TabPanel value={props.initChildTab} index={uploads.length}>
            <Step2Summary uploads={uploads} onBackClicked={props.onBackClicked}
              onClickNext={props.onClickNext} isReadOnly={props.isReadOnly}/>
          </TabPanel>
        </Grid>
      </Grid>
    }
  </div>
}
