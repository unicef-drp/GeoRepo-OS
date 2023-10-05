import {DatasetRoute, RouteInterface, ReviewListRoute} from "../views/routes";
import DatasetDetailWrapper from "./DatasetDetail"
import UploadWizardWrapper from "./Wizard"
import ReviewWrapper from "./ReviewWrapper";


export const DatasetEntityListAdminRoute: RouteInterface = {
  id: 'boundary_lines_dataset_entities',
  name: '',
  path: '/dataset_entities',
  element: DatasetDetailWrapper,
  parent: DatasetRoute
}

export const UploadWizardRoute: RouteInterface = {
  id: 'boundary_lines_upload_wizard',
  name: 'Upload',
  path: '/upload_wizard',
  element: UploadWizardWrapper,
  parent: DatasetEntityListAdminRoute
}

const ReviewDetailRoute: RouteInterface = {
  id: 'boundary_lines_review_detail',
  name: 'Detail',
  path: '/review_detail',
  element: ReviewWrapper,
  parent: ReviewListRoute
}

export const routes: Array<RouteInterface> = [
  DatasetEntityListAdminRoute,
  UploadWizardRoute,
  ReviewDetailRoute
]
