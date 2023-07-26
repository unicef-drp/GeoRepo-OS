import {routes} from "./routes";

const moduleName = 'admin_boundaries'


export function moduleApp() {
  return {
    'name': moduleName,
    'routes': routes,
    // @ts-ignore
    'headers': []
  }
}
