import React, {useState, useEffect} from 'react';
import "../styles/Dataset.scss";
import DatasetEntityList from "../views/DatasetEntityList";


export default function AdminDatasetEntityList() {
    return <DatasetEntityList body={<div>School</div>}/>
}
