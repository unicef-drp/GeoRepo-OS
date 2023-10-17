import React from 'react';
import {useNavigate} from "react-router-dom";
import Button from '@mui/material/Button';
import List from "../../components/List";
import {UserDetailRoute} from '../routes';


export default function Users () {
  const navigate = useNavigate()
  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    navigate(`${UserDetailRoute.path}?id=${rowData[0]}`)
  }
  const customColumnOptions = {
    'email': {
      filter: false,
    },
    'name': {
      filter: false,
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
        onRowClick={handleRowClick}
        actionData={[]}
        fetchUseCache={false}
        customOptions={customColumnOptions}
        options={{
          'confirmFilters': true,
          'customFilterDialogFooter': (currentFilterList: any, applyNewFilters: any) => {
            return (
              <div style={{marginTop: '40px'}}>
                <Button variant="contained" onClick={() => applyNewFilters()}>Apply Filters</Button>
              </div>
            );
          },
        }}
      />
    </div>
  )
}
