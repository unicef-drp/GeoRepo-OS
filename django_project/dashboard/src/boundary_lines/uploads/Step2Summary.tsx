import React, {useEffect, useState} from 'react';
import "../../styles/LayerUpload.scss";

import Grid from '@mui/material/Grid';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import LoadingButton from "@mui/lab/LoadingButton";
import Container from '@mui/material/Container';
import {Button} from "@mui/material";
import axios from "axios";
import {useNavigate, useSearchParams} from "react-router-dom";
import {postData} from "../../utils/Requests";
import Scrollable from '../../components/Scrollable';
import Loading from "../../components/Loading";
import {UploadInterface, SummaryInterface} from "../../models/upload";
import FieldMappingSummary from '../../components/Uploads/FieldMappingSummary';


interface Step2SummaryInterface {
  uploads: UploadInterface[],
  isReadOnly: boolean,
  onBackClicked: Function,
  onClickNext: () => void
}

const UPLOAD_SUMMARY_URL = '/api/upload-session-summary/'
const IMPORT_VALIDATE_URL = '/api/layer-upload-preprocess/'

export default function Step2Summary(props: Step2SummaryInterface) {
  const [summaries, setSummaries] = useState<SummaryInterface[]>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [isValid, setIsValid] = useState<boolean>(false)
  const [alertMessage, setAlertMessage] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    axios.get(UPLOAD_SUMMARY_URL + searchParams.get('session')).then(
      response => {
        setSummaries(response.data.summaries);
        setLoading(false)
        for (const summaryData of (response.data as SummaryInterface[])) {
          if (summaryData.properties !== '[]') {
            setIsValid(false)
            return
          }
        }
        setIsValid(true)
      },
      error => console.log(error)
    )
  }, [searchParams])

  const handleSubmit = () => {
    setLoading(true)
    setAlertMessage('')
    postData(IMPORT_VALIDATE_URL,
      {
        'upload_session': searchParams.get('session')
      }).then(response => {
        setLoading(false)
        props.onClickNext()
      }).catch(
        error => {
          setLoading(false)
          if (error.response && error.response.data && 'detail' in error.response.data) {
            setAlertMessage(error.response.data['detail'])
          }
      })
  }

  return (
    loading ? <div className="loading-container"><Loading /></div> :
    <Scrollable>
      <div className='FormContainer'>
        { alertMessage ?
          <Container>
            <Alert style={{ width: '750px', textAlign: 'left', marginLeft: 'auto', marginRight: 'auto' }} severity={'error'}>
              <AlertTitle>Error</AlertTitle>
              <p className="display-linebreak">
                { alertMessage }
              </p>
            </Alert>
          </Container>
          : null }
        <FieldMappingSummary summaries={summaries} />
        <div className='button-container button-submit-container'>
          {loading ?
            <LoadingButton loading loadingPosition="start"
                           startIcon={<div style={{width: 20}}/>}
                           variant="outlined">
              Saving...
            </LoadingButton> :
            (<Grid container direction='row' justifyContent='space-between'>
            <Grid item>
              <Button onClick={() => props.onBackClicked()} variant="outlined">
                Back
              </Button>
            </Grid>
            <Grid item>
            <Button onClick={handleSubmit} variant="contained">
              {props.isReadOnly ? 'Next': 'Import & Validate'}
            </Button>
            </Grid>
          </Grid>)
          }
        </div>
      </div>
    </Scrollable>
  )
}
