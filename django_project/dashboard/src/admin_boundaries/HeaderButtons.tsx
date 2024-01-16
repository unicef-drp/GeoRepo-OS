
import React, {useState, useEffect} from "react";
import axios from "axios";
import {useNavigate} from "react-router-dom";
import { Box, Button, Menu, MenuItem } from "@mui/material";
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import {HeaderButtonsInterface, UploadDataButton} from "../components/HeaderButtons";
import { BatchEntityEditInterface } from "../models/upload";


const LOAD_BATCH_ENTITY_EDIT_URL = '/api/batch-entity-edit/'

const BatchEditButton = (props: any) => {
  const {dataset} = props
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const menuAsOpen = Boolean(anchorEl)
  const navigate = useNavigate()
  const [ongoingBatchEdit, setOngoingBatchEdit] = useState<BatchEntityEditInterface>(null)
  
  const fetchOngoingBatchEdit = () => {
    axios.get(LOAD_BATCH_ENTITY_EDIT_URL + `?dataset_id=${dataset.id}`).then(
      response => {
        if (response.data) {
            let _data: BatchEntityEditInterface = response.data as BatchEntityEditInterface
            setOngoingBatchEdit(_data)
        }
      }, error => {
        console.log(error)
    })
  }

  useEffect(() => {
    if (dataset && dataset.id) {
      fetchOngoingBatchEdit()
    }
  }, [dataset])

  const createNewBatchEdit = () => {
    axios.put(LOAD_BATCH_ENTITY_EDIT_URL + `?dataset_id=${dataset.id}`).then(
        response => {
            let _data: BatchEntityEditInterface = response.data as BatchEntityEditInterface
            let _navigate_to = `/admin_boundaries/edit_entity/wizard?session=${_data.id}&step=0&dataset=${dataset.id}`
            navigate(_navigate_to)
        }, error => {
            console.log(error)
    })
  }

  const goToPendingBatchEdit = () => {
    let _navigate_to = `/admin_boundaries/edit_entity/wizard?session=${ongoingBatchEdit.id}&step=${ongoingBatchEdit.step}&dataset=${dataset.id}`
    navigate(_navigate_to)
  }

  return (
    <Box>
      <Button
          id='batch-edit-button'
          className={'ThemeButton MuiButton-secondary DatasetBatchEditButton'}
          onClick={(event: React.MouseEvent<HTMLButtonElement>) => setAnchorEl(event.currentTarget)}
          aria-controls={menuAsOpen ? 'batch-edit-menu' : undefined}
          aria-haspopup="true"
          aria-expanded={menuAsOpen ? 'true' : undefined}
          disableElevation
          endIcon={<KeyboardArrowDownIcon />}
      >
          Batch Edit
      </Button>
      <Menu
          id="batch-edit-menu"
          anchorEl={anchorEl}
          open={menuAsOpen}
          onClose={() => setAnchorEl(null)}
          MenuListProps={{
              'aria-labelledby': 'batch-edit-button',
          }}
      >
          { ongoingBatchEdit === null ? <MenuItem onClick={createNewBatchEdit}>Create</MenuItem> : null }
          { ongoingBatchEdit !== null ? <MenuItem onClick={goToPendingBatchEdit}>Pending Batch Edit</MenuItem> : null }
          <MenuItem onClick={() => {}}>View History</MenuItem>
      </Menu>
    </Box>
  )
}

export const UploadDataAdminBoundaries = () => {
  return <UploadDataButton next={'/admin_boundaries/upload_wizard'} moreActions={BatchEditButton} />
}


export const headerButtons: HeaderButtonsInterface[] = [{
  path: '/dataset_entities',
  element: <UploadDataAdminBoundaries/>
}]
