import React from 'react';
import Dashboard from './Dashboard';
import { store } from '../app/store';
import {Provider} from "react-redux";
import {modules} from "../modules";
import { act } from "react-dom/test-utils";
import {unmountComponentAtNode, render} from "react-dom";

let container: any = null;

beforeEach(() => {
  // setup a DOM element as a render target
  container = document.createElement("div");
  document.body.appendChild(container);
});

afterEach(() => {
  // cleanup on exiting
  unmountComponentAtNode(container);
  container.remove();
  container = null;
});

test('renders dashboard admin content', async () => {
  await act(() => render(
      <Provider store={store}>
        <Dashboard modules={modules}/>
      </Provider>, container
  ))
  expect(container.getElementsByClassName(
    'AdminContent').length
  ).toBe(1)
}, 50000);

test('renders routes', async () => {
  await act(() => render(
    <Provider store={store}><Dashboard modules={modules}/></Provider>, container
  ));
  expect(container.innerHTML.includes('GeoRepo')).toBeTruthy();
}, 70000)
