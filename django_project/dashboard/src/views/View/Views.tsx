import React, {useEffect, useState} from 'react';
import {useNavigate, useSearchParams} from "react-router-dom";
import View from "../../models/view";
import List, {ActionDataInterface} from "../../components/List";
import Loading from "../../components/Loading";
import {fetchData, postData} from "../../utils/Requests";
import {ViewEditRoute} from "../routes";
import AlertDialog from '../../components/AlertDialog'
import {Button, Chip} from '@mui/material';
import Grid from '@mui/material/Grid';
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import MoreVertIcon from '@mui/icons-material/MoreVert';
import Popover from '@mui/material/Popover';
import Typography from '@mui/material/Typography';

const VIEW_LIST_URL = '/api/view-list/'
const DELETE_VIEW_URL = '/api/delete-view'

const copyToClipboard = (value: string) => {
  navigator.clipboard.writeText(value)
  alert('Link copied')
}

function ViewPopover(props: any) {
  if (props.view === null) {
    return null
  }
  return (
    <Grid container flexDirection={'column'} sx={{ p: 2 }}>
      <Grid item>
        <Typography sx={{ pb: 1 }}>Mode: {props.view.mode}</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{ pb: 1 }}>Is Default: {props.view.is_default}</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{ pb: 0 }}>UUID:</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{ pb: 1 }}>{props.view.uuid}</Typography>
      </Grid>
      <Grid item>
        <Typography sx={{ pb: 1 }}>Layer Tiles:</Typography>
      </Grid>
      <Grid item>
        <Button variant={'outlined'} onClick={() => copyToClipboard(props.view.layer_tiles)}>Copy Link</Button>
      </Grid>
    </Grid>
  )
}

export default function Views() {
  const [searchParams] = useSearchParams()
  const [views, setViews] = useState<View[]>([])
  const [selectedView, setSelectedView] = useState<View>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [confirmationOpen, setConfirmationOpen] = useState<boolean>(false)
  const [confirmationText, setConfirmationText] = useState<string>('')
  const [deleteButtonDisabled, setDeleteButtonDisabled] = useState<boolean>(false)
  const navigate = useNavigate()
  const [anchorEl, setAnchorEl] = React.useState<HTMLButtonElement | null>(null);

  const handleCloseMoreInfo = () => {
    setAnchorEl(null);
    setSelectedView(null)
  };

  const open = Boolean(anchorEl);
  const id = open ? 'view-popover' : undefined;

  const fetchViews = () => {
    setLoading(true)
    fetchData(VIEW_LIST_URL).then(
      response => {
        setViews(response.data)
        setLoading(false)
      }
    ).catch(e => setLoading(false))
  }

  useEffect(() => {
    fetchViews()
  }, [searchParams])

  const handleClose = () => {
    setConfirmationOpen(false)
  }

  const actionDeleteButton: ActionDataInterface = {
    field: '',
    name: 'Delete',
    getName: (data: any) => {
        if (!data.permissions.includes('Own')) {
            return 'You are not owner of this view'
        } else if (data.is_default === 'Yes') {
          return 'Cannot remove default view'
        }
        return 'Delete'
    },
    color: 'error',
    icon: <DeleteIcon />,
    isDisabled: (data: any) => {
      return !data.permissions.includes('Own') || data.is_default === 'Yes'
    },
    onClick: (data: View) => {
      setSelectedView(data)
      setConfirmationText(
        `Are you sure you want to delete ${data.name}?`)
      setConfirmationOpen(true)
    }
  }

  const actionMoreInfoButton: ActionDataInterface = {
    field: '',
    name: 'More Info',
    color: 'primary',
    icon: <MoreVertIcon />,
    onClick: (data: View, event?: React.MouseEvent<HTMLButtonElement>) => {
      setSelectedView(data)
      setAnchorEl(event.currentTarget);
    }
  }

  const handleDeleteClick = () => {
    setDeleteButtonDisabled(true)
    postData(
      `${DELETE_VIEW_URL}/${selectedView.id}`, {}
    ).then(
      response => {
        setDeleteButtonDisabled(false)
        fetchViews()
        setConfirmationOpen(false)
      }
    ).catch(error => {
      setDeleteButtonDisabled(false)
      alert('Error deleting view')
    })
  }

  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    navigate(ViewEditRoute.path + `?id=${rowData[0]}`)
  }

  return (
    <div className="AdminContentMain main-data-list">
      <AlertDialog open={confirmationOpen} alertClosed={handleClose}
          alertConfirmed={handleDeleteClick}
          alertLoading={deleteButtonDisabled}
          alertDialogTitle={'Delete view'}
          alertDialogDescription={confirmationText}
          confirmButtonText='Delete'
          confirmButtonProps={{color: 'error', autoFocus: true}}
      />
      {
        loading ? <Loading label={'Fetching views'}/> :
          <List
            pageName={'Views'}
            listUrl={''}
            initData={views}
            selectionChanged={null}
            onRowClick={handleRowClick}
            actionData={[actionMoreInfoButton, actionDeleteButton]}
            customOptions={{
              'tags': {
                filter: true,
                sort: false,
                display: true,
                filterType: "multiselect",
                customBodyRender: (value: any, tableMeta: any) => {
                  return <div>
                    {value.map((tag: any, index:number) => <Chip key={index} label={tag}/>)}
                  </div>
                }}
            }}
            excludedColumns={['permissions', 'uuid', 'layer_tiles', 'mode', 'is_default']}
          />
      }
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleCloseMoreInfo}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
      >
        <ViewPopover view={selectedView} />
      </Popover>
    </div>
  )
}
