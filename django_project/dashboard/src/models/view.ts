export default interface View {
  id?: number,
  name: string,
  description?: string,
  status?: string,
  query_string?: string,
  dataset?: string,
  mode?: string,
  tags?: string[],
  total?: number,
  uuid: string,
  preview_session?: string,
  permissions?: string[],
  min_privacy?: number,
  max_privacy?: number,
  is_default?: string,
  layer_tiles?: string,
  is_read_only?: boolean,
  dataset_uuid?: string,
  dataset_style_source_name?: string,
  dataset_name?: string,
  module_name?: string
}

export const isReadOnlyView = (view: View): boolean => {
  let _isReadOnly = true
  if (view.permissions) {
    _isReadOnly = !view.permissions.includes('Own') || view.is_read_only
  } else {
    _isReadOnly = true
  }
  return _isReadOnly
}
