import React, {useEffect, useState} from 'react';
import {useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import {useAppDispatch} from "../../app/hooks";
import Skeleton from '@mui/material/Skeleton';
import EntityEditInterface from '../../models/entity';
import EntityEditForm from '../Dataset/EntityEditForm';
import Scrollable from '../../components/Scrollable';
import {v4 as uuidv4} from 'uuid';
import '../../styles/Entity.scss';

const FETCH_ENTITY_DETAIL = '/api/entity/edit/'

export default function EntityEdit(props: any) {
    const dispatch = useAppDispatch()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [tabSelected, setTabSelected] = useState(0)
    const [searchParams, setSearchParams] = useSearchParams()
    const [entity, setEntity] = useState<EntityEditInterface>()

    const updateSelectedTab = () => {
        let tab = 0
        if (searchParams.get('tab')) {
            tab = parseInt(searchParams.get('tab'))
            setTabSelected(tab)
        }
    }

    const fetchEntityDetail = () => {
        setLoading(true)
        axios.get(`${FETCH_ENTITY_DETAIL}${searchParams.get("id")}/`).then(
            response => {
              setLoading(false)
              let _entity: EntityEditInterface = response.data as EntityEditInterface
              _entity['codes'] = _entity['codes'].map((code) => {
                return {...code, 'uuid': uuidv4()}
              })
              _entity['names'] = _entity['names'].map((name) => {
                return {...name, 'uuid': uuidv4()}
              })
              setEntity(_entity)
            }
          ).catch((error) => {
            if (error.response) {
              if (error.response.status == 403) {
                // TODO: use better way to handle 403
                navigate('/invalid_permission')
              }
            }
          })
    }

    useEffect(() => {
        let entityId = searchParams.get('id') ? parseInt(searchParams.get('id')) : 0
        if (entityId > 0) {
            fetchEntityDetail()
        } else {
            updateSelectedTab()
        }
    }, [searchParams])

    return (
        <Scrollable>
          <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
              { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
              { !loading && (
                <EntityEditForm entity={entity} onEntityUpdated={fetchEntityDetail} />
              )}
          </div>
        </Scrollable>
    )

}
