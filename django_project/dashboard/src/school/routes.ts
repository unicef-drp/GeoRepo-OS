import {DatasetRoute, RouteInterface} from "../views/routes";
import DatasetEntityList from "./DatasetEntityList";


const DatasetEntityListAdminRoute: RouteInterface = {
  id: 'dataset_entities',
  name: '',
  path: '/dataset_entities',
  element: DatasetEntityList,
  parent: DatasetRoute
}


export const routes: Array<RouteInterface> = [
  DatasetEntityListAdminRoute
]
