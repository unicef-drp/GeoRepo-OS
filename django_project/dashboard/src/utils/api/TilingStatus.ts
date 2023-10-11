import axios from "axios";

const SYNC_STATUS_URL = '/api/sync-status/'

export const fetchSyncStatusAPI = (object_type: string, object_uuid: string, callback: (response: any, error: any) => void) => {
    let _fetch_url = `${SYNC_STATUS_URL}${object_type}/${object_uuid}/`
    axios.get(_fetch_url).then(
        response => {
            callback(response.data, null)
        }
    ).catch((error) => {
        console.log('Fetch sync status failed! ', error)
        callback(null, error)
    })
}
