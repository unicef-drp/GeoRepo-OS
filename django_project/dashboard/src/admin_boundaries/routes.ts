import {DatasetRoute, RouteInterface, ReviewListRoute} from "../views/routes";
import DatasetDetailWrapper from "./DatasetDetail"
import UploadWizardWrapper from "./Wizard"
import ReviewWrapper from "./ReviewWrapper";
import BatchEntityEditWizard from "./BatchEntityEditWizard";


export const DatasetEntityListAdminRoute: RouteInterface = {
  id: 'admin_boundaries_dataset_entities',
  name: '',
  path: '/dataset_entities',
  element: DatasetDetailWrapper,
  parent: DatasetRoute
}

export const UploadWizardRoute: RouteInterface = {
  id: 'admin_boundaries_upload_wizard',
  name: 'Upload',
  path: '/upload_wizard',
  element: UploadWizardWrapper,
  parent: DatasetEntityListAdminRoute
}

const ReviewDetailRoute: RouteInterface = {
  id: 'admin_boundaries_review_detail',
  name: 'Detail',
  path: '/review_detail',
  element: ReviewWrapper,
  parent: ReviewListRoute
}

const BatchEntityEditRoute: RouteInterface = {
  id: 'batch_entity_edit',
  name: 'Batch Editor',
  path: '/edit_entity/wizard',
  element: BatchEntityEditWizard,
  parent: DatasetEntityListAdminRoute
}

export const routes: Array<RouteInterface> = [
  DatasetEntityListAdminRoute,
  UploadWizardRoute,
  ReviewDetailRoute,
  BatchEntityEditRoute
]
