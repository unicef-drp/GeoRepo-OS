import React, {useState, useEffect} from 'react';
import List from "../components/List";
import {useSearchParams} from "react-router-dom";
import {Box, Tab, Tabs, Button, Stack} from "@mui/material";
import {a11yProps} from '../components/TabPanel';
import "../styles/Dataset.scss";
import {ExpandedRowInterface} from "../components/Table";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import {fetchingData} from "../utils/Requests";
import axios from "axios";
import {useAppDispatch, useAppSelector} from "../app/hooks";
import {updateMenu, changeCurrentDataset} from "../reducers/breadcrumbMenu";
import {currentModule, setModule} from "../reducers/module";
import toLower from "lodash/toLower";
import Loading from "../components/Loading";

function DatasetExpandedRow(props: ExpandedRowInterface) {
    const [loading, setLoading] = useState<boolean>(true)
    const [revisions, setRevisions] = useState<any[]>([])

    useEffect(() => {
        const url = (
          (window as any).entityRevisions + `?id=${props.rowData[0]}`
        )
        fetchingData(url, {}, {}).then(
          (data) => {
              setLoading(false)
              if (data.responseStatus == 'success') {
                  setRevisions(data.responseData)
              } else {
                  console.error('Error fetching data')
              }
              return
          }
        )
        setTimeout(() => {
            setLoading(false)
        }, 500)
    }, [])

    return (
      loading ?
        <TableRow style={{ height: '50px' }}><Loading style={{ padding: 10 }} size={20}/></TableRow> :
         revisions.map((revision, index) => (
              <TableRow key={index} style={{ background: '#f4f4f4' }}>
                  <TableCell></TableCell>
                  <TableCell>{props.rowData[1]}</TableCell>
                  <TableCell>{new Date(revision.date).toDateString()}</TableCell>
                  <TableCell>{revision.uploader}</TableCell>
                  <TableCell>{revision.status}</TableCell>
                  <TableCell>{revision.revision}</TableCell>
                  <TableCell>
                    <Button variant={'contained'}>View</Button></TableCell>
              </TableRow>
          ))
    )
}

interface DatasetEntityListInterface {
  body?: null | JSX.Element
}

export default function DatasetEntityList(props: DatasetEntityListInterface) {
    const dispatch = useAppDispatch();
    const pageName = 'Dataset'
    const [loading, setLoading] = useState<boolean>(true)
    const [datasetEntityData, setDatasetEntityData] = useState<any[]>([])
    const [searchParams, setSearchParams] = useSearchParams()
    const [tabSelected, setTabSelected] = useState(0)

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabSelected(newValue);
    };

    useEffect(() => {
      dispatch(changeCurrentDataset(searchParams.get('id')))
      axios.get(`/api/dataset-detail/${searchParams.get("id")}`).then(
        response => {
          dispatch(updateMenu({
            id: 'dataset_entities',
            name: response.data.dataset,
            link: `/dataset?${searchParams.toString()}`
          }))
          dispatch(setModule(toLower(response.data.type.replace(' ', '_'))))
        }
      )
      const url = `/api/dataset-entity/list?id=${searchParams.get("id")}`
      axios.get(url).then(
        response => {
          setLoading(false)
          if (response.data) {
            const responseData = response.data.map((_data:any) => {
              _data._ = '';
              return _data
            })
            setDatasetEntityData(responseData)
          }
        }
      )
    }, [searchParams])

  return (
      !loading ?
        <div className="list-container">
          {
            props.body ? props.body :
              <Stack>
                <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                  <Tabs value={tabSelected} onChange={handleChange} aria-label="basic tabs example">
                    <Tab label="Countries" {...a11yProps(0)}/>
                    <Tab disabled={true} label="Views" {...a11yProps(1)}/>
                  </Tabs>
                </Box>
                <List
                  pageName={pageName}
                  listUrl={''}
                  initData={datasetEntityData}
                  selectionChanged={null}
                  expandableRow={DatasetExpandedRow}
                  />
            </Stack>
          }
        </div>: <div className="list-container"><Loading/></div>
    )
}
