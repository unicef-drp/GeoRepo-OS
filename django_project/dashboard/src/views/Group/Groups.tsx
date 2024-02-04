import React from 'react';
import {useNavigate} from "react-router-dom";
import List from "../../components/List";
import {GroupDetailRoute} from '../routes';


export default function Groups() {
  const navigate = useNavigate()
  const customColumnOptions = {
    'name': {
      filter: false,
      customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          let rowData = tableMeta.rowData
          const handleClick = (e: any) => {
              e.preventDefault()
              navigate(`${GroupDetailRoute.path}?id=${rowData[0]}`)
          };
          return (
              <a href='#' onClick={handleClick}>{`${rowData[1]}`}</a>
          )
      },
    },
  }

  return (
    <div className="AdminContentMain main-data-list">
      <List
        pageName={"Groups"}
        listUrl={"/api/group-list/"}
        initData={[]}
        selectionChanged={null}
        onRowClick={null}
        actionData={[]}
        customOptions={customColumnOptions}
        options={{
          'filter': false
        }}
      />
    </div>
  )
}
