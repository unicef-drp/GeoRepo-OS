  import { lazy } from '@loadable/component';
import HomeIcon from '@mui/icons-material/Home';
import {OverridableComponent} from "@mui/material/OverridableComponent";
import {SvgIconTypeMap} from "@mui/material/SvgIcon/SvgIcon";
import DnsIcon from '@mui/icons-material/Dns';
import ViewListIcon from '@mui/icons-material/ViewList';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import PeopleIcon from '@mui/icons-material/People';
import GroupsIcon from '@mui/icons-material/Groups';
import ViewCompactAltIcon from '@mui/icons-material/ViewCompactAlt';
import ViewModuleIcon from '@mui/icons-material/ViewModule';
import PrivacyTipIcon from '@mui/icons-material/PrivacyTip';
import ManageAccountsIcon from '@mui/icons-material/ManageAccounts';

export interface RouteInterface {
  id: string,
  name: string,
  path: string,
  element: Function,
  icon?: OverridableComponent<SvgIconTypeMap>,
  parent?: RouteInterface
}

const HomeRoute: RouteInterface = {
  id: 'home',
  name: 'Home',
  path: '',
  element: lazy(() => import('./Home')),
  icon: HomeIcon,
}

export const DatasetRoute: RouteInterface = {
  id: 'dataset',
  name: 'Dataset',
  path: '/dataset',
  element: lazy(() => import('./Dataset/Dataset' /* webpackChunkName: "dataset" */)),
  icon: DnsIcon
}

const UploaderRoute: RouteInterface = {
  id: 'uploader',
  name: 'Uploader',
  path: '/uploader',
  element: lazy(() => import('./Upload' /* webpackChunkName: "upload" */)),
}

export const UploadSessionListRoute: RouteInterface = {
  id: 'upload_list',
  name: 'Uploads',
  path: '/upload_list',
  element: lazy(() => import('./Upload/UploadSessionList' /* webpackChunkName: "upload_session_list" */)),
  icon: ViewListIcon
}

export const DatasetCreateRoute: RouteInterface = {
  id: 'create_dataset',
  name: 'Create Dataset',
  path: '/create_dataset',
  element: lazy(() => import('./Dataset/DatasetCreate' /* webpackChunkName: "dataset_create" */)),
  parent: DatasetRoute
}

export const ReviewListRoute: RouteInterface = {
  id: 'review_list',
  name: 'Reviews',
  path: '/review_list',
  element: lazy(() => import('./Review/List'  /* webpackChunkName: "review_list" */)),
  icon: FactCheckIcon
}

export const UserListRoute: RouteInterface = {
  id: 'user_list',
  name: 'Users',
  path: '/user_list',
  element: lazy(() => import('./User/Users' /* webpackChunkName: "users" */)),
  icon: PeopleIcon
}

export const UserDetailRoute: RouteInterface = {
  id: 'user_detail',
  name: 'User',
  path: '/user',
  element: lazy(() => import('./User/UserDetail' /* webpackChunkName: "user_detail" */)),
  parent: UserListRoute
}

export const UserProfileRoute: RouteInterface = {
  id: 'user_profile',
  name: 'Profile',
  path: '/profile',
  element: lazy(() => import('./User/UserDetail' /* webpackChunkName: "user_detail" */)),
  icon: ManageAccountsIcon
}

export const UserAddRoute: RouteInterface = {
  id: 'add_user',
  name: 'Add User',
  path: '/add_user',
  element: lazy(() => import('./User/UserCreate' /* webpackChunkName: "user_create" */)),
  parent: UserListRoute
}

export const GroupListRoute: RouteInterface = {
  id: 'group_list',
  name: 'Groups',
  path: '/group_list',
  element: lazy(() => import('./Group/Groups' /* webpackChunkName: "groups" */)),
  icon: GroupsIcon
}

export const GroupDetailRoute: RouteInterface = {
  id: 'group_detail',
  name: 'Group',
  path: '/group',
  element: lazy(() => import('./Group/GroupDetail' /* webpackChunkName: "group_detail" */)),
  parent: GroupListRoute
}

export const AccessRequestListRoute: RouteInterface = {
  id: 'access_request_list',
  name: 'Access Requests',
  path: '/access_request_list',
  element: lazy(() => import('./AccessRequest/AccessRequestList' /* webpackChunkName: "access_request_list" */)),
  icon: PrivacyTipIcon
}

export const AccessRequestDetailRoute: RouteInterface = {
  id: 'access_request_detail',
  name: 'Access Request',
  path: '/access_request',
  element: lazy(() => import('./AccessRequest/AccessRequestDetail' /* webpackChunkName: "access_request_detail" */)),
  parent: AccessRequestListRoute
}

export const AccessRequestSubmitRoute: RouteInterface = {
  id: 'access_request_submit',
  name: 'Access Request',
  path: '/access_request_submit',
  element: lazy(() => import('./AccessRequest/SubmitAccessRequest' /* webpackChunkName: "access_request_submit" */)),
  icon: PrivacyTipIcon
}

export const ViewListRoute: RouteInterface = {
  id: 'view',
  name: 'Views',
  path: '/views',
  element: lazy(() => import('./View/Views' /* webpackChunkName: "views" */)),
  icon: ViewCompactAltIcon
}

export const ViewCreateRoute: RouteInterface = {
  id: 'view_create',
  name: 'Create View',
  path: '/view_create',
  element: lazy(() => import('./View/ViewDetail' /* webpackChunkName: "view_detail" */)),
  parent: ViewListRoute
}

export const ViewEditRoute: RouteInterface = {
  id: 'view_edit',
  name: 'Edit View',
  path: '/view_edit',
  element: lazy(() => import('./View/ViewDetail' /* webpackChunkName: "view_detail" */)),
  parent: ViewListRoute
}

export const ViewEditTilingConfigRoute: RouteInterface = {
  id: 'view_tiling_config_wizard',
  name: 'Update Tiling Config',
  path: '/view_edit_tiling_config_wizard',
  element: lazy(() => import('./Dataset/Configurations/TilingConfigWizard' /* webpackChunkName: "view_edit_tiling_config_wizard" */)),
  parent: ViewEditRoute
}

export const EntityConceptUCodeRoute: RouteInterface = {
  id: 'entity_by_concept_ucode',
  name: 'Entity Detail By Concept UCode',
  path: '/entity',
  element: lazy(() => import('./Dataset/ConceptUcodeDetail' /* webpackChunkName: "concept_ucode_detail" */)),
  parent: DatasetRoute
}

// export const EntityEditRoute: RouteInterface = {
//   id: 'entity_edit',
//   name: 'Entity Edit',
//   path: '/entity',
//   element: lazy(() => import('./Dataset/EntityDetail' /* webpackChunkName: "entity_edit" */)),
//   parent: DatasetRoute
// }

export const ModuleListRoute: RouteInterface = {
  id: 'module_list',
  name: 'Modules',
  path: '/modules',
  element: lazy(() => import('./Module/ModuleList' /* webpackChunkName: "module_list" */)),
  icon: ViewModuleIcon
}

export const ModuleDetailRoute: RouteInterface = {
  id: 'module_detail',
  name: 'Module',
  path: '/module',
  element: lazy(() => import('./Module/ModuleDetail' /* webpackChunkName: "module_detail" */)),
  parent: ModuleListRoute
}

export const InvalidPermissionRoute: RouteInterface = {
  id: 'invalid_permission',
  name: 'Invalid Permission',
  path: '/invalid_permission',
  element: lazy(() => import('./InvalidPermission' /* webpackChunkName: "invalid_permission" */)),
}

export const routes: Array<RouteInterface> = (window as any).is_admin ? [
  HomeRoute,
  DatasetRoute,
  ViewListRoute,
  UploaderRoute,
  UploadSessionListRoute,
  DatasetCreateRoute,
  ReviewListRoute,
  UserListRoute,
  UserDetailRoute,
  UserAddRoute,
  GroupListRoute,
  GroupDetailRoute,
  ViewCreateRoute,
  ViewEditRoute,
  ViewEditTilingConfigRoute,
  EntityConceptUCodeRoute,
  ModuleListRoute,
  ModuleDetailRoute,
  InvalidPermissionRoute,
  AccessRequestListRoute,
  AccessRequestDetailRoute,
  UserProfileRoute
] : [
  HomeRoute,
  DatasetRoute,
  ViewListRoute,
  UploaderRoute,
  UploadSessionListRoute,
  DatasetCreateRoute,
  ReviewListRoute,
  ViewCreateRoute,
  ViewEditRoute,
  ViewEditTilingConfigRoute,
  EntityConceptUCodeRoute,
  InvalidPermissionRoute,
  AccessRequestSubmitRoute,
  UserProfileRoute
]


export const getActiveRoute = (route: RouteInterface): RouteInterface => {
  return route && route.parent ? getActiveRoute(route.parent) : route
}
