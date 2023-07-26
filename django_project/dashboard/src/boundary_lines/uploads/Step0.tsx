import React, {useState, useEffect} from "react";
import '../../styles/LayerUpload.scss'
import {
  Box,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormGroup,
  Grid,
  TextField,
  Typography,
} from "@mui/material";
import {DatePicker} from "@mui/x-date-pickers/DatePicker";
import {LocalizationProvider} from "@mui/x-date-pickers";
import {AdapterDateFns} from "@mui/x-date-pickers/AdapterDateFns";
import {useSearchParams} from "react-router-dom";
import {postData} from "../../utils/Requests";
import axios from "axios";
import Loading from "../../components/Loading";
import { WizardStepInterface } from "../../models/upload";

export const LOAD_UPLOAD_SESSION_DETAIL_URL = '/api/upload-session/'

export default function (props: WizardStepInterface) {
  const [isHistoricalUpload, setIsHistoricalUpload] = useState<boolean>(false)
  const [startDate, setStartDate] = useState<null | Date>(null)
  const [endDate, setEndDate] = useState<null | Date>(null)
  const [source, setSource] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    const uploadSession = searchParams.get('session')
    if (uploadSession) {
      // pull the source/description from saved session
      axios.get(LOAD_UPLOAD_SESSION_DETAIL_URL + uploadSession).then(
        response => {
          setSource(response.data.source)
          setDescription(response.data.description)
          setIsHistoricalUpload(response.data.is_historical_upload)
          setStartDate(response.data.historical_start_date)
          setEndDate(response.data.historical_end_date)
        }, error => {
          console.log(error)
        })
    }
  }, [])

  const handleNextClick = () => {
    setLoading(true)
    postData((window as any).updateUploadSessionUrl, {
      'source': source,
      'description': description,
      'session': searchParams.get('session'),
      'is_historical_upload': isHistoricalUpload,
      'historical_start_date': startDate,
      'historical_end_date': endDate
    }).then( response => {
      if (response.data.session_id) {
        props.onClickNext()
      }
    }).catch(error => {
      alert('Error adding new data.')
      console.log(error)
    })
  }

  return (<div className='FormContainer'>
    <FormControl className='FormContent' disabled={props.isReadOnly}>
      <Grid container columnSpacing={2} rowSpacing={2}>
        <Grid className={'form-label'} item md={2} xl={2} xs={12}>
          <Typography variant={'subtitle1'}>Source</Typography>
        </Grid>
        <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
          <TextField
            disabled={loading || props.isReadOnly}
            id="input_file"
            hiddenLabel={true}
            type={"text"}
            onChange={val => setSource(val.target.value)}
            value={source}
            sx={{ width: '100%' }}
          />
        </Grid>
        <Grid className={'form-label'} item md={2} xl={2} xs={12}>
          <Typography variant={'subtitle1'}>Description</Typography>
        </Grid>
        <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
          <TextField
            disabled={loading || props.isReadOnly}
            id="input_file"
            hiddenLabel={true}
            type={"text"}
            onChange={val => setDescription(val.target.value)}
            value={description}
            sx={{ width: '100%' }}
          />
        </Grid>
        <Grid item md={2} xl={2} xs={12}>
        </Grid>
        <Grid item md={10} xs={12}>
          <FormGroup>
            <FormControlLabel control={<Checkbox value={isHistoricalUpload} checked={isHistoricalUpload}
                                                 disabled={loading || props.isReadOnly}
                                                 onChange={(val) => setIsHistoricalUpload(val.target.checked)}/>}
                              label="Historical upload" />
          </FormGroup>
          <div style={{ textAlign: 'initial' }}>
            <Typography variant={"subtitle2"} style={{ marginTop: 2, marginBottom: 10 }} className={ !isHistoricalUpload || props.isReadOnly ? "disabled-text" : ""}>GeoRepo validity from</Typography>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="Start Date"
                inputFormat="MM/dd/yyyy"
                value={startDate}
                disabled={!isHistoricalUpload || loading || props.isReadOnly}
                PopperProps={{
                  placement: "top-end",
                }}
                renderInput={(params: any) => <TextField {...params} sx={{ marginRight: 2 }}/>}
                onChange={(val) => setStartDate(val)}/>
              <DatePicker
                label="End Date"
                inputFormat="MM/dd/yyyy"
                minDate={startDate}
                value={endDate}
                PopperProps={{
                  placement: "top-end",
                }}
                disabled={!isHistoricalUpload || loading || props.isReadOnly}
                renderInput={(params: any) => <TextField {...params} />}
                onChange={(val) => setEndDate(val)}/>
            </LocalizationProvider>
          </div>
        </Grid>
      </Grid>
      <Box sx={{ textAlign: 'right' }}>
        <div className='button-container'>
          <Button
            variant={"contained"}
            disabled={loading || !source}
            onClick={handleNextClick}>
              <span style={{ display: 'flex' }}>
            { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Next" }</span>
          </Button>
        </div>
      </Box>
    </FormControl>
  </div>)
}
