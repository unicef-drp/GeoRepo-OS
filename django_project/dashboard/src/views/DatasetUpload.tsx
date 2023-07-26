import React, {Fragment, useEffect, useState} from "react";
import axios from "axios";
import {useSearchParams} from "react-router-dom";
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import '../styles/DatasetUpload.scss';
import {FormControl, Grid, InputLabel, MenuItem, Select, Typography} from "@mui/material";
import {SaveButton} from "../components/Elements/Buttons";

const UPLOAD_SESSION_URL = '/api/upload-session/'

export default function DatasetUpload() {

  const [searchParams, setSearchParams] = useSearchParams()
  const [levels, setLevels] = useState([])
  const [dataset, setDataset] = useState('')
  const [status, setStatus] = useState('')

  const getDatasetUploadSession = (uploadSession: string) => {
    axios.get(UPLOAD_SESSION_URL + uploadSession).then(
      response => {
        setLevels(response.data.levels)
        setDataset(response.data.dataset)
        setStatus(new Date(response.data.modified_at).toLocaleString())
      }, error => {
        console.log(error)
      })
  }

  useEffect(() => {
    const uploadSession = searchParams.get('id')
    if (uploadSession) {
      getDatasetUploadSession(uploadSession)
    }
  }, [searchParams])

  return (
    <Fragment>
      <div className="AdminBaseInput">
        <Grid container>
          <Grid item xs={12} md={4}>
            <FormControl id="country-select-form">
              <InputLabel id="country-select-label">Dataset</InputLabel>
              <Select
                labelId="dataset-select-label"
                id="dataset-select"
                value={dataset}
                label="Dataset"
                onChange={null}
                disabled
              >
                {
                  dataset ? <MenuItem selected value={dataset}>{dataset}</MenuItem> : null
                }
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={8}>
            <Typography className={'dataset-upload-status'}>
              Last updated {status}
            </Typography>
          </Grid>
        </Grid>
      </div>
      <div className='AdminList'>
        <TableContainer component={Paper}>
          <Table sx={{ minWidth: 650 }} aria-label="simple table">
            <TableHead>
              <TableRow>
                <TableCell width={10}>Level</TableCell>
                <TableCell variant={"head"}>File name</TableCell>
                <TableCell>Feature Count</TableCell>
                <TableCell>Level Name</TableCell>
                <TableCell>Field Mapping</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {levels.map((row) => (
                <TableRow
                  key={row.file_name}
                  sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                >
                  <TableCell component="th" scope="row">
                    {row.level}
                  </TableCell>
                  <TableCell>{row.file_name}</TableCell>
                  <TableCell>-</TableCell>
                  <TableCell>{row.entity_type}</TableCell>
                  <TableCell>-</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        <div className="AdminFooter">
          <SaveButton variant="success" text={"Upload"}/>
        </div>
      </div>
    </Fragment>
  )
}
