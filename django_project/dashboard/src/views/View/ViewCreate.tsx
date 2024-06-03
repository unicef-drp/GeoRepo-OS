import React, {
  useEffect,
  useRef,
  useState,
  Suspense, useCallback
} from "react";
import {
  Box,
  Button,
  FormControl,
  FormControlLabel,
  Grid, List,
  ListItemText,
  MenuItem,
  Popover,
  Radio,
  RadioGroup,
  Select,
  SelectChangeEvent,
  TextField,
  Typography,
  Chip
} from "@mui/material";
import Autocomplete, { createFilterOptions } from '@mui/material/Autocomplete';
import axios from "axios";
import {useNavigate, useSearchParams} from "react-router-dom";
import {fetchData, postData} from "../../utils/Requests";
import {ViewListRoute} from "../routes";
import View, {isReadOnlyView} from "../../models/view";
import Loading from "../../components/Loading";
import {
  AutocompleteOption,
  SQLAutocomplete,
  SQLDialect
} from 'sql-autocomplete';
import '../../styles/ViewCreate.scss';
import ListItemButton from "@mui/material/ListItemButton";
import Scrollable from "../../components/Scrollable";

const TReactQuill = React.lazy(() => import("../../components/ReactQuill"));

const sqlAutocomplete = new SQLAutocomplete(
  SQLDialect.PLpgSQL,
);

const CREATE_VIEW_URL = '/api/create-new-view/'
const UPDATE_VIEW_URL = '/api/update-view/'
const DETAIL_VIEW_URL = '/api/view-detail'
const QUERY_CHECK_URL = '/api/query-view-check/'
const GET_TAG_LIST_URL = '/api/tag-list/'
const RESERVED_TAG_LIST = ['all_versions', 'latest', 'dataset', 'subset']

const stripHtml = (text: string) => {
  const regex = /(<([^>]+)>)/gi
  return text.replace(regex, "").replaceAll('&nbsp;', ' ')
}

export interface TempQueryCreateInterface {
  queryString: string,
  dataset: string,
  name: string,
  description: string,
  mode: string,
  queryCheckResult: string,
  tags?: string[],
  datasetUuid?: string
}

interface ViewCreateInterface {
  tempData: TempQueryCreateInterface,
  onQueryValidation: (isValid: boolean, query: string) => void,
  onPreviewClicked: (tempData: TempQueryCreateInterface) => void,
  onViewLoaded?: (view: View) => void
}

const filterTagList = createFilterOptions<string>();

export default function ViewCreate(props: ViewCreateInterface) {
  const inputRef = useRef()
  const inputContainerRef = useRef()
  const [loading, setLoading] = useState<boolean>(false)
  const [isReadOnly, setIsReadOnly] = useState<boolean>(true)
  const [name, setName] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [mode, setMode] = useState<string>('')
  const [datasets, setDatasets] = useState<any[]>([])
  const [dataset, setDataset] = useState<string>('')
  const [datasetUuid, setDatasetUuid] = useState<string>('')
  const [query, setQuery] = useState<string>(`<span class="keyword">SELECT * FROM geographicalentity WHERE </span>`)
  const [queryChanged, setQueryChanged] = useState<boolean>(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const [queryCheckResult, setQueryCheckResult] = useState<string>('')
  const [itemSelected, setItemSelected] = useState<number>(0)

  const [popoverOpen, setPopoverOpen] = useState<boolean>(false)
  const [options, setOptions] = useState<AutocompleteOption[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [tagList, setTagList] = useState<string[]>([])

  const navigate = useNavigate()
  const datasetUrlList = '/api/dataset-group/list/'
  const sqlColumnTables = '/api/columns-tables-list/'
  const isUpdating = !!searchParams.get('id')
  const [anchorPosition, setAnchorPosition] = useState<any>({
      top: 0,
      left: 0
  })
  const isAdminUser = (window as any).is_admin
  const [editView, setEditView] = useState<View>(null)

  useEffect(() => {
    if (datasets.length > 0 && props.tempData) {
      // if there is tmpQueryString, then it is from preview
      setQuery(`<span class="keyword">${props.tempData.queryString}</span>`)
      setName(props.tempData.name)
      setDescription(props.tempData.description)
      setDataset(props.tempData.dataset)
      setDatasetUuid(props.tempData.datasetUuid)
      setMode(props.tempData.mode)
      setQueryCheckResult(props.tempData.queryCheckResult)
      setTags(props.tempData.tags)
      setLoading(false)
      setIsReadOnly(false)
      setEditView(null)
    } else if (searchParams.get('id')) {
      fetchData(DETAIL_VIEW_URL + `/${searchParams.get('id')}`).then(
        response => {
          setLoading(false)
          const view:View = response.data
          setName(view.name)
          setDescription(view.description)
          setTags(view.tags)
          if (view.query_string) {
            setQueryCheckResult(`Total view data : ${view.total}`)
            if (view.query_string.includes('dataset_id')) {
              view.query_string = view.query_string.replace(/\sAND(.\w+)?.dataset_id[^\w.-]+[^\s]+/gi, '');
            }
            setQuery(`<span class="keyword">${view.query_string}</span>`)
          }
          setDataset(view.dataset)
          setDatasetUuid(view.dataset_uuid)
          setMode(view.mode)
          if (props.onViewLoaded) {
            props.onViewLoaded(view)
          }
          // set read only if does not have own permission
          let _isReadOnly = isReadOnlyView(view)
          setIsReadOnly(_isReadOnly)
          if (_isReadOnly && datasets.length === 0) {
            // add current dataset name
            datasets.push({
              id: parseInt(view.dataset),
              dataset: view.dataset_name
            })
          }
          setEditView(view)
        }
      ).catch((error) => {
          console.log(error)
          setLoading(false)
          if (error.response) {
              if (error.response.status == 403) {
                // TODO: use better way to handle 403
                navigate('/invalid_permission')
              }
          }
      })
    } else {
      // create
      setIsReadOnly(false)
      setEditView(null)
    }
  }, [datasets])

  useEffect(() => {
    let _query_params = 'create_view=true'
    if (searchParams.get('id')) {
      _query_params = 'edit_view=true'
    }
    axios.get(`${datasetUrlList}?${_query_params}`).then(
      response => {
        setDatasets(response.data)
      }
    )
    if (searchParams.get('id')) {
      setLoading(true)
    }
    axios.get(sqlColumnTables).then(
        response => {
          if (response.data) {
            sqlAutocomplete.setTableNames(response.data.tables)
            sqlAutocomplete.setColumnNames(response.data.columns)
          }
        }
    )
    axios.get(GET_TAG_LIST_URL).then(
      response => {
        if (response.data) {
          setTagList(response.data)
        }
      }
    )
  }, [searchParams])

  useEffect(() => {
    const queryWithoutHtml = query ? stripHtml(query) : ''
    props.onQueryValidation(false, queryWithoutHtml)
    if (query) {
      if (editView && editView.query_string === queryWithoutHtml) {
        setQueryCheckResult('Query Valid!')
        setQueryChanged(false)
        setPopoverOpen(false)
        return
      }
      setQueryCheckResult('')
      setQueryChanged(true)
      if (!queryWithoutHtml.at(-1) || queryWithoutHtml.at(-1) === " ") {
        return
      }
      const _options = sqlAutocomplete.autocomplete(queryWithoutHtml).slice(0, 10).filter(
          (__option: any) => __option.value !== null
      )
      setOptions(_options)
      if (_options.length > 0 && queryWithoutHtml !== "") {
        setItemSelected(1)
        setPopoverOpen(true)
      } else {
        setPopoverOpen(false)
      }
    } else {
        setPopoverOpen(false)
    }
  }, [query])

  const handleModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setMode((event.target as HTMLInputElement).value)
  }

  const handleDatasetChange = (event: SelectChangeEvent) => {
    setDataset(event.target.value)
    // find dataset uuid
    let _dataset = datasets.find(e => e.id == event.target.value)
    if (_dataset) {
      setDatasetUuid(_dataset.uuid)
    }
  }

  const updateView = () => {
    const payload = {
      name: name,
      description: description,
      dataset_id: dataset,
      mode: mode,
      query_string: stripHtml(query),
      tags: tags
    }
    setLoading(true)
    postData(UPDATE_VIEW_URL + `${searchParams.get('id')}`, payload).then(
      response => {
        setLoading(false)
        navigate(ViewListRoute.path)
      }
    ).catch(error => {
      alert('Error updating view...')
      setLoading(false)
    })
  }

  const createView = () => {
    const payload = {
      name: name,
      description: description,
      dataset_id: dataset,
      mode: mode,
      query_string: stripHtml(query),
      tags: tags
    }
    setLoading(true)
    postData(CREATE_VIEW_URL, payload).then(
      response => {
        setLoading(false)
        navigate(ViewListRoute.path)
      }
    ).catch(error => {
      alert('Error creating view...')
      setLoading(false)
    })
  }

  const queryCheck = () => {
    setLoading(true)
    postData(QUERY_CHECK_URL, {
      'query_string': stripHtml(query),
      'dataset': dataset
    }).then(
      response => {
        setLoading(false)
        setQueryChanged(false)
        props.onQueryValidation(response.data.valid, stripHtml(query))
        if (response.data.valid) {
          setQueryCheckResult(`Total view data : ${response.data.total}`)
        } else {
          setQueryCheckResult('Invalid query')
        }
      }
    ).catch(
      error => {
        setLoading(false)
        setQueryCheckResult('Invalid query')
      }
    )
  }

  const updateQuery = (index: any = null) => {
    try {
      const editor: any = (inputRef.current as any).getEditor()
      const option = options[ index ? index : itemSelected - 1 ]
      let currentValue = stripHtml(query).split(' ').pop()
      if (currentValue.includes('.')) {
        currentValue = currentValue.split('.').pop()
      }
      setQuery(query.replace(`${currentValue}</`, `<span class="${option.optionType.toLowerCase()}">${option.value}&nbsp;</span></`))
      setTimeout(() => {
        editor.setSelection(editor.getSelection().index + currentValue.length + 30, 0)
      }, 100)
      setPopoverOpen(false)
    } catch (e) {
      console.log(e)
      return
    }
  }

  const handleQueryChange = useCallback((value: any) => {
    if (inputRef && inputRef.current) {
      const editor: any = (inputRef.current as any).getEditor()
      const container: any = (inputContainerRef.current as any)
      const containerBound = container.getBoundingClientRect()
      const sel: any = editor.getSelection()
      if (sel) {
        const bound: any = editor.getBounds(sel.index)
        setAnchorPosition({
          top: containerBound.top + bound.top,
          left: containerBound.left + bound.left
        })
      }
      if (value !== '<p><br></p>' && value.match(/<br>/g)) {
        if (!query.match(/<br>/g) || value.match(/<br>/g).length > query.match(/<br>/g).length) {
          return
        }
      }
    }
    if (value === '<p><br></p>') {
        setQuery('')
    } else {
        setQuery(value)
    }
  }, [])

  const handlePopoverClick = (e: any) => {
    setPopoverOpen(false)
    const editor: any = (inputRef.current as any).getEditor()
    editor.focus()
    setTimeout(() => {
      editor.setSelection(editor.getSelection().index + 12, 0)
    }, 100)
  }

  const handleKeyDown = (e: any) => {
    // arrow up/down button should select next/previous list element
    if (popoverOpen) {
      if (e.keyCode === 38 && itemSelected > 1) {
        e.preventDefault();
        setItemSelected(itemSelected - 1)
      } else if (e.keyCode === 40 && itemSelected < options.length) {
        e.preventDefault();
        setItemSelected(itemSelected + 1)
      } else if (e.keyCode === 13) {
        e.preventDefault();
        e.stopPropagation();
        updateQuery()
      } else {
        setPopoverOpen(false)
      }
    }
  }

  const handleListItemClick = (index: number) => {
    setItemSelected(index + 1)
    updateQuery(index)
  }

  const onPreviewClicked = () => {
    props.onPreviewClicked({
      name: name,
      dataset: dataset,
      description: description,
      mode: mode,
      queryCheckResult: queryCheckResult,
      queryString: stripHtml(query),
      tags: tags,
      datasetUuid: datasetUuid
    })
  }

  return (
    <Scrollable>
    <div className="FormContainer">
      <Popover
          id="size-popover"
          open={popoverOpen}
          anchorReference="anchorPosition"
          anchorPosition={anchorPosition}
          onClick={handlePopoverClick}
          onKeyDown={handleKeyDown}
          anchorOrigin={{
            vertical: 'top', horizontal: 'left',
          }}
          transformOrigin={{
            vertical: 'top', horizontal: 'left',
          }}
          disableAutoFocus
      >
        <Box sx={{width: '100%', maxWidth: 360, bgcolor: 'background.paper'}}>
          <List component="nav" dense>
              { options.map((option: any, index: number) => (
                  <ListItemButton onClick={(e) => handleListItemClick(index)}
                      disableRipple dense
                                  selected={itemSelected == index + 1}
                                  key={index}>
                      <ListItemText primary={option.value} secondary={option.optionType}/>
                  </ListItemButton>
              ))}
          </List>
        </Box>
      </Popover>
      <FormControl className="FormContent" disabled={isReadOnly}>
        <Grid container columnSpacing={2} rowSpacing={2}>
          <Grid className={'form-label'} item md={2} xl={2} xs={12}>
            <Typography variant={'subtitle1'}>Name</Typography>
          </Grid>
          <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
            <TextField
              disabled={loading || isReadOnly}
              id="view_name"
              hiddenLabel={true}
              type={"text"}
              onChange={val => setName(val.target.value)}
              value={name}
              sx={{ width: '100%' }}
            />
          </Grid>
          <Grid className={'form-label'} item md={2} xl={2} xs={12}>
            <Typography variant={'subtitle1'}>Description</Typography>
          </Grid>
          <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
            <TextField
              disabled={loading || isReadOnly}
              id="view_desc"
              hiddenLabel={true}
              type={"text"}
              onChange={val => setDescription(val.target.value)}
              value={description}
              sx={{ width: '100%' }}
            />
          </Grid>
          <Grid className={'form-label'} item md={2} xl={2} xs={12}>
            <Typography variant={'subtitle1'}>Select Dataset</Typography>
          </Grid>
          <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
            <Select sx={{ width: '80%', textAlign: 'left' }} disabled={datasets.length == 0 || loading || isReadOnly} onChange={handleDatasetChange} value={dataset}>
              { datasets.map((_dataset: any) => (
                <MenuItem key={_dataset.id} value={_dataset.id}>
                  {_dataset.dataset}
                </MenuItem>
              ))}
            </Select>
          </Grid>
          <Grid className={'form-label'} item md={2} xl={2} xs={12}>
            <Typography variant={'subtitle1'}>Mode</Typography>
          </Grid>
          <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
            <FormControl>
              <RadioGroup
                aria-labelledby="demo-controlled-radio-buttons-group"
                name="controlled-radio-buttons-group"
                value={mode}
                onChange={handleModeChange}
              >
                <FormControlLabel value="static" control={<Radio disabled={loading || isReadOnly} />} label="Static" />
                <FormControlLabel value="dynamic" control={<Radio disabled={loading || isReadOnly} />} label="Dynamic" />
              </RadioGroup>
            </FormControl>
          </Grid>
          <Grid className={'form-label'} item md={2} xl={2} xs={12}>
            <Typography variant={'subtitle1'}>Tags</Typography>
          </Grid>
          <Grid item md={10} xs={12} sx={{ display: 'flex' }}>
            <FormControl sx={{ width: '100%' }}>
              <Autocomplete
                multiple
                value={tags}
                onChange={(event, newValue) => {
                  let _items = [...newValue]
                  if (_items.length > 0) {
                    let _val:string = _items[_items.length - 1]
                    let _isExisting = tagList.some((option) => _val === option)
                    if (!isAdminUser && !_isExisting) {
                      // remove if it's not added by admin user
                      _items.splice(-1)
                    } else {
                      _items[_items.length - 1] = _val.replace('Add ', '').replace(/"/g, '')
                      if (RESERVED_TAG_LIST.indexOf(_items[_items.length - 1].toLowerCase()) !== -1) {
                        _items.splice(-1)
                      }
                    }
                  }
                  setTags(_items)
                }}
                renderTags={(tagValue, getTagProps) =>
                  tagValue.map((option, index) => (
                    <Chip
                      label={option}
                      {...getTagProps({ index })}
                      disabled={RESERVED_TAG_LIST.indexOf(option.toLowerCase()) !== -1}
                    />
                  ))
                }
                filterOptions={(options, params) => {
                  const filtered = filterTagList(options, params);

                  const { inputValue } = params;
                  // Suggest the creation of a new value
                  const isExisting = options.some((option) => inputValue === option);
                  if (inputValue !== '' && !isExisting && isAdminUser) {
                    filtered.push(`Add "${inputValue}"`);
                  }

                  return filtered;
                }}
                selectOnFocus
                clearOnBlur
                handleHomeEndKeys
                id="tag-autocomplete"
                options={tagList}
                getOptionLabel={(option) => {
                  return option;
                }}
                renderOption={(props, option) => <li {...props}>{option}</li>}
                sx={{ width: '100%' }}
                freeSolo
                renderInput={(params) => (
                  <TextField {...params} sx={{ width: '100%' }} />
                )}
                disabled={loading || isReadOnly}
              />
            </FormControl>
          </Grid>
          <Grid className={'form-label'} item md={2} xl={2} xs={12}>
            <Typography variant={'subtitle1'}>Query</Typography>
          </Grid>
          <Grid item md={9} xs={12} sx={{ display: 'flex', flexDirection: 'column' }}>
            <Suspense fallback={<Loading/>}>
              <TReactQuill
                quillRef={inputRef}
                formats={[]}
                modules={{
                    toolbar: [],
                }}
                value={query}
                quillContainerRef={inputContainerRef}
                onChange={handleQueryChange}
                onKeyDown={handleKeyDown}
                style={{minHeight: '100px'}}
                readOnly={isReadOnly} />
            </Suspense>
          </Grid>
          <Grid item md={1} xs={12}>
            <Button onClick={queryCheck} disabled={loading || isReadOnly} variant={'outlined'} color={queryChanged ? 'warning' : 'success'} style={{ width: '100%' }}>Check Query{queryChanged ? '*' : ''}</Button>
            {/*<Button disabled={loading} variant={'outlined'} color={'warning'} style={{ width: '100%', marginTop: 10}}>Help</Button>*/}
          </Grid>
          <Grid className={'form-label'} item md={2} xl={2} xs={12}>
          </Grid>
          <Grid item md={9} xs={12}>
            { queryCheckResult ? <div className={ 'check-result ' + (queryCheckResult.includes('Invalid') ? 'invalid': '') }> {queryCheckResult} </div> : null }
          </Grid>
        </Grid>
        <Box sx={{ textAlign: 'right' }}>
          <Grid container flexDirection={'row'} justifyContent={'space-between'}>
            <Grid item>
              <Button
                variant={"outlined"}
                color={"success"}
                disabled={!query || !name || !mode || !dataset || loading || queryChanged || queryCheckResult.includes('Invalid') || isReadOnly}
                onClick={onPreviewClicked}
              >
                Preview
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant={"contained"}
                color={"success"}
                disabled={!query || !name || !mode || !dataset || loading || queryChanged || queryCheckResult.includes('Invalid') || isReadOnly}
                onClick={isUpdating ? updateView : createView}
              >
                {loading ?
                  <span className="ButtonContent">
                    <Loading size={20}/> {isUpdating ? "Updating" : "Creating"} view</span>:
                  <span>{isUpdating ? "Update" : "Create"} view</span>
                }
              </Button>
            </Grid>
          </Grid>
        </Box>
      </FormControl>
    </div>
    </Scrollable>
  )
}
