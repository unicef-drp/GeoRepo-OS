import React from "react";
import {HeaderButtonsInterface, UploadDataButton} from "../components/HeaderButtons";

export const UploadDataAdminBoundaries = () => {
  return <UploadDataButton next={'/boundary_lines/upload_wizard'} />
}


export const headerButtons: HeaderButtonsInterface[] = [{
  path: '/dataset_entities',
  element: <UploadDataAdminBoundaries/>
}]
