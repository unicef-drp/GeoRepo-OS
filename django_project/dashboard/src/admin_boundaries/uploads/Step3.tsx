import React, {useEffect, useState, useRef} from "react";
import {
  Button,
  Grid,
  Select,
  MenuItem,
  SelectChangeEvent,
  Alert,
  AlertTitle,
  Typography,
  FormControl,
  InputLabel,
  Box,
  Checkbox,
  ListItemText,
  ListItemIcon,
  ListItem,
  Tooltip,
  Link} from "@mui/material";
import FormControlLabel from '@mui/material/FormControlLabel';
import ListSubheader from '@mui/material/ListSubheader';
import axios from "axios";
import '../../styles/Step3.scss';
import {postData} from "../../utils/Requests";
import {useAppDispatch} from "../../app/hooks";
import {useNavigate, useSearchParams} from "react-router-dom";
import {setPollInterval, FETCH_INTERVAL_JOB} from "../../reducers/notificationPoll";
import InfoIcon from '@mui/icons-material/Info';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import Step3RematchCountryList from "./Step3RematchCountry";
import Loading from "../../components/Loading";
import Scrollable from "../../components/Scrollable";
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import CancelIcon from '@mui/icons-material/Cancel';
import TextField from '@mui/material/TextField';
import { WizardStepInterface } from "../../models/upload";
import { VariableSizeList as List, ListChildComponentProps } from 'react-window';
import ResizeTableEvent from "../../components/ResizeTableEvent"

interface AdminLevelName {
  [key: string]: string
}

interface CountryItem {
  id: string,
  country: string,
  layer0_id: string,
  max_level: string,
  country_entity_id?: number,
  layer0_file?: string,
  revision?: number,
  last_update?: string,
  updated_by?: string,
  upload_id?: number,
  has_rematched?: boolean,
  ucode?: string,
  max_level_in_layer?: string,
  is_available?: boolean,
  total_rematched_count?: number,
  total_level1_children?: number,
  admin_level_names?: AdminLevelName
}

export default function Step3(props: WizardStepInterface) {
  const [datasetData, setDatasetData] = useState<CountryItem[]>([])
  const [isFetchingData, setIsFetchingData] = useState<boolean>(true)
  const [isLevel0Upload, setIsLevel0Upload] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(true)
  const [selectedEntities, setSelectedEntities] = useState<string[]>([])
  const [availableLevels, setAvailableLevels] = useState<number[]>([])
  const [alertMessage, setAlertMessage] = useState('')
  const [disableBackButton, setDisableBackButton] = useState<boolean>(false)
  const [fetchTrigger, setFetchTrigger] = useState<Date>(new Date())
  const [openAdminLevel1Modal, setOpenAdminLevel1Modal] = useState<boolean>(false)
  const [selectedUpload, setSelectedUpload] = useState<CountryItem>(null)
  const [selectedUploadCountry, setSelectedUploadCountry] = useState<string>('')
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const [editableKey, setEditableKey] = useState('')
  const listContainerRef = useRef(null)
  const [listViewHeight, setListViewHeight] = useState(0)
  const [isCheckAll, setCheckAll] = useState(false)
  const [progress, setProgress] = useState('')
  const listRef = useRef({} as any);
  const rowHeights = useRef({} as any);

  const fetchEntityList = () => {
    axios.get((window as any).datasetEntityList + `?session=${props.uploadSession}`).then(
      response => {
        setLoading(false)
        
        if (response.data['auto_matched_parent_ready']) {
          setIsFetchingData(false)
          setIsLevel0Upload(response.data['is_level_0_upload'])
          setDatasetData(response.data['results'] as CountryItem[])
          setAvailableLevels(response.data['available_levels'])
          let _selected_entities = []
          for (let data of response.data['results']) {
            if (data['is_selected'] && data['is_available'])
              _selected_entities.push(data['id'])
          }
          if (_selected_entities.length === response.data['results'].length) {
            setCheckAll(true)
          } else {
            setSelectedEntities(_selected_entities)
          }
          setFetchTrigger(null)
          setProgress('')
          if (props.onCheckProgress) {
            props.onCheckProgress()
          }
        } else {
          setProgress(response.data['progress'])
          // trigger to fetch notification frequently
          dispatch(setPollInterval(FETCH_INTERVAL_JOB))
          // trigger another call
          setFetchTrigger(new Date())
        }
      },
      error => {
        setLoading(false)
        console.error(error)
      }
    )
  }

  useEffect(() => {
    if (fetchTrigger !== null) {
      const interval = setTimeout(() => {
        fetchEntityList()
      }, 2000);
      return () => clearTimeout(interval);
    }
  }, [fetchTrigger])

  useEffect(() => {
    if (isCheckAll) {
      setSelectedEntities(datasetData.map((item) => item.id))
    } else {
      setSelectedEntities([])
    }
  }, [isCheckAll])

  const selectionChanged = (id: any, is_checked: boolean) => {
    let _selected_entities = [...selectedEntities]
    if (!is_checked) {
      let existing = _selected_entities.indexOf(id)
      if (existing !== -1) {
        _selected_entities.splice(existing, 1)
      }
    } else {
      _selected_entities.push(id)
    }
    
    setSelectedEntities(_selected_entities)
  }

  const validateButtonClicked = () => {
    setLoading(true)
    setAlertMessage('')
    let entities = selectedEntities.reduce((acc:any, current: string) => {
      acc.push(datasetData.find((entity: any) => entity.id == current))
      return acc
    }, [])

    postData(
      (window as any).validateUploadSession,
      {
        'upload_session': props.uploadSession,
        'entities': entities
      }).then(response => {
        setAlertMessage('')
        if (response.status === 200) {
          // trigger to fetch notification frequently
          dispatch(setPollInterval(FETCH_INTERVAL_JOB))
          props.onClickNext()
        }
      }).catch(
        error => {
          setLoading(false)
          if (error.response && error.response.data && error.response.data.length) {
            setAlertMessage(error.response.data.join('\n'))
          } else if (error.response && error.response.data && error.response.data['detail']) {
            setAlertMessage(error.response.data['detail'])
          } else {
            setAlertMessage('')
            alert('Error validating the data, please try again later')
          }
        })
  }

  const maxLevelSelectionChanged = (idx: any, selectedLevel: any) => {
      let new_data = [...datasetData]
      let item = {
        ...new_data[idx],
        'max_level': selectedLevel
      }
      new_data[idx] = item
      setDatasetData(new_data)
  }

  const selectCountryToView = (value: CountryItem) => {
    if (openAdminLevel1Modal && selectedUpload?.upload_id === value.upload_id) {
      // hide
      setSelectedUpload(null)
      setSelectedUploadCountry('')
      setOpenAdminLevel1Modal(false)
      return;
    }
    let name = `${value.country} - ${value.ucode?value.ucode:value.layer0_id}`
    setSelectedUpload(value)
    setSelectedUploadCountry(name)
    setOpenAdminLevel1Modal(true)
  }

  const secondaryAction = (rowIndex: number, rowData: CountryItem) => {
    return (
      <Box sx={{ minWidth: 120 }}>
        <FormControl fullWidth disabled={props.isReadOnly || !rowData.is_available}>
          <InputLabel id="max-level-select-label">Max Level</InputLabel>
          <Select
            labelId="max-level-select-label"
            id="max-level-select"
            value={rowData.max_level}
            label="Max Level"
            onChange={(event: SelectChangeEvent) => {
              maxLevelSelectionChanged(rowIndex, event.target.value)
            }}
          >
            {availableLevels.map((level: number) => {
              return rowData.max_level_in_layer=='' || level <= parseInt(rowData.max_level_in_layer) ? (
                <MenuItem
                  value={level}
                  key={level}>{level}
                </MenuItem>
              ) : null 
              })}
          </Select>
        </FormControl>
      </Box>
    );
  }

  const getItemTitle = (value: CountryItem) => {
    let rematched_txt = (value.has_rematched ? `${value.total_rematched_count}` : '0') +
        ' rematched' +
        (value.total_rematched_count > 1 ? ' entities': ' entity')
    return (
      <div style={{display:'flex', alignItems:'center' }}>
        <span>
          {`${value.country}` + (value.revision ? ` - Revision ${value.revision}`: ' (NEW)')}
        </span>
        {value.has_rematched && (
          <Tooltip title={`This country has ${rematched_txt} in admin level 1`}>
            <InfoIcon fontSize="small" color="warning" sx={{ ml: '10px' }} />
          </Tooltip>
        )}
        {!props.isReadOnly && !value.is_available && (
          <Tooltip title={`This country has upload being reviewed`}>
            <WarningAmberIcon fontSize="small" color="warning" sx={{ ml: '10px' }} />
          </Tooltip>
        )}
      </div>
    )
  }

  const getItemDescription = (value: CountryItem) => {
    
    return (
      <React.Fragment>
        <Grid container flexDirection='column' className="ListItemSecondary">
          <Grid item>
            <Typography
              sx={{ display: 'inline' }}
              component="span"
              variant="body2"
              color="text.primary"
            >
              {(value.country_entity_id && value.ucode ? `UCode: ${value.ucode}`:`Default Code: ${value.layer0_id}`) }
            </Typography>
            { value.country_entity_id && value.last_update && ` — Last update on ${new Date(value.last_update).toDateString()} by ${value.updated_by}`}
            { value.country_entity_id === null && ` — ${value.layer0_file}`}
          </Grid>
          <Grid item>
            <Typography
                sx={{ display: 'inline' }}
                component="span"
                variant="body2"
                color="text.primary"
              >
                {`Total admin level 1: ${value.total_level1_children} entities `}
            </Typography>
            <Link href="#" underline="hover" onClick={() => selectCountryToView(value)}>
              { openAdminLevel1Modal && selectedUpload && selectedUpload.upload_id === value.upload_id ? 'Hide': 'View' }
            </Link>
          </Grid>
        </Grid>
      </React.Fragment>
    )
  }

  const adminLevelNamesOnKeyPress = (e: any, idx: number, value: CountryItem, level: string) => {
    if(e.keyCode == 13){
        e.preventDefault()
        let _data = datasetData.map((countryItem, index) => {
          if (index === idx) {
            let _level_names = {...countryItem.admin_level_names}
            _level_names[level] = e.target.value
            countryItem.admin_level_names = _level_names
          }
          return countryItem
        })
        setDatasetData(_data)
        setEditableKey('')
    } else if (e.keyCode == 27) {
        e.preventDefault()
        setEditableKey('')
    }
}

  const adminLevelNames = (idx: number, value: CountryItem) => {
    let _filtered = Object.keys(value.admin_level_names).filter(val => parseInt(val) <= parseInt(value.max_level))
    if (!isLevel0Upload) {
      _filtered = _filtered.filter(val => parseInt(val) > 0)
    }
    return (
      <Grid container flexDirection={'row'} spacing={4} sx={{overflowX:'auto'}} flexWrap={'nowrap'}>
      {_filtered.map((key: string) => {
        const _editable_key = `${idx}-${key}`
        return (
          <Grid item key={`Level-${key}`}>
            <Grid container flexDirection={'column'} >
              <Grid item>
                {`Level ${key}`}
              </Grid>
              <Grid item sx={{height: '45px'}}>
                <Grid container flexDirection={'row'} alignItems={'center'} sx={{height:'100%'}} flexWrap={'nowrap'}>
                  <Grid item>
                    { editableKey===_editable_key ? (
                      <TextField
                        label=""
                        id="standard-size-small"
                        defaultValue={value.admin_level_names[key]}
                        size="small"
                        variant="standard"
                        onKeyDown={(e: any) => adminLevelNamesOnKeyPress(e, idx, value, key)}
                        autoFocus
                    />
                    ) : `${value.admin_level_names[key]}`}
                  </Grid>
                  <Grid item>
                    { editableKey===_editable_key ? (
                          <IconButton aria-label="cancel" title='cancel' disabled={props.isReadOnly} onClick={() => setEditableKey('')}>
                              <CancelIcon fontSize='small' />
                          </IconButton>
                      ) : (
                          <IconButton aria-label="edit" title='edit' disabled={props.isReadOnly} onClick={() => setEditableKey(_editable_key)}>
                              <EditIcon fontSize='small' />
                          </IconButton>
                    )}
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        )
      })
      }
      </Grid>
    )
  }

  const renderSelectedCountryItem = (value: CountryItem) => {
    const labelId = `checkbox-list-label-${value.layer0_id}`;
    return (
      <ListItem key={value.id} component="div" disablePadding>
        <Grid container flexDirection={'row'} alignItems={'center'} flexWrap={'nowrap'}>
          <Grid item>
            <ListItemIcon>
              <Checkbox
                edge="start"
                checked={selectedEntities.indexOf(value.id) !== -1}
                tabIndex={-1}
                disableRipple
                inputProps={{ "aria-labelledby": labelId }}
                onChange={(event: any) =>  selectionChanged(value.id, event.target.checked)}
                disabled={true}
              />
            </ListItemIcon>
          </Grid>
          <Grid item flexDirection={'row'} flex={2}>
            <ListItemText id={labelId} primary={getItemTitle(value)}
              secondary={getItemDescription(value)} disableTypography sx={{ flexGrow: 0, paddingRight: '20px' }} />
          </Grid>
          <Grid item>
            
          </Grid>
          <Grid item flexDirection={'row'} flex={3} sx={{paddingLeft: '30px', overflowX: 'auto'}}>
            <Grid container>
              
            </Grid>
          </Grid>
        </Grid>
      </ListItem>
    )
  }

  const renderRow = (props_list: ListChildComponentProps) => {
    const { index, style } = props_list;
    const value = datasetData[index];
    const labelId = `checkbox-list-label-${value.layer0_id}`;
    const rowRef = useRef({} as any);

    useEffect(() => {
      if (rowRef.current) {
        // set dynamic row height based on
        // https://github.com/bvaughn/react-window/issues/582
        setRowHeight(index, rowRef.current.clientHeight);
      }
      // eslint-disable-next-line
    }, [rowRef]);

    return (
      <ListItem style={style} key={value.id} component="div" disablePadding>
        <Grid ref={rowRef} container flexDirection={'row'} alignItems={'center'} flexWrap={'nowrap'}>
          <Grid item>
            <ListItemIcon>
              <Checkbox
                edge="start"
                checked={selectedEntities.indexOf(value.id) !== -1}
                tabIndex={-1}
                disableRipple
                inputProps={{ "aria-labelledby": labelId }}
                onChange={(event: any) =>  selectionChanged(value.id, event.target.checked)}
                disabled={props.isReadOnly || !value.is_available}
              />
            </ListItemIcon>
          </Grid>
          <Grid item flexDirection={'row'} flex={2}>
            <ListItemText id={labelId} primary={getItemTitle(value)}
              secondary={getItemDescription(value)} disableTypography sx={{ flexGrow: 0, paddingRight: '20px' }} />
          </Grid>
          <Grid item>
            { secondaryAction(index, value) }
          </Grid>
          <Grid item flexDirection={'row'} flex={3} sx={{paddingLeft: '30px', overflowX: 'auto'}}>
            <Grid container>
              { adminLevelNames(index, value) }
            </Grid>
          </Grid>
        </Grid>
      </ListItem>
    )
  }

  const getRowHeight = (index: any) => {
    return rowHeights.current[index] + 4 || 82;
  }

  const setRowHeight = (index: any, size: any) => {
    listRef.current.resetAfterIndex(0);
    rowHeights.current = { ...rowHeights.current, [index]: size };
  }

  return (
    <Scrollable>
    <Grid container className="Step3Container" flexDirection={'column'}>
      { alertMessage ?
          <Alert style={{ width: '750px', textAlign: 'left' }} severity={'error'}>
            <AlertTitle>Error</AlertTitle>
            <p className="display-linebreak">
              { alertMessage }
            </p>
          </Alert> : null }
      {!loading && <ResizeTableEvent containerRef={listContainerRef} onBeforeResize={() => setListViewHeight(0)}
                onResize={(clientHeight:number) => {
                  setListViewHeight(clientHeight - 100)
                }} />}
      
      <Grid item style={{ width: '100%' }}>
        <h3 style={{ textAlign: 'left' }}>Import Data</h3>
      </Grid>
      <Grid item flexDirection={'column'} ref={listContainerRef} flex={1} style={{ width: '100%' }} className="Step3Content">
      {
        isFetchingData ? 
          <div style={{ width: '100%' }}>
            <Grid container flexDirection={'column'} spacing={1}>
              <Grid item>
                <Loading/>
              </Grid>
              <Grid item>
                { progress ? progress : 'Retrieving data...' }                
              </Grid>
            </Grid>
          </div> : 
          <div style={{ width: '100%' }}>
            {
              datasetData.length > 0 && !openAdminLevel1Modal ?
                <div>
                  <ListSubheader>
                    <Grid container flexDirection={'row'}>
                      <Grid item>
                        <FormControlLabel control={
                          <Checkbox
                            edge="start"
                            checked={isCheckAll}
                            disableRipple
                            onChange={(event: any) =>  setCheckAll(event.target.checked)}
                            disabled={props.isReadOnly}
                            indeterminate={selectedEntities.length !== datasetData.length && selectedEntities.length !== 0}
                          />
                        }
                        label={`Select All (${selectedEntities.length}/${datasetData.length})`} sx={{color:'#000'}} />
                      </Grid>
                    </Grid>
                  </ListSubheader>
                  <div style={{ padding: '0 20px'}}>
                    <List
                      height={listViewHeight}
                      width={'100%'}
                      itemSize={getRowHeight}
                      itemCount={datasetData.length}
                      overscanCount={5}
                      ref={listRef}
                    >
                      {renderRow}
                    </List>
                  </div>
                </div> : null
            }
        </div>
      }
      {
        openAdminLevel1Modal && (
          <Grid container flexDirection={'column'}>
            <Grid item sx={{maxHeight: '80px'}}>
                {renderSelectedCountryItem(selectedUpload)}
            </Grid>
            <Grid item >
              <h4 style={{textAlign:'start', marginTop: '10px', marginBottom: '10px'}}>Admin Level 1 in { `${selectedUploadCountry}`}</h4>
              <Step3RematchCountryList handleOnBack={() => setOpenAdminLevel1Modal(false)}
                    entityUploadId={selectedUpload?.upload_id} />
            </Grid>
          </Grid>
        )
      }
      </Grid>
      <Grid item className="button-container" style={{marginLeft:0, width: '100%'}}>
        <Grid container direction='row' justifyContent='space-between'>
          <Grid item>
            <Button disabled={disableBackButton} onClick={() => props.onBackClicked()} variant="outlined">
              Back
            </Button>
          </Grid>
          <Grid item>
            { props.canResetProgress && !loading && (
              <Button onClick={props.onResetProgress} color={'warning'} variant="outlined" sx={{marginRight: '10px'}}>
                Update Selection
              </Button>
            )}
            {
              datasetData.length > 0 ?
                <Button variant="contained"
                        disabled={loading || (selectedEntities.length == 0)}
                        onClick={validateButtonClicked}
                >
                  { props.isReadOnly? 'Next': 'Validate'}
                </Button> : null
            }
          </Grid>
        </Grid>
      </Grid>
    </Grid>
    </Scrollable>
  )
}
