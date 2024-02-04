import React from 'react';
import {useNavigate} from "react-router-dom";
import List, {applyFilterDialogFooter} from "../../components/List";
import {UserDetailRoute} from '../routes';


export default function Users () {
  const navigate = useNavigate()
  const customColumnOptions = {
    'email': {
      filter: false,
    },
    'name': {
      filter: false,
      customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          let rowData = tableMeta.rowData
          const _name = rowData[1] ? rowData[1].trim() : ''
          const handleClick = (e: any) => {
              e.preventDefault()
              navigate(`${UserDetailRoute.path}?id=${rowData[0]}`)
          };
          return (
              <a href='#' onClick={handleClick}>{`${_name ? _name : rowData[2]}`}</a>
          )
      },
    },
    'username': {
      filter: false,
    },
    'id': {
      filter: false,
      display: false,
    }
  }

  return (
    <div className="AdminContentMain main-data-list">
      <List
        pageName={"Users"}
        listUrl={"/api/user-list/"}
        initData={[]}
        selectionChanged={null}
        onRowClick={null}
        actionData={[]}
        fetchUseCache={false}
        customOptions={customColumnOptions}
        options={{
          'confirmFilters': true,
          'customFilterDialogFooter': applyFilterDialogFooter,
        }}
      />
    </div>
  )
}
