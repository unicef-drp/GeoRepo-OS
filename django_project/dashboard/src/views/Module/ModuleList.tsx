import React, {useEffect, useState} from 'react';
import {useNavigate, useSearchParams} from "react-router-dom";
import List from "../../components/List";
import Loading from "../../components/Loading";
import {fetchData} from "../../utils/Requests";


const MODULE_LIST_URL = '/api/module-list/'


export default function ModuleList() {
  const [searchParams] = useSearchParams()
  const [modules, setModules] = useState<any[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const navigate = useNavigate()
  const customColumnOptions = {
    'name': {
      filter: false,
      customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          let rowData = tableMeta.rowData
          const handleClick = (e: any) => {
              e.preventDefault()
              navigate(`/module?uuid=${rowData[3]}`)
          };
          return (
              <a href='#' onClick={handleClick}>{`${rowData[1]}`}</a>
          )
      },
    },
  }

  const fetchModules = () => {
      setLoading(true)
      fetchData(MODULE_LIST_URL).then(
          response => {
              setModules(response.data)
              setLoading(false)
          }
      ).catch(error => {
        setLoading(false)
        if (error.response) {
          if (error.response.status == 403) {
            // TODO: use better way to handle 403
            navigate('/invalid_permission')
          }
        }
      })
  }

  useEffect(() => {
      fetchModules()
    }, [searchParams])
  
  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    navigate(`/module?uuid=${rowData[3]}`)
  }

  return (
    <div className="AdminContentMain main-data-list">
      {
        loading ? <Loading label={'Fetching modules'}/> :
          <List
            pageName={'Modules'}
            listUrl={''}
            initData={modules}
            selectionChanged={null}
            onRowClick={null}
            excludedColumns={['uuid', 'is_active']}
            actionData={[]}
            customOptions={customColumnOptions}
            options={{
              'filter': false
            }}
          />
      }
    </div>
  )
}
