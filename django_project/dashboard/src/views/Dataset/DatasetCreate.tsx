import React, {useEffect, useRef, useState} from "react";
import CancelIcon from '@mui/icons-material/Cancel';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import InputAdornment from '@mui/material/InputAdornment';
import axios from "axios";
import debounce from "lodash/debounce";
import {Box, Button, FormControl, Grid, MenuItem, TextField, Typography} from "@mui/material";
import Select, { SelectChangeEvent } from '@mui/material/Select';
import Dataset from '../../models/dataset';
import HtmlTooltip from "../../components/HtmlTooltip";
import Loading from "../../components/Loading";
import toLower from "lodash/toLower";
import {postData} from "../../utils/Requests";
import {setModule} from "../../reducers/module";
import {useAppDispatch} from "../../app/hooks";
import {useNavigate} from "react-router-dom";
import Scrollable from '../../components/Scrollable';
import PrivacyLevel from "../../models/privacy";
import AlertMessage from '../../components/AlertMessage';

import '../../styles/LayerUpload.scss';


const DATASET_SHORT_CODE_MAX_LENGTH = 4
const CHECK_SHORT_CODE_DATASET_URL = '/api/check-dataset-short-code/'
const FETCH_PRIVACY_LEVEL_LABELS = '/api/permission/privacy-levels/'

export default function DatasetCreate() {
  const [loading, setLoading] = useState<boolean>(true)
  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [modules, setModules] = useState<any[]>([])
  const [selectedModule, setSelectedModule] = useState<string>('')
  const [shortCode, setShortCode] = useState<string>(null)
  const [isValidShortCode, setIsValidShortCode] = useState<boolean>(false)
  const [shortCodeError, setShortCodeError] = useState<string>(null)
  const [maxPrivacyLevel, setMaxPrivacyLevel] = useState(4)
  const [minPrivacyLevel, setMinPrivacyLevel] = useState(1)
  const [privacyLevelLabels, setPrivacyLevelLabels] = useState<PrivacyLevel>({})
  const [alertMessage, setAlertMessage] = useState<string>('')
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const debounceCheckShortCode = useRef(debounce((code) => {
      checkShortCode(code)
    }, 500)).current

  const submitCreateDataset = () => {
    if (maxPrivacyLevel < minPrivacyLevel) {
      setAlertMessage('Error! Maximum privacy level cannot be lower than minimum privacy level')
      return;
    }
    setLoading(true)
    postData('/api/create-dataset/', {
      module_id: selectedModule,
      name: name,
      description: description,
      short_code: shortCode,
      max_privacy_level: maxPrivacyLevel,
      min_privacy_level: minPrivacyLevel
    }).then((response) => {
      setLoading(false)
      if (response.status === 201) {
        let _dataset: Dataset = response.data
        let moduleName = toLower(_dataset.type).replace(' ', '_')
        dispatch(setModule(moduleName))
        navigate(`/${moduleName}/dataset_entities?id=${_dataset.id}`)
      }
    }).catch((error) => {
      setLoading(false)
      if (error.response.data && 'detail' in error.response.data) {
        alert(error.response.data['detail'])
      } else {
        alert("Error creating a dataset.")
      }
    })
  }

  useEffect(() => {
    axios.get('/api/module-list/').then(
      response => {
        if (response.data) {
          setLoading(false)
          setModules(response.data)
        }
      }
    )
    fetchPrivacyLevelLabels()
  }, [])

  useEffect(() => {
    if (shortCode) {
      debounceCheckShortCode(shortCode)
    } else {
      setIsValidShortCode(false)
    }
  }, [shortCode])

  const checkShortCode = (code: string) => {
    postData(CHECK_SHORT_CODE_DATASET_URL, {
      'short_code': code
    }).then((response) => {
      setIsValidShortCode(response.data['is_available'])
      if ('error' in response.data)
        setShortCodeError(response.data['error'])
    }).catch(() => {
      console.log("Error checking dataset short code.")
    })
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
    <div className="AdminContentMain">
      <Scrollable>
        <div className='FormContainer'>
        <FormControl className='FormContent'>
          <AlertMessage message={alertMessage} onClose={() => setAlertMessage('')} />
          <Grid container columnSpacing={2} rowSpacing={2}>
            <Grid className={'form-label'} item md={2} xl={2} xs={12}>
              <Typography variant={'subtitle1'}>Name</Typography>
            </Grid>
            <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
              <TextField
                disabled={loading}
                id="dataset_name"
                hiddenLabel={true}
                type={"text"}
                onChange={val => setName(val.target.value)}
                defaultValue=""
                sx={{ width: '100%' }}
              />
            </Grid>
            <Grid className={'form-label'} item md={2} xl={2} xs={12}>
              <Typography variant={'subtitle1'}>Description</Typography>
            </Grid>
            <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
              <TextField
                multiline
                minRows={3}
                disabled={loading}
                id="dataset_description"
                hiddenLabel={true}
                type={"text"}
                onChange={val => setDescription(val.target.value)}
                defaultValue=""
                sx={{ width: '100%' }}
              />
            </Grid>
            <Grid className={'form-label'} item md={2} xl={2} xs={12}>
              <Typography variant={'subtitle1'}>Type</Typography>
            </Grid>
            <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
              <Select
                labelId={'module'}
                sx={{ minWidth: '300px' }}
                value={selectedModule}
                label={''}
                onChange={(e) => setSelectedModule(e.target.value as string)}
              >
                {modules.map((module: any) =>
                  <MenuItem
                    value={module.id}
                    key={module.id}>{module.name}
                  </MenuItem>
                )}
              </Select>
            </Grid>
            <Grid item className={'form-label'} md={2} xl={2} xs={12}>
              <Grid container flexDirection={'row'} alignItems={'center'}>
                <Grid item>
                  <Typography variant={'subtitle1'}>
                    Short Code
                  </Typography>
                </Grid>
                <Grid item>
                  <HtmlTooltip tooltipTitle='Dataset Short Code'
                      tooltipDescription={<p>Dataset short code will be used as prefix in UCode. It must be 4 characters and unique</p>}
                  />            
                </Grid>
              </Grid>
            </Grid>
            <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
              <TextField
                disabled={loading}
                id="dataset_short_code"
                hiddenLabel={true}
                type={"text"}
                onChange={val => setShortCode(val.target.value)}
                defaultValue=""
                inputProps={{ 
                  maxLength: DATASET_SHORT_CODE_MAX_LENGTH
                }}
                sx={{ minWidth: '300px' }}
                InputProps={{
                  endAdornment:
                    <InputAdornment position='end'>
                      { shortCode != null ? isValidShortCode ? <CheckCircleIcon color="success" /> : <CancelIcon color="error" /> : null}
                    </InputAdornment>
                }}
                error={!isValidShortCode && shortCode != null}
                helperText={shortCodeError}
              />
            </Grid>
            <Grid className={'form-label'} item md={2} xl={2} xs={12}>
              <Typography variant={'subtitle1'}>Maximum privacy level</Typography>
            </Grid>
            <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
              <FormControl sx={{minWidth: '300px'}}>
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
            <Grid className={'form-label'} item md={2} xl={2} xs={12}>
              <Typography variant={'subtitle1'}>Minimum privacy level</Typography>
            </Grid>
            <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
              <FormControl sx={{minWidth: '300px'}}>
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
          </Grid>
          <Box sx={{ textAlign: 'right' }}>
            <Button
              variant={"contained"}
              disabled={loading || !name || !description || !selectedModule || !isValidShortCode}
              onClick={submitCreateDataset}>
                <span style={{ display: 'flex' }}>
              { loading ? <Loading size={20} style={{ marginRight: 10 }}/> : ''} { "Create Dataset" }</span>
            </Button>
          </Box>
        </FormControl>
        </div>
      </Scrollable>
  </div>)
}
