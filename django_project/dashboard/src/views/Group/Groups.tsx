import React from 'react';
import {useNavigate} from "react-router-dom";
import List from "../../components/List";
import {GroupDetailRoute} from '../routes';


export default function Groups() {
  const navigate = useNavigate()
  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    navigate(`${GroupDetailRoute.path}?id=${rowData[0]}`)
  }

  return (
    <div className="AdminContentMain main-data-list">
      <List
        pageName={"Groups"}
        listUrl={"/api/group-list/"}
        initData={[]}
        selectionChanged={null}
        onRowClick={handleRowClick}
        actionData={[]}
      />
    </div>
  )
}
