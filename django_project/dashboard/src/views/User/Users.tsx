import React from 'react';
import {useNavigate} from "react-router-dom";
import List from "../../components/List";
import {UserDetailRoute} from '../routes';


export default function Users () {
  const navigate = useNavigate()
  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    navigate(`${UserDetailRoute.path}?id=${rowData[0]}`)
  }

  return (
    <div className="AdminContentMain main-data-list">
      <List
        pageName={"Users"}
        listUrl={"/api/user-list/"}
        initData={[]}
        selectionChanged={null}
        onRowClick={handleRowClick}
        actionData={[]}
        fetchUseCache={false}
      />
    </div>
  )
}
