import breadcrumbReducer, {
  BreadcrumbState,
  changeCurrentMenu,
  addMenu,
  revertMenu
} from './breadcrumbMenu';

describe('breadcrumb reducer', () => {
  const initialState: BreadcrumbState = {
    currentMenu: 'menu',
    menus: []
  };
  it('should handle initial state', () => {
    expect(breadcrumbReducer(undefined, { type: 'unknown' })).toEqual({
      currentMenu: '',
      menus: []
    });
  });
  it('should handle menu changed', () => {
    const breadcrumbReducer1 = breadcrumbReducer(initialState, changeCurrentMenu('test'))
    expect(breadcrumbReducer1.currentMenu).toEqual('test')
  });
  it('should add menu', () => {
    const breadcrumbReducer1 = breadcrumbReducer(initialState, addMenu({
      'id': 'test',
      'name': 'test',
      'link': 'link'
    }))
    expect(breadcrumbReducer1.currentMenu).toEqual('test')
    expect(breadcrumbReducer1.menus).toEqual([{
      'id': 'test',
      'name': 'test',
      'link': 'link'
    }])
  });
  it('should revert', () => {
    const state: BreadcrumbState = {
      currentMenu: 'menu',
      menus: [
        {
          id: 'test',
          name: 'menu1',
          link: 'link1'
        },
        {
          id: 'test2',
          name: 'menu2',
          link: 'link2'
        },
        {
          id: 'test3',
          name: 'menu3',
          link: 'link3'
        },
        {
          id: 'test4',
          name: 'menu4',
          link: 'link4'
        }
      ]
    };
    const breadcrumbReducer1 = breadcrumbReducer(state, revertMenu('test2'))
    expect(breadcrumbReducer1.menus).toEqual([
      {
        id: 'test',
        name: 'menu1',
        link: 'link1'
      },
      {
        id: 'test2',
        name: 'menu2',
        link: 'link2'
      },
    ])
    // @ts-ignore
    expect(breadcrumbReducer1.menus.length).toEqual(2)
    expect(breadcrumbReducer1.currentMenu).toEqual('test2')
  })

});
