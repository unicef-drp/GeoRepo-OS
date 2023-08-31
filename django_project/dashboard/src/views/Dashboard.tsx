import React, {Suspense, useEffect, useState, useRef} from 'react';
import {useSearchParams} from "react-router-dom";
import '../styles/App.scss';
import '../styles/mui.scss';
import NavBar from "../components/NavBar";
import SideNavigation from "../components/SideNavigation";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  matchPath, useLocation, Link
} from "react-router-dom";
import {routes, RouteInterface} from "./routes";
import {headerButtons, HeaderButtonsInterface} from "../components/HeaderButtons";
import { useAppSelector, useAppDispatch } from '../app/hooks';
import {addMenu, breadcrumbMenus, changeMenu} from "../reducers/breadcrumbMenu";
import Notification from '../components/Notification';
import Maintenance from '../components/Maintenance';
import Loading from "../components/Loading";
import ErrorBoundary from "../components/ErrorBoundary";
import { HelpCenter } from '../components/HelpCenter'
import HelpIcon from '@mui/icons-material/Help';


export function useMatchedRoute(routes: RouteInterface[]) {
  const { pathname } = useLocation();
  for (const route of routes) {
    if (matchPath({ path: route.path }, pathname)) {
      return route;
    }
  }
}

interface DashboardInterface {
  modules?: string[]
}

function Dashboard(props: DashboardInterface) {
  const helpPageRef = useRef<HTMLButtonElement | null>(null)
  const [appRoutes, setAppRoutes] = useState<RouteInterface[]>([])
  const [appHeaderButtons, setAppHeaderButtons] = useState([])

  useEffect(() => {
    async function getModuleData() {
      let allRoutes = [...routes]
      let allHeaderButtons = [...headerButtons]
      for (let module of props.modules) {
        await import(`../${module}/app`).then(async ({moduleApp}) => {
          let moduleData = moduleApp()
          if (moduleData.routes) {
            allRoutes.push(...moduleData.routes.map((route: RouteInterface) => {
              route.path = `/${module}` + route.path
              return route
            }))
          }
          if (moduleData.headers) {
            allHeaderButtons.push(...moduleData.headers.map((header: HeaderButtonsInterface) => {
              header.path = `/${module}` + header.path
              return header
            }))
          }
        })
      }
      setAppRoutes(allRoutes)
      setAppHeaderButtons(allHeaderButtons)
    }
    getModuleData()
  }, [])

  return (
    <div className="App">
      <NavBar helpPageRef={helpPageRef}/>
      {/*<div className='HelpButton .SvgButton'>*/}
      {/*  <a href='#' onClick={_ => {*/}
      {/*    helpPageRef?.current.open()*/}
      {/*  }}>*/}
      {/*    <HelpIcon/>*/}
      {/*  </a>*/}
      {/*</div>*/}
      <main>
            {
              appRoutes.length === 0  || appHeaderButtons.length === 0 ? <div style={{width: "100%"}} className={"loading-container"}>
                    <Loading/></div> :
                <Router>
                  <SideNavigation routes={appRoutes}/>
                  <Notification/>
                  <div className='AdminContent'>
                    <Header routes={appRoutes} headerButtons={appHeaderButtons}/>
                    <Maintenance />
                    <Suspense fallback={<Loading/>}>
                      <ErrorBoundary>
                        <Routes>
                          {appRoutes.map((route, key) => {
                            return <Route key={key} path={route.path} element={<route.element/>}/>
                          })}
                        </Routes>
                      </ErrorBoundary>
                    </Suspense>
                  </div>
                </Router>
            }
      </main>
      <HelpCenter ref={helpPageRef}/>
    </div>
  );
}

interface HeaderInterface {
  routes: RouteInterface[],
  headerButtons: HeaderButtonsInterface[]
}

export function Header(props: HeaderInterface) {
  const dispatch = useAppDispatch();
  const route = useMatchedRoute(props.routes);
  const menus = useAppSelector(breadcrumbMenus);
  const [searchParams, setSearchParams] = useSearchParams()

  const breadCrumb = () => {
    if (menus.length > 0) {
      return <div>
        {
          menus.map((menu, index) => {
            let _link = menu.link
            if (index === menus.length - 1) {
              _link += `?${searchParams.toString()}`
            }
            return <Link key={index} to={_link}>{index > 0 ? ' > ' : ''}{menu.name}</Link>
          })
        }
      </div>
    }
  }

  const updateBreadcrumbs = (route: RouteInterface) => {
    if (route.parent) {
      updateBreadcrumbs(route.parent)
    } else {
      dispatch(changeMenu({
        'id': route.id,
        'name': route.name,
        'link': route.path
      }))
    }
    dispatch(addMenu({
      'id': route.id,
      'name': route.name,
      'link': route.path
    }))
  }

  useEffect(() => {
    if (route) {
      updateBreadcrumbs(route)
    }
  }, [route])

  return (
    <div className='AdminContentHeader'>
      <div className='AdminContentHeader-Left'>
        <b className='light'>{ breadCrumb() }</b>
      </div>
      <div className="AdminContentHeader-Right">
        { props.headerButtons.find(headerButton => headerButton.path === route.path) ?
          props.headerButtons.find(headerButton => headerButton.path === route.path).element : '' }
      </div>
    </div>
  )
}

export default Dashboard;
