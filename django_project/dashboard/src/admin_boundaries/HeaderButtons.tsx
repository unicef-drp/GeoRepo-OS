
import React from "react";
import {HeaderButtonsInterface, UploadDataButton} from "../components/HeaderButtons";

export const UploadDataAdminBoundaries = () => {
  return <UploadDataButton next={'/admin_boundaries/upload_wizard'} />
}


export const headerButtons: HeaderButtonsInterface[] = [{
  path: '/dataset_entities',
  element: <UploadDataAdminBoundaries/>
}]
