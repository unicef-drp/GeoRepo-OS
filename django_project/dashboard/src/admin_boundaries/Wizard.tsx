import React, { useState } from "react";
import UploadWizard from "../views/Dataset/UploadWizard";
import { WizardStepElementInterface } from "../models/upload";
import { DatasetEntityListAdminRoute } from "./routes"

import Step0 from "./uploads/Step0";
import Step1 from "./uploads/Step1";
import Step2 from "./uploads/Step2";
import Step3 from "./uploads/Step3";
import Step4 from "./uploads/Step4";


export default function UploadWizardWrapper() {
    const [steps, setSteps] = useState<WizardStepElementInterface[]>([
      {
        title: 'Step 1',
        element: Step0
      },
      {
        title: 'Step 2',
        element: Step1
      },
      {
        title: 'Step 3',
        element: Step2
      },
      {
        title: 'Step 4',
        element: Step3
      },
      {
        title: 'Step 5',
        element: Step4
      }
    ])
    return (
      <UploadWizard steps={steps} moduleName={'admin_boundaries'} datasetEntitiesPath={DatasetEntityListAdminRoute.path} />
    )
  }
