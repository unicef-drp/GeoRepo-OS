
import React from "react";
import axios from "axios";
import {useNavigate} from "react-router-dom";
import { Box, Button } from "@mui/material";
import {HeaderButtonsInterface, UploadDataButton} from "../components/HeaderButtons";
import { BatchEntityEditInterface } from "../models/upload";


const LOAD_BATCH_ENTITY_EDIT_URL = '/api/batch-entity-edit/'

const BatchEditButton = (props: any) => {
  const {dataset} = props
  const navigate = useNavigate()

  const createNewBatchEdit = () => {
    axios.put(LOAD_BATCH_ENTITY_EDIT_URL + `?dataset_id=${dataset.id}`).then(
        response => {
            let _data: BatchEntityEditInterface = response.data as BatchEntityEditInterface
            goToBatchEdit(_data)
        }, error => {
            console.log(error)
            // check if has existing batch edit
            if (error.response) {
              if ('batch_edit' in error.response.data) {
                  let _batchEdit = error.response.data['batch_edit'] as BatchEntityEditInterface
                  goToBatchEdit(_batchEdit)
              } else if ('detail' in error.response.data) {
                alert(error.response.data['detail'])
              } else {
                alert('There is unexpected error when creating batch editor session, please try again later or contact administrator!')
              }
          } else {
            alert('There is unexpected error when creating batch editor session, please try again later or contact administrator!')
          }
    })
  }

  const goToBatchEdit = (ongoingBatchEdit: BatchEntityEditInterface) => {
    let _navigate_to = `/admin_boundaries/edit_entity/wizard?session=${ongoingBatchEdit.id}&step=${ongoingBatchEdit.step}&dataset=${dataset.id}`
    navigate(_navigate_to)
  }

  return (
    <Box>
      <Button
          id='batch-edit-button'
          disabled={dataset?.is_empty}
          className={'ThemeButton MuiButton-secondary DatasetBatchEditButton'}
          onClick={(event: React.MouseEvent<HTMLButtonElement>) => createNewBatchEdit()}
          disableElevation
      >
          Batch Editor
      </Button>
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
