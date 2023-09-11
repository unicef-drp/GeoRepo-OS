import React, {useEffect, useState} from 'react';
import {useSearchParams} from "react-router-dom";
import {useNavigate} from "react-router-dom";
import axios from "axios";
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import {useAppDispatch} from "../../app/hooks";
import {updateMenu} from "../../reducers/breadcrumbMenu";
import TabPanel, {a11yProps} from '../../components/TabPanel';
import Skeleton from '@mui/material/Skeleton';
import { EntityEditRoute } from '../routes';
import EntityEditInterface  from '../../models/entity';
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
              dispatch(updateMenu({
                id: `entity_detail`,
                name: `${_entity.names[0].name}`
              }))
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
        } else if (entityId === 0) {
            setLoading(false)
            dispatch(updateMenu({
                id: `entity_detail`,
                name: `Add New Entity`
              }))
              updateSelectedTab()
        } else {
            updateSelectedTab()
        }
    }, [searchParams])

    const handleChange = (event: React.SyntheticEvent, newValue: number) => {
        navigate(`${EntityEditRoute.path}?id=${searchParams.get('id')}&tab=${newValue}`)
    }

    return (
        <Scrollable>
          <div style={{display:'flex', flex: 1, flexDirection: 'column'}}>
              { loading && <Skeleton variant="rectangular" height={'100%'} width={'100%'}/> }
              { !loading && (
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                  <Tabs value={tabSelected} onChange={handleChange} aria-label="Entity Tab">
                      <Tab key={'tab-0'} label={'DETAIL'} {...a11yProps(0)} />
                  </Tabs>
              </Box>
              )}
              { !loading && (
                <Grid container sx={{ flexGrow: 1, flexDirection: 'column' , overflow: 'auto'}}>
                  <TabPanel key={0} value={tabSelected} index={0} padding={1}>
                      <EntityEditForm entity={entity} onEntityUpdated={fetchEntityDetail} />
                  </TabPanel>
                </Grid>
              )}
          </div>
        </Scrollable>
    )

}
