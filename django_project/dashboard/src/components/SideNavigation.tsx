import React from 'react';
import '../styles/SideNavigation.scss';
import {getActiveRoute, RouteInterface} from "../views/routes";
import {
  NavLink
} from "react-router-dom";
import {useMatchedRoute} from "../views/Dashboard";

interface SideNavigationProps {
  routes: RouteInterface[]
}

export default function SideNavigation(props: SideNavigationProps) {
  const route = useMatchedRoute(props.routes);

  return (
    <div className='SideNavigation'>
      { props.routes.filter(_route => _route.icon).map((_route, key)=> (
        <NavLink to={_route.path} className={"SideNavigation-Row " + (getActiveRoute(route).id === _route.id ? "active" : "")} key={key} data-id={_route.id}>
          <_route.icon className="SideNavigation-Row-Icon"/>
          <span className='SideNavigation-Row-Name'>{_route.name}</span>
        </NavLink>
      ))}
    </div>
  )
}
