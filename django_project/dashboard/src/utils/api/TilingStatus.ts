import axios from "axios";

const TILING_CONFIGS_STATUS_URL = '/api/tiling-configs/status/'

export const fetchTilingStatusAPI = (object_type: string, object_uuid: string, callback: (response: any, error: any) => void) => {
    let _fetch_url = `${TILING_CONFIGS_STATUS_URL}${object_type}/${object_uuid}/`
    axios.get(_fetch_url).then(
        response => {
            callback(response.data, null)
        }
    ).catch((error) => {
        console.log('Fetch Tiling status failed! ', error)
        callback(null, error)
    })
}
