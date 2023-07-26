import React, { useState } from "react";
import ReviewDetail from "../views/Review/Detail";
import { ReviewTabElementInterface } from "../models/upload";
import DetailSummaryTable from "./Review/DetailSummaryTable";
import DetailMatchTable from "./Review/DetailMatchTable";

export default function ReviewWrapper() {
    return (
        <ReviewDetail detail={DetailMatchTable} summary={DetailSummaryTable} moduleName='admin_boundaries' />
    )
}
