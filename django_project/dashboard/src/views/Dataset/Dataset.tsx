import React, {useEffect, useState} from 'react';
import List, {ActionDataInterface, applyFilterDialogFooter} from "../../components/List";
import {useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import DeleteIcon from "@mui/icons-material/Delete";
import Button from '@mui/material/Button';
import {useAppDispatch} from "../../app/hooks";
import {setModule} from "../../reducers/module";
import {modules} from "../../modules";
import {postData} from "../../utils/Requests";
import Loading from "../../components/Loading";
import AlertDialog from '../../components/AlertDialog'
import Dataset from '../../models/dataset';
import {ThemeButton} from "../../components/Elements/Buttons";
import TaskStatus from '../../components/TaskStatus';

const DELETE_DATASET_URL = '/api/delete-dataset'

const COLUMNS = [
  'id',
  'dataset',
  'created_by',
  'type',
  'date',
  'sync_status',
  'permissions',
  'is_empty',
  'is_active'
]

export default function Dataset() {
  const pageName = 'Dataset'
  const datasetUrlList = '/api/dataset-group/list/'
  const [searchParams, setSearchParams] = useSearchParams()
  const [dataset, setDataset] = useState<Dataset[]>([])
  const [selectedDataset, setSelectedDataset] = useState<Dataset>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [confirmationOpen, setConfirmationOpen] = useState<boolean>(false)
  const [confirmationText, setConfirmationText] = useState<string>('')
  const [deleteButtonDisabled, setDeleteButtonDisabled] = useState<boolean>(false)
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const customColumnOptions = {
    'is_active': {
        filter: true,
        sort: true,
        display: true,
        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          return value ? 'Active' : 'Deprecated'
        }
    },
    'permissions': {
      filter: false,
      display: false,
    },
    'is_empty': {
      filter: false,
      display: false,
    },
    'id': {
      filter: false,
      display: false,
    },
    'dataset': {
      filter: false,
      'customBodyRender': (value: any, tableMeta: any, updateValue: any) => {
          let rowData = tableMeta.rowData
          const handleClick = (e: any) => {
              e.preventDefault()
              let moduleName = toLower(rowData[3]).replace(' ', '_')
              const datasetId = rowData[0]
              if (!moduleName) {
                moduleName = modules[0]
              }
              dispatch(setModule(moduleName))
              navigate(`/${moduleName}/dataset_entities?id=${datasetId}`)
          };
          return (
              <a href='#' onClick={handleClick}>{`${rowData[1]}`}</a>
          )
      },
    },
    'sync_status': {
        filter: true,
        sort: true,
        display: true,
        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          const onClick = (e: any) => {
            e.stopPropagation();
            navigate(`/admin_boundaries/dataset_entities?id=${tableMeta.rowData[0]}&tab=8`)
          }
          if (value != 'Synced') {
            return (
              <ThemeButton
                icon={null}
                title={'Out of Sync'}
                variant={'secondary'}
                onClick={onClick}
              />
            )
          }
          return 'Synced'
        }
    }
  }
  const [deleteTaskId, setDeleteTaskId] = useState('')
  
  const customColumnHeaderRender = {
    'is_active': (columnMeta: any, handleToggleColumn: Function) => {
        return <span>Status</span>
    }
  }

  const fetchDataset = () => {
    setLoading(true)
    axios.get(datasetUrlList).then(
      response => {
        setLoading(false)
        setDataset(response.data.map((d: any)=>{
          let keys = Object.keys(d)
          for (const key of keys) {
            if (!(COLUMNS.includes(key))) {
              delete d[key]
            }
          }
          return d
        }))
      }
    )
  }

  useEffect(() => {
    fetchDataset()
  }, [searchParams])

  const actionDeleteButton: ActionDataInterface = {
    field: '',
    name: 'Delete',
    getName: (data: any) => {
        if (!data.permissions.includes('Own')) {
            return 'You are not owner of this dataset'
        } else if (!data.is_empty) {
          return 'Cannot remove non-empty dataset'
        }
        return 'Delete'
    },
    color: 'error',
    icon: <DeleteIcon />,
    isDisabled: (data: any) => {
      return !data.permissions.includes('Own') || !data.is_empty
    },
    onClick: (data: any) => {
      setSelectedDataset(data)
      setConfirmationText(
        `Are you sure you want to delete ${data.dataset}?`)
      setConfirmationOpen(true)
    }
  }

  const handleDeleteClick = () => {
    setDeleteButtonDisabled(true)
    postData(
      `${DELETE_DATASET_URL}/${selectedDataset.id}`, {}
    ).then(
      response => {
        setDeleteButtonDisabled(false)
        setConfirmationOpen(false)
        setDeleteTaskId(response.data['task_id'])
      }
    ).catch(error => {
      setDeleteButtonDisabled(false)
      alert('Error deleting dataset')
    })
  }

  const handleClose = () => {
    setConfirmationOpen(false)
  }

  return (
    <div className="AdminContentMain main-data-list">
      <AlertDialog open={confirmationOpen} alertClosed={handleClose}
          alertConfirmed={handleDeleteClick}
          alertLoading={deleteButtonDisabled}
          alertDialogTitle={'Delete dataset'}
          alertDialogDescription={confirmationText}
          confirmButtonText='Delete'
          confirmButtonProps={{color: 'error', autoFocus: true}}
      />
      <TaskStatus dialogTitle='Deleting dataset' errorMessage='Error! There is unexpected error while deleting dataset, please contact Administrator.'
        successMessage='Dataset has been deleted successfully!' task_id={deleteTaskId} onCompleted={() => {
          setDeleteTaskId('')
          fetchDataset()
        }}
        />
      {!loading ?
        <List
          pageName={pageName}
          listUrl={''}
          initData={dataset}
          selectionChanged={null}
          onRowClick={null}
          actionData={[actionDeleteButton]}
          excludedColumns={['permissions', 'is_empty']}
          customOptions={customColumnOptions}
          customColumnHeaderRender={customColumnHeaderRender}
          options={{
            'confirmFilters': true,
            'customFilterDialogFooter': applyFilterDialogFooter
          }}
        /> : <Loading/>
      }
    </div>
  )
}
