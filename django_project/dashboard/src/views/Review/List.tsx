import React, {useEffect, useState} from "react";
import {useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import {RootState} from "../../app/store";
import { useAppSelector, useAppDispatch } from '../../app/hooks';
import {setModule} from "../../reducers/module";
import {modules} from "../../modules";
import List from "../../components/List";
import Loading from "../../components/Loading";
import {setSelectedReviews} from "../../reducers/reviewAction";


export interface ReviewData {
  id: number,
  revision: number,
  module: string
}


export default function ReviewList () {
  const [loading, setLoading] = useState<boolean>(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<any[]>([])
  const [customOptions, setCustomOptions] = useState<any>({})
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const isBatchReviewAvailable = useAppSelector((state: RootState) => state.reviewAction.isBatchReviewAvailable)
  const isBatchReview = useAppSelector((state: RootState) => state.reviewAction.isBatchReview)
  const pendingReviews = useAppSelector((state: RootState) => state.reviewAction.pendingReviews)
  const reviewUpdatedAt = useAppSelector((state: RootState) => state.reviewAction.updatedAt)

  const fetchReviewList = () => {
    axios.get('/api/review-list').then((response) => {
      setLoading(false)
      if (response.data) {
        // update filter values if searchParams has upload filter
        let _upload = searchParams.get('upload')
        if (_upload) {
          setCustomOptions({
            'upload': {
              'filterList': [_upload]
            }
          })
        }
        setData(response.data)
      }
    })
  }

  useEffect(() => {
    fetchReviewList()
  }, [searchParams])

  useEffect(() => {
    if (reviewUpdatedAt) {
      fetchReviewList()
    }
  }, [reviewUpdatedAt])

  const canRowBeSelected = (dataIndex: number, rowData: any) => {
    if (!isBatchReviewAvailable)
      return false
    return !pendingReviews.includes(rowData['id']) && rowData['is_comparison_ready']
  }

  const selectionChanged = (data: any) => {
    dispatch(setSelectedReviews(data))
  }

  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    console.log(rowData)
    let moduleName = toLower(rowData[8]).replace(' ', '_')
    if (!moduleName) {
      moduleName = modules[0]
    }
    dispatch(setModule(moduleName))
    // Go to review page
    navigate(`/${moduleName}/review_detail?id=${rowData[0]}`)
  }

  return (
    loading ?
      <div className={"loading-container"}><Loading/></div> :
      <div className="AdminContentMain review-list main-data-list">
        <List pageName={"Review"}
          listUrl={""}
          initData={data}
          selectionChanged={selectionChanged}
          onRowClick={handleRowClick}
          actionData={[]}
          excludedColumns={['module', 'is_comparison_ready']}
          isRowSelectable={isBatchReview}
          canRowBeSelected={canRowBeSelected}
          customOptions={customOptions}
          options={{
            'selectToolbarPlacement': 'none'
          }}
        />
      </div>
  )
}
